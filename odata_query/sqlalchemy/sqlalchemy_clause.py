import datetime as dt
import operator
from typing import Any, Callable, List, Type, Union

from dateutil.parser import isoparse
from sqlalchemy.inspection import inspect
from sqlalchemy.orm.attributes import InstrumentedAttribute
from sqlalchemy.orm.decl_api import DeclarativeMeta
from sqlalchemy.orm.relationships import RelationshipProperty
from sqlalchemy.sql import functions
from sqlalchemy.sql.expression import (
    BinaryExpression,
    BindParameter,
    BooleanClauseList,
    ClauseElement,
    ColumnClause,
    False_,
    Null,
    True_,
    and_,
    cast,
    extract,
    false,
    literal,
    null,
    or_,
    true,
)
from sqlalchemy.types import Date, Time

from odata_query import ast, exceptions as ex, typing, utils, visitor

from . import functions_ext


class AstToSqlAlchemyClauseVisitor(visitor.NodeVisitor):
    """
    :class:`NodeVisitor` that transforms an :term:`AST` into a SQLAlchemy query
    filter clause.

    Args:
        root_model: The root model of the query.
    """

    def __init__(self, root_model: Type[DeclarativeMeta]):
        self.root_model = root_model
        self.join_relationships: List[InstrumentedAttribute] = []

    def visit_Identifier(self, node: ast.Identifier) -> ColumnClause:
        ":meta private:"
        try:
            return getattr(self.root_model, node.name)
        except AttributeError:
            raise ex.InvalidFieldException(node.name)

    def visit_Attribute(self, node: ast.Attribute) -> ColumnClause:
        ":meta private:"
        rel_attr = self.visit(node.owner)
        # Owner is an InstrumentedAttribute, hopefully of a relationship.
        # But we need the model pointed to by the relationship.
        prop_inspect = inspect(rel_attr).property
        if not isinstance(prop_inspect, RelationshipProperty):
            # TODO: new exception:
            raise ValueError(f"Not a relationship: {node.owner}")
        self.join_relationships.append(rel_attr)

        # We'd like to reference the column on the related class:
        owner_cls = prop_inspect.entity.class_
        try:
            return getattr(owner_cls, node.attr)
        except AttributeError:
            raise ex.InvalidFieldException(node.attr)

    def visit_Null(self, node: ast.Null) -> Null:
        ":meta private:"
        return null()

    def visit_Integer(self, node: ast.Integer) -> BindParameter:
        ":meta private:"
        return literal(int(node.val))

    def visit_Float(self, node: ast.Float) -> BindParameter:
        ":meta private:"
        return literal(float(node.val))

    def visit_Boolean(self, node: ast.Boolean) -> Union[True_, False_]:
        ":meta private:"
        if node.val == "true":
            return true()
        else:
            return false()

    def visit_String(self, node: ast.String) -> BindParameter:
        ":meta private:"
        return literal(node.val)

    def visit_Date(self, node: ast.Date) -> BindParameter:
        ":meta private:"
        try:
            return literal(dt.date.fromisoformat(node.val))
        except ValueError:
            raise ex.ValueException(node.val)

    def visit_DateTime(self, node: ast.DateTime) -> BindParameter:
        ":meta private:"
        try:
            return literal(isoparse(node.val))
        except ValueError:
            raise ex.ValueException(node.val)

    def visit_Time(self, node: ast.Time) -> BindParameter:
        ":meta private:"
        try:
            return literal(dt.time.fromisoformat(node.val))
        except ValueError:
            raise ex.ValueException(node.val)

    def visit_Duration(self, node: ast.Duration) -> BindParameter:
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
        return literal(td)

    def visit_GUID(self, node: ast.GUID) -> BindParameter:
        ":meta private:"
        return literal(node.val)

    def visit_List(self, node: ast.List) -> list:
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
        left = self.visit(node.left)
        right = self.visit(node.right)
        op = self.visit(node.op)

        return op(left, right)

    def visit_Eq(
        self, node: ast.Eq
    ) -> Callable[[ClauseElement, ClauseElement], BinaryExpression]:
        ":meta private:"
        return operator.eq

    def visit_NotEq(
        self, node: ast.NotEq
    ) -> Callable[[ClauseElement, ClauseElement], BinaryExpression]:
        ":meta private:"
        return operator.ne

    def visit_Lt(
        self, node: ast.Lt
    ) -> Callable[[ClauseElement, ClauseElement], BinaryExpression]:
        ":meta private:"
        return operator.lt

    def visit_LtE(
        self, node: ast.LtE
    ) -> Callable[[ClauseElement, ClauseElement], BinaryExpression]:
        ":meta private:"
        return operator.le

    def visit_Gt(
        self, node: ast.Gt
    ) -> Callable[[ClauseElement, ClauseElement], BinaryExpression]:
        ":meta private:"
        return operator.gt

    def visit_GtE(
        self, node: ast.GtE
    ) -> Callable[[ClauseElement, ClauseElement], BinaryExpression]:
        ":meta private:"
        return operator.ge

    def visit_In(
        self, node: ast.In
    ) -> Callable[[ClauseElement, ClauseElement], BinaryExpression]:
        ":meta private:"
        return lambda a, b: a.in_(b)

    def visit_Compare(self, node: ast.Compare) -> BinaryExpression:
        ":meta private:"
        left = self.visit(node.left)
        right = self.visit(node.right)
        op = self.visit(node.comparator)

        # If a node is a `relationship` representing a single foreign key,
        # the client meant to compare the foreign key, not the related object.
        # E.g. In "blogpost/author eq 1", left should be "blogpost/author_id"
        left = self._maybe_sub_relationship_with_foreign_key(left)
        right = self._maybe_sub_relationship_with_foreign_key(right)

        return op(left, right)

    def visit_And(
        self, node: ast.And
    ) -> Callable[[ClauseElement, ClauseElement], BooleanClauseList]:
        ":meta private:"
        return and_

    def visit_Or(
        self, node: ast.Or
    ) -> Callable[[ClauseElement, ClauseElement], BooleanClauseList]:
        ":meta private:"
        return or_

    def visit_BoolOp(self, node: ast.BoolOp) -> BooleanClauseList:
        ":meta private:"
        left = self.visit(node.left)
        right = self.visit(node.right)
        op = self.visit(node.op)
        return op(left, right)

    def visit_Not(self, node: ast.Not) -> Callable[[ClauseElement], ClauseElement]:
        ":meta private:"
        return operator.invert

    def visit_UnaryOp(self, node: ast.UnaryOp) -> ClauseElement:
        ":meta private:"
        mod = self.visit(node.op)
        val = self.visit(node.operand)

        try:
            return mod(val)
        except TypeError:
            raise ex.TypeException(node.op.__class__.__name__, val)

    def visit_Call(self, node: ast.Call) -> ClauseElement:
        ":meta private:"
        try:
            handler = getattr(self, "func_" + node.func.name.lower())
        except AttributeError:
            raise ex.UnsupportedFunctionException(node.func.name)

        return handler(*node.args)

    def visit_CollectionLambda(self, node: ast.CollectionLambda):
        ":meta private:"
        owner_prop = self.visit(node.owner)
        collection_model = inspect(owner_prop).property.entity.class_

        if node.lambda_:
            # For the lambda, we want to strip the identifier off, because
            # we will execute this as a subquery in the wanted model's context.
            subq_ast = utils.expression_relative_to_identifier(
                node.lambda_.identifier, node.lambda_.expression
            )
            subq_transformer = self.__class__(collection_model)
            subquery_filter = subq_transformer.visit(subq_ast)
        else:
            subquery_filter = None

        if isinstance(node.operator, ast.Any):
            return owner_prop.any(subquery_filter)
        else:
            # For an ALL query, invert both the filter and the EXISTS:
            if node.lambda_:
                subquery_filter = ~subquery_filter
            return ~owner_prop.any(subquery_filter)

    def func_contains(self, field: ast._Node, substr: ast._Node) -> ClauseElement:
        ":meta private:"
        return self._substr_function(field, substr, "contains")

    def func_startswith(self, field: ast._Node, substr: ast._Node) -> ClauseElement:
        ":meta private:"
        return self._substr_function(field, substr, "startswith")

    def func_endswith(self, field: ast._Node, substr: ast._Node) -> ClauseElement:
        ":meta private:"
        return self._substr_function(field, substr, "endswith")

    def func_length(self, arg: ast._Node) -> functions.Function:
        ":meta private:"
        return functions.char_length(self.visit(arg))

    def func_concat(self, *args: ast._Node) -> functions.Function:
        ":meta private:"
        return functions.concat(*[self.visit(arg) for arg in args])

    def func_indexof(self, first: ast._Node, second: ast._Node) -> functions.Function:
        ":meta private:"
        # TODO: Highly dialect dependent, might want to implement in GenericFunction:
        # Subtract 1 because OData is 0-indexed while SQL is 1-indexed
        return functions_ext.strpos(self.visit(first), self.visit(second)) - 1

    def func_substring(
        self, fullstr: ast._Node, index: ast._Node, nchars: ast._Node = None
    ) -> functions.Function:
        ":meta private:"
        # Add 1 because OData is 0-indexed while SQL is 1-indexed
        if nchars:
            return functions_ext.substr(
                self.visit(fullstr),
                self.visit(index) + 1,
                self.visit(nchars),
            )
        else:
            return functions_ext.substr(self.visit(fullstr), self.visit(index) + 1)

    def func_matchespattern(
        self, field: ast._Node, pattern: ast._Node
    ) -> functions.Function:
        ":meta private:"
        identifier = self.visit(field)
        return identifier.regexp_match(self.visit(pattern))

    def func_tolower(self, field: ast._Node) -> functions.Function:
        ":meta private:"
        return functions_ext.lower(self.visit(field))

    def func_toupper(self, field: ast._Node) -> functions.Function:
        ":meta private:"
        return functions_ext.upper(self.visit(field))

    def func_trim(self, field: ast._Node) -> functions.Function:
        ":meta private:"
        return functions_ext.ltrim(functions_ext.rtrim(self.visit(field)))

    def func_date(self, field: ast._Node) -> ClauseElement:
        ":meta private:"
        return cast(self.visit(field), Date)

    def func_day(self, field: ast._Node) -> functions.Function:
        ":meta private:"
        return extract(self.visit(field), "day")

    def func_hour(self, field: ast._Node) -> functions.Function:
        ":meta private:"
        return extract(self.visit(field), "hour")

    def func_minute(self, field: ast._Node) -> functions.Function:
        ":meta private:"
        return extract(self.visit(field), "minute")

    def func_month(self, field: ast._Node) -> functions.Function:
        ":meta private:"
        return extract(self.visit(field), "month")

    def func_now(self) -> functions.Function:
        ":meta private:"
        return functions.now()

    def func_second(self, field: ast._Node) -> functions.Function:
        ":meta private:"
        return extract(self.visit(field), "second")

    def func_time(self, field: ast._Node) -> functions.Function:
        ":meta private:"
        return cast(self.visit(field), Time)

    def func_year(self, field: ast._Node) -> functions.Function:
        ":meta private:"
        return extract(self.visit(field), "year")

    def func_ceiling(self, field: ast._Node) -> functions.Function:
        ":meta private:"
        return functions_ext.ceil(self.visit(field))

    def func_floor(self, field: ast._Node) -> functions.Function:
        ":meta private:"
        return functions_ext.floor(self.visit(field))

    def func_round(self, field: ast._Node) -> functions.Function:
        ":meta private:"
        return functions_ext.round(self.visit(field))

    def _substr_function(
        self, field: ast._Node, substr: ast._Node, func: str
    ) -> ClauseElement:
        ":meta private:"
        typing.typecheck(field, (ast.Identifier, ast.String), "field")
        typing.typecheck(substr, ast.String, "substring")

        identifier = self.visit(field)
        substring = self.visit(substr)
        op = getattr(identifier, func)

        return op(substring)

    def _maybe_sub_relationship_with_foreign_key(
        self, elem: ClauseElement
    ) -> ClauseElement:
        """
        If the given ClauseElement is a `relationship` with a single ForeignKey,
        replace it with the `ForeignKey` itself.

        :meta private:
        """
        try:
            prop_inspect = inspect(elem).property
            if isinstance(prop_inspect, RelationshipProperty):
                foreign_key = prop_inspect._calculated_foreign_keys
                if len(foreign_key) == 1:
                    return next(iter(foreign_key))
        except Exception:
            pass

        return elem
