import datetime as dt
import operator
import uuid
from typing import Any, Callable, Dict, List, Optional, Type

from dateutil.parser import isoparse
from django.db.models import Exists, F, Model, OuterRef, Q, Value, functions
from django.db.models.expressions import Expression

from odata_query import ast, exceptions as ex, typing, utils, visitor

from .utils import reverse_relationship

COMPARISON_INVERT = {
    ast.Eq: ast.Eq,
    ast.NotEq: ast.NotEq,
    ast.Lt: ast.Gt,
    ast.LtE: ast.GtE,
    ast.Gt: ast.Lt,
    ast.GtE: ast.LtE,
}


class AstToDjangoQVisitor(visitor.NodeVisitor):
    """
    :class:`NodeVisitor` that transforms an :term:`AST` into a Django Q
    filter object.

    Args:
        root_model: The root model of the query.
    """

    def __init__(self, root_model: Type[Model]):
        self.root_model = root_model
        self.queryset_annotations: Dict[str, Expression] = {}

    def visit_Identifier(self, node: ast.Identifier) -> F:
        ":meta private:"
        return F(node.name)

    def visit_Attribute(self, node: ast.Attribute) -> F:
        ":meta private:"
        owner = self.visit(node.owner)
        full_id = owner.name + "__" + node.attr
        return F(full_id)

    def visit_Null(self, node: ast.Null) -> str:
        ":meta private:"
        raise NotImplementedError("Should not be reached")

    def visit_Integer(self, node: ast.Integer) -> Value:
        ":meta private:"
        return Value(int(node.val))

    def visit_Float(self, node: ast.Float) -> Value:
        ":meta private:"
        return Value(float(node.val))

    def visit_Boolean(self, node: ast.Boolean) -> Value:
        ":meta private:"
        return Value(node.val == "true")

    def visit_String(self, node: ast.String) -> Value:
        ":meta private:"
        return Value(node.val)

    def visit_Date(self, node: ast.Date) -> Value:
        ":meta private:"
        try:
            return Value(dt.date.fromisoformat(node.val))
        except ValueError:
            raise ex.ValueException(node.val)

    def visit_DateTime(self, node: ast.DateTime) -> Value:
        ":meta private:"
        try:
            return Value(isoparse(node.val))
        except ValueError:
            raise ex.ValueException(node.val)

    def visit_Time(self, node: ast.Time) -> Value:
        ":meta private:"
        try:
            return Value(dt.time.fromisoformat(node.val))
        except ValueError:
            raise ex.ValueException(node.val)

    def visit_Duration(self, node: ast.Duration) -> Value:
        ":meta private:"
        sign, days, hours, minutes, seconds = node.unpack()
        td = dt.timedelta(
            days=float(days or 0),
            hours=float(hours or 0),
            minutes=float(minutes or 0),
            seconds=float(seconds or 0),
        )
        if sign and sign == "-":
            td = -1 * td
        return Value(td)

    def visit_GUID(self, node: ast.GUID) -> Value:
        ":meta private:"
        return uuid.UUID(node.val)

    def visit_List(self, node: ast.List) -> List:
        ":meta private:"
        return [self.visit(n) for n in node.val]

    def visit_Add(self, node: ast.Add) -> Callable[[Any, Any], Any]:
        ":meta private:"
        return operator.add

    def visit_Sub(self, node: ast.Sub) -> Callable[[Any, Any], Any]:
        ":meta private:"
        return operator.sub

    def visit_Mult(self, node: ast.Mult) -> Callable[[Any, Any], Any]:
        ":meta private:"
        return operator.mul

    def visit_Div(self, node: ast.Div) -> Callable[[Any, Any], Any]:
        ":meta private:"
        return operator.truediv

    def visit_Mod(self, node: ast.Mod) -> Callable[[Any, Any], Any]:
        ":meta private:"
        return operator.mod

    def visit_BinOp(self, node: ast.BinOp) -> Any:
        ":meta private:"
        # Left or right can be an Identifier, in which case it needs to be
        # wrapped in F()
        left = self.visit(node.left)
        right = self.visit(node.right)
        op = self.visit(node.op)

        return op(left, right)

    def visit_Eq(self, node: ast.Eq) -> str:
        ":meta private:"
        return "__exact"

    def visit_NotEq(self, node: ast.NotEq) -> str:
        ":meta private:"
        return "__ne"

    def visit_Lt(self, node: ast.Lt) -> str:
        ":meta private:"
        return "__lt"

    def visit_LtE(self, node: ast.LtE) -> str:
        ":meta private:"
        return "__lte"

    def visit_Gt(self, node: ast.Gt) -> str:
        ":meta private:"
        return "__gt"

    def visit_GtE(self, node: ast.GtE) -> str:
        ":meta private:"
        return "__gte"

    def visit_In(self, node: ast.In) -> str:
        ":meta private:"
        return "__in"

    def visit_Compare(self, node: ast.Compare) -> Q:
        ":meta private:"
        # Special case: comparison to NULL => isnull=True/False
        # Should not be wrapped with Value(True/False)
        # See: https://github.com/django/django/blob/0aacbdcf27b258387643b033352e99e6103abda8/django/db/models/lookups.py#L515
        if isinstance(node.right, ast.Null):
            lhs = self._attempt_keywordify(node.left)
            if not lhs:
                raise ex.TypeException(node.comparator.__class__.__name__, "null")
            q_keyword = lhs + "__isnull"
            if isinstance(node.comparator, ast.Eq):
                return Q(**{q_keyword: True})
            elif isinstance(node.comparator, ast.NotEq):
                return Q(**{q_keyword: False})
            else:
                raise ex.TypeException(node.comparator.__class__.__name__, "null")

        # Need an identifier on any side to make a Django Q:
        keyword = self._attempt_keywordify(node.left)
        if not keyword:
            # No keyword on the left, try the right:
            keyword = self._attempt_keywordify(node.right)
            if keyword:
                # Keyword on right, flip the comparison so it's left now:
                node = self._flip_comparison(node)
            else:
                # No keywords at all, cannot continue:
                raise ex.TypeException(
                    node.comparator.__class__.__name__, str(node.left)
                )

        q_keyword = keyword + self.visit(node.comparator)
        query = Q(**{q_keyword: self.visit(node.right)})

        return query

    def visit_And(self, node: ast.And) -> Callable[[Q, Q], Q]:
        ":meta private:"
        return operator.and_

    def visit_Or(self, node: ast.Or) -> Callable[[Q, Q], Q]:
        ":meta private:"
        return operator.or_

    def visit_BoolOp(self, node: ast.BoolOp) -> Q:
        ":meta private:"
        left = self.visit(node.left)
        right = self.visit(node.right)

        if isinstance(left, (F, Value)):
            raise ex.TypeException(node.op.__class__.__name__, left)
        if isinstance(right, (F, Value)):
            raise ex.TypeException(node.op.__class__.__name__, right)

        op = self.visit(node.op)

        return op(left, right)

    def visit_Not(self, node: ast.Not) -> Callable[[Q], Q]:
        ":meta private:"
        return operator.invert

    def visit_UnaryOp(self, node: ast.UnaryOp) -> str:
        ":meta private:"
        mod = self.visit(node.op)
        val = self.visit(node.operand)

        try:
            return mod(val)
        except TypeError:
            raise ex.TypeException(node.op.__class__.__name__, val)

    def visit_Call(self, node: ast.Call) -> Q:
        ":meta private:"
        try:
            q_gen = getattr(self, "djangofunc_" + node.func.name.lower())
        except AttributeError:
            raise ex.UnsupportedFunctionException(node.func.name)

        return q_gen(*node.args)

    def visit_CollectionLambda(self, node: ast.CollectionLambda) -> Q:
        ":meta private:"
        # NOTE: The initial implementation translated to SQL's ANY/ALL keywords,
        # but those behave very differently from OData's any/all keywords!

        owner_path = self._attempt_keywordify(node.owner)
        if not owner_path:
            raise ex.TypeException("lambda_expression", str(node.owner))

        path_to_outerref, related_model = reverse_relationship(
            owner_path, self.root_model
        )
        subquery = related_model.objects.filter(Q(**{path_to_outerref: OuterRef("pk")}))
        # .values(related_field.remote_field.name)

        if node.lambda_:
            # For the lambda, we want to strip the identifier off, because
            # we will execute this as a subquery in the wanted model's context.
            subq_ast = utils.expression_relative_to_identifier(
                node.lambda_.identifier, node.lambda_.expression
            )
            subq_transformer = self.__class__(related_model)
            subquery_filter = subq_transformer.visit(subq_ast)
        else:
            subquery_filter = None

        if isinstance(node.operator, ast.Any):
            # If ANY item should match in the subquery, we can use EXISTS():
            if subquery_filter:
                subquery = subquery.filter(subquery_filter)
            return Exists(subquery)

        elif isinstance(node.operator, ast.All):
            # If ALL items in the collection must match, we invert the condition and use NOT EXISTS():
            if subquery_filter:
                subquery = subquery.filter(~subquery_filter)
            return Exists(subquery, negated=True)

        else:
            raise NotImplementedError()

    def djangofunc_contains(self, field: ast._Node, substr: ast._Node) -> Q:
        ":meta private:"
        return self._substr_function(field, substr, "contains")

    def djangofunc_startswith(self, field: ast._Node, substr: ast._Node) -> Q:
        ":meta private:"
        return self._substr_function(field, substr, "startswith")

    def djangofunc_endswith(self, field: ast._Node, substr: ast._Node) -> Q:
        ":meta private:"
        return self._substr_function(field, substr, "endswith")

    def djangofunc_length(self, arg: ast._Node) -> functions.Length:
        ":meta private:"
        return functions.Length(self.visit(arg))

    def djangofunc_concat(self, *args: ast._Node) -> functions.Concat:
        ":meta private:"
        return functions.Concat(*[self.visit(arg) for arg in args])

    def djangofunc_indexof(
        self, first: ast._Node, second: ast._Node
    ) -> functions.StrIndex:
        ":meta private:"
        # Subtract 1 because OData is 0-indexed while SQL is 1-indexed
        return functions.StrIndex(self.visit(first), self.visit(second)) - 1

    def djangofunc_substring(
        self, fullstr: ast._Node, index: ast._Node, nchars: ast._Node = None
    ) -> functions.Substr:
        ":meta private:"
        # Add 1 because OData is 0-indexed while SQL is 1-indexed
        return functions.Substr(
            self.visit(fullstr),
            self.visit(index) + 1,
            self.visit(nchars) if nchars else None,
        )

    def djangofunc_matchespattern(self, field: ast._Node, pattern: ast._Node) -> Q:
        ":meta private:"
        lhs = self._attempt_keywordify(field)
        if not lhs:
            raise ex.ArgumentTypeException("matchespattern")
        q_keyword = lhs + "__regex"
        pattern = self.visit(pattern)

        return Q(**{q_keyword: pattern})

    def djangofunc_tolower(self, field: ast._Node) -> functions.Lower:
        ":meta private:"
        return functions.Lower(self.visit(field))

    def djangofunc_toupper(self, field: ast._Node) -> functions.Upper:
        ":meta private:"
        return functions.Upper(self.visit(field))

    def djangofunc_trim(self, field: ast._Node) -> functions.Trim:
        ":meta private:"
        return functions.Trim(self.visit(field))

    def djangofunc_date(self, field: ast._Node) -> functions.TruncDate:
        ":meta private:"
        return functions.TruncDate(self.visit(field))

    def djangofunc_day(self, field: ast._Node) -> functions.ExtractDay:
        ":meta private:"
        return functions.ExtractDay(self.visit(field))

    def djangofunc_hour(self, field: ast._Node) -> functions.ExtractHour:
        ":meta private:"
        return functions.ExtractHour(self.visit(field))

    def djangofunc_minute(self, field: ast._Node) -> functions.ExtractMinute:
        ":meta private:"
        return functions.ExtractMinute(self.visit(field))

    def djangofunc_month(self, field: ast._Node) -> functions.ExtractMonth:
        ":meta private:"
        return functions.ExtractMonth(self.visit(field))

    def djangofunc_now(self) -> functions.Now:
        ":meta private:"
        return functions.Now()

    def djangofunc_second(self, field: ast._Node) -> functions.ExtractSecond:
        ":meta private:"
        return functions.ExtractSecond(self.visit(field))

    def djangofunc_time(self, field: ast._Node) -> functions.TruncTime:
        ":meta private:"
        return functions.TruncTime(self.visit(field))

    def djangofunc_year(self, field: ast._Node) -> functions.ExtractYear:
        ":meta private:"
        return functions.ExtractYear(self.visit(field))

    def djangofunc_ceiling(self, field: ast._Node) -> functions.Ceil:
        ":meta private:"
        return functions.Ceil(self.visit(field))

    def djangofunc_floor(self, field: ast._Node) -> functions.Floor:
        ":meta private:"
        return functions.Floor(self.visit(field))

    def djangofunc_round(self, field: ast._Node) -> functions.Round:
        ":meta private:"
        return functions.Round(self.visit(field))

    def _substr_function(
        self, field: ast._Node, substr: ast._Node, django_func: str
    ) -> Q:
        ":meta private:"
        typing.typecheck(field, (ast.Identifier, ast.String), "field")
        typing.typecheck(substr, ast.String, "substring")

        lhs = self._attempt_keywordify(field)
        if not lhs:
            raise ex.ArgumentTypeException(django_func)
        q_keyword = lhs + "__" + django_func
        substring = self.visit(substr)

        return Q(**{q_keyword: substring})

    def _attempt_keywordify(self, node: ast._Node) -> Optional[str]:
        ":meta private:"
        if isinstance(node, ast._Literal):
            return None

        res = self.visit(node)
        if isinstance(res, F):
            return res.name

        if (
            hasattr(res, "lookup_name")
            and hasattr(res, "lhs")
            and hasattr(res.lhs, "name")
        ):
            return res.lhs.name + "__" + res.lookup_name

        # Attempt to make this a QS annotation (SQL alias):
        if isinstance(res, Expression):
            identity = self._gen_annotation_name(res)
            self.queryset_annotations[identity] = res
            return identity

        return None

    def _gen_annotation_name(self, expr: Expression) -> str:
        ":meta private:"
        if hasattr(expr, "name"):
            return expr.name
        elif hasattr(expr, "value"):
            return str(expr.value)

        func_name = expr.__class__.__name__

        try:
            args = expr.get_source_expressions()
        except AttributeError:
            args = []

        args_str = [self._gen_annotation_name(a) for a in args]

        return (
            "_".join([func_name] + args_str)
            .replace(" ", "_")
            .replace(",", "")
            .replace(":", "_")
            .lower()
        )

    @staticmethod
    def _flip_comparison(comp: ast.Compare) -> ast.Compare:
        """
        Flip a comparison left-to-right. E.g.: (4 > version_id) becomes (version_id < 4)

        :meta private:
        """
        new_op = COMPARISON_INVERT[type(comp.comparator)]()
        new_left = comp.right
        new_right = comp.left

        return ast.Compare(new_op, new_left, new_right)
