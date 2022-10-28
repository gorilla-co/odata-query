import sys
from typing import Type

if sys.version_info >= (3, 8):
    from typing import Protocol
else:
    from typing_extensions import Protocol

from odata_query import ast, visitor


class LiteralValNode(Protocol):
    """:meta private:"""

    val: str


PRECEDENCE = {
    ast.Attribute: 10,
    ast.Call: 10,
    ast.Not: 9,
    ast.USub: 9,
    ast.Mult: 8,
    ast.Div: 8,
    ast.Mod: 8,
    ast.Add: 7,
    ast.Sub: 7,
    ast.Gt: 6,
    ast.GtE: 6,
    ast.Lt: 6,
    ast.LtE: 6,
    ast.Eq: 5,
    ast.NotEq: 5,
    ast.And: 4,
    ast.Or: 3,
}


class AstToODataVisitor(visitor.NodeVisitor):
    """
    :class:`NodeVisitor` that transforms an :term:`AST` back into an OData
    query string.
    """

    def visit_Identifier(self, node: ast.Identifier) -> str:
        """:meta private:"""
        if node.namespace:
            prefix = ".".join(node.namespace)
            return prefix + "." + node.name
        return node.name

    def visit_Attribute(self, node: ast.Attribute) -> str:
        """:meta private:"""
        return self.visit(node.owner) + "/" + node.attr

    def visit_Null(self, node: ast.Null) -> str:
        """:meta private:"""
        return "null"

    def visit_String(self, node: ast.String) -> str:
        """:meta private:"""
        return "'" + node.val + "'"

    def visit_Duration(self, node: ast.Duration) -> str:
        """:meta private:"""
        return "duration'" + node.val + "'"

    def _visit_Literal(self, node: LiteralValNode) -> str:
        """:meta private:"""
        return node.val

    visit_Integer = _visit_Literal
    visit_Float = _visit_Literal
    visit_Boolean = _visit_Literal
    visit_Date = _visit_Literal
    visit_Time = _visit_Literal
    visit_DateTime = _visit_Literal
    visit_GUID = _visit_Literal

    def visit_List(self, node: ast.List) -> str:
        """:meta private:"""
        return "(" + ", ".join(self.visit(v) for v in node.val) + ")"

    def visit_Add(self, node: ast.Add) -> str:
        """:meta private:"""
        return "add"

    def visit_Sub(self, node: ast.Sub) -> str:
        """:meta private:"""
        return "sub"

    def visit_Mult(self, node: ast.Mult) -> str:
        """:meta private:"""
        return "mul"

    def visit_Div(self, node: ast.Div) -> str:
        """:meta private:"""
        return "div"

    def visit_Mod(self, node: ast.Mod) -> str:
        """:meta private:"""
        return "mod"

    def visit_BinOp(self, node: ast.BinOp) -> str:
        """:meta private:"""
        left = self._visit_and_paren_if_precedence_lower(node.left, type(node.op))
        right = self._visit_and_paren_if_precedence_lower(node.right, type(node.op))
        return left + " " + self.visit(node.op) + " " + right

    def visit_Eq(self, node: ast.Eq) -> str:
        """:meta private:"""
        return "eq"

    def visit_NotEq(self, node: ast.NotEq) -> str:
        """:meta private:"""
        return "ne"

    def visit_Lt(self, node: ast.Lt) -> str:
        """:meta private:"""
        return "lt"

    def visit_LtE(self, node: ast.LtE) -> str:
        """:meta private:"""
        return "le"

    def visit_Gt(self, node: ast.Gt) -> str:
        """:meta private:"""
        return "gt"

    def visit_GtE(self, node: ast.GtE) -> str:
        """:meta private:"""
        return "ge"

    def visit_In(self, node: ast.In) -> str:
        """:meta private:"""
        return "in"

    def visit_Compare(self, node: ast.Compare) -> str:
        """:meta private:"""
        left = self._visit_and_paren_if_precedence_lower(
            node.left, type(node.comparator)
        )
        right = self._visit_and_paren_if_precedence_lower(
            node.right, type(node.comparator)
        )
        return left + " " + self.visit(node.comparator) + " " + right

    def visit_And(self, node: ast.And) -> str:
        """:meta private:"""
        return "and"

    def visit_Or(self, node: ast.Or) -> str:
        """:meta private:"""
        return "or"

    def visit_BoolOp(self, node: ast.BoolOp) -> str:
        """:meta private:"""
        left = self._visit_and_paren_if_precedence_lower(node.left, type(node.op))
        right = self._visit_and_paren_if_precedence_lower(node.right, type(node.op))
        return left + " " + self.visit(node.op) + " " + right

    def visit_Not(self, node: ast.Not) -> str:
        """:meta private:"""
        return "not"

    def visit_USub(self, node: ast.USub) -> str:
        """:meta private:"""
        return "-"

    def visit_UnaryOp(self, node: ast.UnaryOp) -> str:
        """:meta private:"""
        operand = self._visit_and_paren_if_precedence_lower(node.operand, type(node.op))
        return self.visit(node.op) + " " + operand

    def visit_Call(self, node: ast.Call) -> str:
        """:meta private:"""
        return (
            self.visit(node.func)
            + "("
            + ", ".join(self.visit(n) for n in node.args)
            + ")"
        )

    def visit_Any(self, node: ast.Any) -> str:
        """:meta private:"""
        return "any"

    def visit_All(self, node: ast.All) -> str:
        """:meta private:"""
        return "all"

    def visit_Lambda(self, node: ast.Lambda) -> str:
        """:meta private:"""
        return self.visit(node.identifier) + ": " + self.visit(node.expression)

    def visit_CollectionLambda(self, node: ast.CollectionLambda) -> str:
        """:meta private:"""
        return (
            self.visit(node.owner)
            + "/"
            + self.visit(node.operator)
            + "("
            + (self.visit(node.lambda_) if node.lambda_ else "")
            + ")"
        )

    def _visit_and_paren_if_precedence_lower(
        self, node: ast._Node, precedence: Type[ast._Node]
    ) -> str:
        """
        Transform `node` by visiting it, then wrap the result in parentheses if
        the expressions precedence is lower than that of `precedence`.

        :meta private:
        """
        res = self.visit(node)

        if hasattr(node, "op"):
            node_op = type(node.op)  # type: ignore
        elif hasattr(node, "comparator"):
            node_op = type(node.comparator)  # type: ignore
        else:
            node_op = type(node)

        node_prec = PRECEDENCE.get(node_op, 100)
        check_prec = PRECEDENCE.get(precedence, 100)

        if node_prec < check_prec:
            res = "(" + res + ")"

        return res
