import datetime as dt
import operator
from typing import Callable, Union

from dateutil.parser import isoparse
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
    column,
    false,
    literal,
    null,
    or_,
    true,
)

from odata_query import ast, exceptions as ex, visitor


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
