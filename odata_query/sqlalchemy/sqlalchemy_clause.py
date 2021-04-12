import datetime as dt
import operator
from typing import Any, Callable, Union

from dateutil.parser import isoparse
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
    column,
    extract,
    false,
    literal,
    null,
    or_,
    true,
)
from sqlalchemy.types import Date, Time

from odata_query import ast, exceptions as ex, typing, visitor

from . import functions_ext


class AstToSqlAlchemyClauseVisitor(visitor.NodeVisitor):
    def visit_Identifier(self, node: ast.Identifier) -> ColumnClause:
        return column(node.name)

    def visit_Null(self, node: ast.Null) -> Null:
        return null()

    def visit_Integer(self, node: ast.Integer) -> BindParameter:
        return literal(int(node.val))

    def visit_Float(self, node: ast.Float) -> BindParameter:
        return literal(float(node.val))

    def visit_Boolean(self, node: ast.Boolean) -> Union[True_, False_]:
        if node.val == "true":
            return true()
        else:
            return false()

    def visit_String(self, node: ast.String) -> BindParameter:
        return literal(node.val)

    def visit_Date(self, node: ast.Date) -> BindParameter:
        try:
            return literal(dt.date.fromisoformat(node.val))
        except ValueError:
            raise ex.ValueException(node.val)

    def visit_DateTime(self, node: ast.DateTime) -> BindParameter:
        try:
            return literal(isoparse(node.val))
        except ValueError:
            raise ex.ValueException(node.val)

    def visit_Time(self, node: ast.Time) -> BindParameter:
        try:
            return literal(dt.time.fromisoformat(node.val))
        except ValueError:
            raise ex.ValueException(node.val)

    def visit_Duration(self, node: ast.Duration) -> BindParameter:
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
        return literal(node.val)

    def visit_List(self, node: ast.List) -> list:
        return [self.visit(n) for n in node.val]

    def visit_Add(self, node: ast.Add) -> Callable[[Any, Any], Any]:
        return operator.add

    def visit_Sub(self, node: ast.Sub) -> Callable[[Any, Any], Any]:
        return operator.sub

    def visit_Mult(self, node: ast.Mult) -> Callable[[Any, Any], Any]:
        return operator.mul

    def visit_Div(self, node: ast.Div) -> Callable[[Any, Any], Any]:
        return operator.truediv

    def visit_Mod(self, node: ast.Mod) -> Callable[[Any, Any], Any]:
        return operator.mod

    def visit_BinOp(self, node: ast.BinOp) -> Any:
        left = self.visit(node.left)
        right = self.visit(node.right)
        op = self.visit(node.op)

        return op(left, right)

    def visit_Eq(
        self, node: ast.Eq
    ) -> Callable[[ClauseElement, ClauseElement], BinaryExpression]:
        return operator.eq

    def visit_NotEq(
        self, node: ast.NotEq
    ) -> Callable[[ClauseElement, ClauseElement], BinaryExpression]:
        return operator.ne

    def visit_Lt(
        self, node: ast.Lt
    ) -> Callable[[ClauseElement, ClauseElement], BinaryExpression]:
        return operator.lt

    def visit_LtE(
        self, node: ast.LtE
    ) -> Callable[[ClauseElement, ClauseElement], BinaryExpression]:
        return operator.le

    def visit_Gt(
        self, node: ast.Gt
    ) -> Callable[[ClauseElement, ClauseElement], BinaryExpression]:
        return operator.gt

    def visit_GtE(
        self, node: ast.GtE
    ) -> Callable[[ClauseElement, ClauseElement], BinaryExpression]:
        return operator.ge

    def visit_In(
        self, node: ast.In
    ) -> Callable[[ClauseElement, ClauseElement], BinaryExpression]:
        return lambda a, b: a.in_(b)

    def visit_Compare(self, node: ast.Compare) -> BinaryExpression:
        left = self.visit(node.left)
        right = self.visit(node.right)
        op = self.visit(node.comparator)

        return op(left, right)

    def visit_And(
        self, node: ast.And
    ) -> Callable[[ClauseElement, ClauseElement], BooleanClauseList]:
        return and_

    def visit_Or(
        self, node: ast.Or
    ) -> Callable[[ClauseElement, ClauseElement], BooleanClauseList]:
        return or_

    def visit_BoolOp(self, node: ast.BoolOp) -> BooleanClauseList:
        left = self.visit(node.left)
        right = self.visit(node.right)
        op = self.visit(node.op)
        return op(left, right)

    def visit_Not(self, node: ast.Not) -> Callable[[ClauseElement], ClauseElement]:
        return operator.invert

    def visit_UnaryOp(self, node: ast.UnaryOp) -> ClauseElement:
        mod = self.visit(node.op)
        val = self.visit(node.operand)

        try:
            return mod(val)
        except TypeError:
            raise ex.InvalidUnaryOperandException()

    def visit_Call(self, node: ast.Call) -> ClauseElement:
        try:
            handler = getattr(self, "func_" + node.func.name.lower())
        except AttributeError:
            raise ex.UnsupportedFunctionException(
                f"We do not support the function '{node.func.name}' yet."
            )

        return handler(*node.args)

    def func_contains(self, field: ast._Node, substr: ast._Node) -> ClauseElement:
        return self._substr_function(field, substr, "contains")

    def func_startswith(self, field: ast._Node, substr: ast._Node) -> ClauseElement:
        return self._substr_function(field, substr, "startswith")

    def func_endswith(self, field: ast._Node, substr: ast._Node) -> ClauseElement:
        return self._substr_function(field, substr, "endswith")

    def func_length(self, arg: ast._Node) -> functions.Function:
        return functions.char_length(self.visit(arg))

    def func_concat(self, *args: ast._Node) -> functions.Function:
        return functions.concat(*[self.visit(arg) for arg in args])

    def func_indexof(self, first: ast._Node, second: ast._Node) -> functions.Function:
        # TODO: Highly dialect dependent, might want to implement in GenericFunction:
        # Subtract 1 because OData is 0-indexed while SQL is 1-indexed
        return functions_ext.strpos(self.visit(first), self.visit(second)) - 1

    def func_substring(
        self, fullstr: ast._Node, index: ast._Node, nchars: ast._Node = None
    ) -> functions.Function:
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
        identifier = self.visit(field)
        return identifier.regexp_match(self.visit(pattern))

    def func_tolower(self, field: ast._Node) -> functions.Function:
        return functions_ext.lower(self.visit(field))

    def func_toupper(self, field: ast._Node) -> functions.Function:
        return functions_ext.upper(self.visit(field))

    def func_trim(self, field: ast._Node) -> functions.Function:
        return functions_ext.ltrim(functions_ext.rtrim(self.visit(field)))

    def func_date(self, field: ast._Node) -> ClauseElement:
        return cast(self.visit(field), Date)

    def func_day(self, field: ast._Node) -> functions.Function:
        return extract(self.visit(field), "day")

    def func_hour(self, field: ast._Node) -> functions.Function:
        return extract(self.visit(field), "hour")

    def func_minute(self, field: ast._Node) -> functions.Function:
        return extract(self.visit(field), "minute")

    def func_month(self, field: ast._Node) -> functions.Function:
        return extract(self.visit(field), "month")

    def func_now(self) -> functions.Function:
        return functions.now()

    def func_second(self, field: ast._Node) -> functions.Function:
        return extract(self.visit(field), "second")

    def func_time(self, field: ast._Node) -> functions.Function:
        return cast(self.visit(field), Time)

    def func_year(self, field: ast._Node) -> functions.Function:
        return extract(self.visit(field), "year")

    def func_ceiling(self, field: ast._Node) -> functions.Function:
        return functions_ext.ceil(self.visit(field))

    def func_floor(self, field: ast._Node) -> functions.Function:
        return functions_ext.floor(self.visit(field))

    def func_round(self, field: ast._Node) -> functions.Function:
        return functions_ext.round(self.visit(field))

    def _substr_function(
        self, field: ast._Node, substr: ast._Node, func: str
    ) -> ClauseElement:
        typing.typecheck(field, (ast.Identifier, ast.String), "field")
        typing.typecheck(substr, ast.String, "substring")

        identifier = self.visit(field)
        substring = self.visit(substr)
        op = getattr(identifier, func)

        return op(substring)
