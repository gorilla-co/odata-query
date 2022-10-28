import operator
from typing import Any, Callable, Optional, Union

from sqlalchemy.sql import functions
from sqlalchemy.sql.expression import (
    BinaryExpression,
    BindParameter,
    BooleanClauseList,
    ClauseElement,
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

from odata_query import ast, exceptions as ex, typing, visitor

from . import functions_ext


class _CommonVisitors(visitor.NodeVisitor):
    """
    Contains the visitor methods that are equal between SQLAlchemy Core and ORM.
    """

    def visit_Null(self, node: ast.Null) -> Null:
        ":meta private:"
        return null()

    def visit_Integer(self, node: ast.Integer) -> BindParameter:
        ":meta private:"
        return literal(node.py_val)

    def visit_Float(self, node: ast.Float) -> BindParameter:
        ":meta private:"
        return literal(node.py_val)

    def visit_Boolean(self, node: ast.Boolean) -> Union[True_, False_]:
        ":meta private:"
        if node.val == "true":
            return true()
        else:
            return false()

    def visit_String(self, node: ast.String) -> BindParameter:
        ":meta private:"
        return literal(node.py_val)

    def visit_Date(self, node: ast.Date) -> BindParameter:
        ":meta private:"
        try:
            return literal(node.py_val)
        except ValueError:
            raise ex.ValueException(node.val)

    def visit_DateTime(self, node: ast.DateTime) -> BindParameter:
        ":meta private:"
        try:
            return literal(node.py_val)
        except ValueError:
            raise ex.ValueException(node.val)

    def visit_Time(self, node: ast.Time) -> BindParameter:
        ":meta private:"
        try:
            return literal(node.py_val)
        except ValueError:
            raise ex.ValueException(node.val)

    def visit_Duration(self, node: ast.Duration) -> BindParameter:
        ":meta private:"
        return literal(node.py_val)

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
        self, fullstr: ast._Node, index: ast._Node, nchars: Optional[ast._Node] = None
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
        return extract("day", self.visit(field))

    def func_hour(self, field: ast._Node) -> functions.Function:
        ":meta private:"
        return extract("hour", self.visit(field))

    def func_minute(self, field: ast._Node) -> functions.Function:
        ":meta private:"
        return extract("minute", self.visit(field))

    def func_month(self, field: ast._Node) -> functions.Function:
        ":meta private:"
        return extract("month", self.visit(field))

    def func_now(self) -> functions.Function:
        ":meta private:"
        return functions.now()

    def func_second(self, field: ast._Node) -> functions.Function:
        ":meta private:"
        return extract("second", self.visit(field))

    def func_time(self, field: ast._Node) -> functions.Function:
        ":meta private:"
        return cast(self.visit(field), Time)

    def func_year(self, field: ast._Node) -> functions.Function:
        ":meta private:"
        return extract("year", self.visit(field))

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
