import operator
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, Type, Union
from uuid import UUID

import django
from django.db.models import (
    Case,
    Exists,
    F,
    Model,
    OuterRef,
    Q,
    Value,
    When,
    functions,
    lookups,
)
from django.db.models.expressions import Expression

try:
    # Django gis requires system level libraries, which not every user needs.
    from django.contrib.gis.db.models import functions as gis_functions
    from django.contrib.gis.geos import GEOSGeometry

    _gis_error = None
except Exception as e:
    gis_functions = None
    GEOSGeometry = None
    _gis_error = e

from odata_query import ast, exceptions as ex, typing, utils, visitor

from .django_q_ext import NotEqual
from .utils import reverse_relationship

DJANGO_LT_4 = django.VERSION[0] < 4

COMPARISON_FLIP = {
    lookups.Exact: lookups.Exact,
    NotEqual: NotEqual,
    lookups.LessThan: lookups.GreaterThan,
    lookups.LessThanOrEqual: lookups.GreaterThanOrEqual,
    lookups.GreaterThan: lookups.LessThan,
    lookups.GreaterThanOrEqual: lookups.LessThanOrEqual,
    ast.Eq: ast.Eq,
    ast.NotEq: ast.NotEq,
    ast.Lt: ast.Gt,
    ast.LtE: ast.GtE,
    ast.Gt: ast.Lt,
    ast.GtE: ast.LtE,
}


def requires_gis(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not gis_functions:
            raise ImportError(
                "Cannot use geography functions because GeoDjango failed to load."
            ) from _gis_error
        return func(*args, **kwargs)

    return wrapper


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

        # Keep track of the depth of `visit` calls, so we know when we should
        # turn the Django expression into a final `Q` object.
        self._depth: int = 0

    def visit(self, node: ast._Node) -> Any:
        """:meta private:"""
        self._depth += 1
        res = super().visit(node)
        self._depth -= 1

        if self._depth == 0:
            res = self._ensure_q(res)

        return res

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
        return Value(node.py_val)

    def visit_Float(self, node: ast.Float) -> Value:
        ":meta private:"
        return Value(node.py_val)

    def visit_Boolean(self, node: ast.Boolean) -> Value:
        ":meta private:"
        return Value(node.py_val)

    def visit_String(self, node: ast.String) -> Value:
        ":meta private:"
        return Value(node.py_val)

    def visit_Date(self, node: ast.Date) -> Value:
        ":meta private:"
        try:
            return Value(node.py_val)
        except ValueError:
            raise ex.ValueException(node.val)

    def visit_DateTime(self, node: ast.DateTime) -> Value:
        ":meta private:"
        try:
            return Value(node.py_val)
        except ValueError:
            raise ex.ValueException(node.val)

    def visit_Time(self, node: ast.Time) -> Value:
        ":meta private:"
        try:
            return Value(node.py_val)
        except ValueError:
            raise ex.ValueException(node.val)

    def visit_Duration(self, node: ast.Duration) -> Value:
        ":meta private:"
        return Value(node.py_val)

    def visit_GUID(self, node: ast.GUID) -> Value:
        ":meta private:"
        return Value(node.py_val)

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

    def visit_Eq(self, node: ast.Eq) -> Type[lookups.Lookup]:
        ":meta private:"
        return lookups.Exact

    def visit_NotEq(self, node: ast.NotEq) -> Type[lookups.Lookup]:
        ":meta private:"
        return NotEqual

    def visit_Lt(self, node: ast.Lt) -> Type[lookups.Lookup]:
        ":meta private:"
        return lookups.LessThan

    def visit_LtE(self, node: ast.LtE) -> Type[lookups.Lookup]:
        ":meta private:"
        return lookups.LessThanOrEqual

    def visit_Gt(self, node: ast.Gt) -> Type[lookups.Lookup]:
        ":meta private:"
        return lookups.GreaterThan

    def visit_GtE(self, node: ast.GtE) -> Type[lookups.Lookup]:
        ":meta private:"
        return lookups.GreaterThanOrEqual

    def visit_In(self, node: ast.In) -> Type[lookups.Lookup]:
        ":meta private:"
        return lookups.In

    def visit_Compare(self, node: ast.Compare) -> lookups.Lookup:
        ":meta private:"
        lhs = self.visit(node.left)

        # Special case: comparison to NULL => isnull=True/False
        # Should not be wrapped with Value(True/False)
        # See: https://github.com/django/django/blob/0aacbdcf27b258387643b033352e99e6103abda8/django/db/models/lookups.py#L515
        if isinstance(node.right, ast.Null):
            if isinstance(node.comparator, ast.Eq):
                return lookups.IsNull(lhs, True)
            elif isinstance(node.comparator, ast.NotEq):
                return lookups.IsNull(lhs, False)
            else:
                raise ex.TypeException(node.comparator.__class__.__name__, "null")

        django_cls = self.visit(node.comparator)
        rhs = self.visit(node.right)

        return django_cls(lhs, rhs)

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

        if DJANGO_LT_4:
            left = self._ensure_q(left)
            right = self._ensure_q(right)

        op = self.visit(node.op)

        return op(left, right)

    def visit_Not(self, node: ast.Not) -> Callable[[Q], Q]:
        ":meta private:"
        return operator.invert

    def visit_UnaryOp(self, node: ast.UnaryOp) -> str:
        ":meta private:"
        mod = self.visit(node.op)
        val = self.visit(node.operand)

        # Can only apply `~` to Q objects:
        val = self._ensure_q(val)

        try:
            return mod(val)
        except TypeError:
            raise ex.TypeException(node.op.__class__.__name__, val)

    def visit_Call(self, node: ast.Call) -> Union[Expression, Q]:
        ":meta private:"

        func_name = node.func.full_name().replace(".", "__")

        try:
            q_gen = getattr(self, "djangofunc_" + func_name.lower())
        except AttributeError:
            raise ex.UnsupportedFunctionException(func_name)

        args = []
        kwargs = {}
        for arg in node.args:
            if isinstance(arg, ast.NamedParam):
                kwargs[arg.name.name] = arg.param
            else:
                args.append(arg)

        res = q_gen(*args, **kwargs)
        return res

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

    @requires_gis
    def djangofunc_geo__intersects(
        self, field: ast.Identifier, geography: ast.Geography
    ):
        return Q(**{field.name + "__" + "intersects": GEOSGeometry(geography.wkt())})

    @requires_gis
    def djangofunc_geo__distance(self, field: ast.Identifier, geography: ast.Geography):
        return gis_functions.Distance(field.name, GEOSGeometry(geography.wkt()))

    @requires_gis
    def djangofunc_geo__length(self, field: ast.Identifier):
        return gis_functions.Length(field.name)

    def djangofunc_contains(
        self, field: ast._Node, substr: ast._Node
    ) -> lookups.Contains:
        ":meta private:"
        return self._substr_function(field, substr, lookups.Contains)

    def djangofunc_startswith(
        self, field: ast._Node, substr: ast._Node
    ) -> lookups.StartsWith:
        ":meta private:"
        return self._substr_function(field, substr, lookups.StartsWith)

    def djangofunc_endswith(
        self, field: ast._Node, substr: ast._Node
    ) -> lookups.EndsWith:
        ":meta private:"
        return self._substr_function(field, substr, lookups.EndsWith)

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
        self, fullstr: ast._Node, index: ast._Node, nchars: Optional[ast._Node] = None
    ) -> functions.Substr:
        ":meta private:"
        # Add 1 because OData is 0-indexed while SQL is 1-indexed
        return functions.Substr(
            self.visit(fullstr),
            self.visit(index) + 1,
            self.visit(nchars) if nchars else None,
        )

    def djangofunc_matchespattern(
        self, field: ast._Node, pattern: ast._Node
    ) -> lookups.Regex:
        ":meta private:"
        return lookups.Regex(self.visit(field), self.visit(pattern))

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
        self, field: ast._Node, substr: ast._Node, django_func: Type[Expression]
    ) -> Expression:
        ":meta private:"
        typing.typecheck(field, (ast.Identifier, ast.String), "field")
        typing.typecheck(substr, ast.String, "substring")

        return django_func(self.visit(field), self.visit(substr))

    def _fix_uuid(self, node: Any) -> Any:
        # Workaround for Django <4 'Value is not a valid UUID':
        if isinstance(node, Value) and isinstance(node.value, UUID):
            return node.value

        if isinstance(node, list):
            return [self._fix_uuid(i) for i in node]

        return node

    def _ensure_q(self, node: Any) -> Q:
        """
        Turn a given Django `Lookup`, `Expression` or `Function` into a `Q` object.
        This is mainly necessary for Django <4 where the nodes cannot be directly
        used in `Q` objects and have to be expressed as `Q(keyword=value)`.
        """
        if isinstance(node, (Q, Exists)):
            return node

        if not DJANGO_LT_4:
            return Q(node)

        # Need an identifier on any side to make a Django Q:
        keyword = self._attempt_keywordify(node.lhs)
        if not keyword:
            # No keyword on the left, try the right:
            keyword = self._attempt_keywordify(node.rhs)
            if keyword:
                node = self._flip_comparison(node)
            else:
                # No keywords at all, cannot continue:
                raise ex.TypeException(node.__class__.__name__, str(node.lhs))

        if isinstance(node, lookups.Lookup):
            keyword += "__" + node.lookup_name

        node.rhs = self._fix_uuid(node.rhs)
        query = Q(**{keyword: node.rhs})
        return query

    def _attempt_keywordify(self, node: Any) -> Optional[str]:
        """
        Try to turn ``node`` into a keyword argument that can be used in a Django
        ``Q`` object. E.g. a ``contains(name, 'something')`` node should resolve
        to the keyword ``name__contains``.

        :meta private:
        """
        # A literal can not be expressed as a keyword.
        if isinstance(node, (ast._Literal, Value)):
            return None

        # If an AST Node was passed, visit it to get something Django related:
        if isinstance(node, ast._Node):
            res = self.visit(node)
        else:
            res = node

        # If `res` is already wrapped in a `Q` object, we need to unwrap it first.
        # This is the case with expressions that are filterable by themselves,
        # such as `contains(a, b)`.
        if isinstance(res, Q) and isinstance(res.children[0], Expression):
            res = res.children[0]

        # An `F` expression is a field or expression known to Django, and can
        # be used as a keyword.
        if isinstance(res, F):
            return res.name

        # Field lookups are also easily expressed as keywords.
        if (
            hasattr(res, "lookup_name")
            and hasattr(res, "lhs")
            and hasattr(res.lhs, "name")
            # Expressions with a `rhs` have parameters and should be handled
            # as function calls:
            and not getattr(res, "rhs", False)
        ):
            return res.lhs.name + "__" + res.lookup_name

        # Lookups with parameters need to be wrapped in a `CASE WHEN` expression
        if isinstance(res, lookups.Lookup):
            identity = self._gen_annotation_name(res)
            if DJANGO_LT_4:
                res = self._ensure_q(res)
            res = Case(When(res, then=True), default=False)
            self.queryset_annotations[identity] = res
            return identity

        # For more complicated expressions, we can add them to the query as a
        # QuerySet annotation. This annotation is then valid as a keyword:
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
    def _flip_comparison(comp: lookups.Lookup) -> lookups.Lookup:
        """
        Flip a comparison left-to-right. E.g.: (4 > version_id) becomes (version_id < 4)

        :meta private:
        """
        new_op = COMPARISON_FLIP[type(comp)]
        new_left = comp.rhs
        new_right = comp.lhs

        return new_op(new_left, new_right)
