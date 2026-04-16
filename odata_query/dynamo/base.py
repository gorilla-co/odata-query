"""DynamoDB backend for odata-query.

Converts OData $filter ASTs directly to boto3 ``ConditionBase`` objects
without using ``eval()``.

Example::

    from odata_query.dynamo import apply_odata_query

    condition = apply_odata_query("status eq 'active' and age gt 18")
    # Returns: Attr('status').eq('active') & Attr('age').gt(18)

    response = table.query(
        KeyConditionExpression=Key('pk').eq('user#tenant1'),
        FilterExpression=condition,
    )
"""

from __future__ import annotations

from boto3.dynamodb.conditions import Attr, ConditionBase

from .. import ast, exceptions, visitor
from ..grammar import parse_odata


class AstToDynamoConditionVisitor(visitor.NodeVisitor):
    """Build boto3 DynamoDB conditions directly from the OData AST.

    Unlike the string-building visitors used by other backends, this visitor
    returns live boto3 ``ConditionBase`` objects at every node — no
    ``eval()`` required.
    """

    def visit_Identifier(self, node: ast.Identifier) -> str:
        ":meta private:"
        return ".".join((*node.namespace, node.name)) if node.namespace else node.name

    def visit_Attribute(self, node: ast.Attribute) -> str:
        ":meta private:"
        owner = self.visit(node.owner)
        return f"{owner}.{node.attr}"

    def visit_Integer(self, node: ast.Integer) -> int:
        ":meta private:"
        return node.py_val

    def visit_Float(self, node: ast.Float) -> float:
        ":meta private:"
        return node.py_val

    def visit_Boolean(self, node: ast.Boolean) -> bool:
        ":meta private:"
        return node.py_val

    def visit_String(self, node: ast.String) -> str:
        ":meta private:"
        return node.py_val

    def visit_Null(self, node: ast.Null) -> None:
        ":meta private:"
        return None

    def visit_GUID(self, node: ast.GUID):
        ":meta private:"
        return node.py_val

    def visit_Date(self, node: ast.Date):
        ":meta private:"
        return node.py_val

    def visit_Time(self, node: ast.Time):
        ":meta private:"
        return node.py_val

    def visit_DateTime(self, node: ast.DateTime):
        ":meta private:"
        return node.py_val

    def visit_Duration(self, node: ast.Duration):
        ":meta private:"
        return node.py_val

    def visit_List(self, node: ast.List) -> list:
        ":meta private:"
        return [self.visit(item) for item in node.val]

    def visit_Function(self, node: ast.Function) -> ConditionBase:
        ":meta private:"
        field_name = self._field_name(node.left)
        if isinstance(node.function, ast.Exists):
            return Attr(field_name).exists()
        if isinstance(node.function, ast.Not_Exists):
            return Attr(field_name).not_exists()
        raise exceptions.UnsupportedFunctionException(type(node.function).__name__)

    def visit_Compare(self, node: ast.Compare) -> ConditionBase:
        ":meta private:"
        field_name = self._field_name(node.left)
        field = Attr(field_name)

        # DynamoDB has two distinct "no value" states:
        #   State 1 - attribute is absent (never stored / deleted)
        #   State 2 - attribute exists with DynamoDB NULL type
        #
        # 'field eq null' -> absent OR null-typed   (covers both states)
        # 'field ne null' -> exists AND not null-typed  (has a real value)
        if isinstance(node.right, ast.Null):
            if isinstance(node.comparator, ast.Eq):
                return field.not_exists() | field.attribute_type("NULL")
            if isinstance(node.comparator, ast.NotEq):
                return field.exists() & ~field.attribute_type("NULL")

        if isinstance(node.comparator, ast.Between):
            values = self.visit(node.right)
            if not isinstance(values, list) or len(values) != 2:
                raise exceptions.ArgumentTypeException("between", "two-item list")
            return field.between(values[0], values[1])

        value = self.visit(node.right)
        if isinstance(node.comparator, ast.Eq):
            return field.eq(value)
        if isinstance(node.comparator, ast.NotEq):
            return field.ne(value)
        if isinstance(node.comparator, ast.Lt):
            return field.lt(value)
        if isinstance(node.comparator, ast.LtE):
            return field.lte(value)
        if isinstance(node.comparator, ast.Gt):
            return field.gt(value)
        if isinstance(node.comparator, ast.GtE):
            return field.gte(value)
        if isinstance(node.comparator, ast.In):
            values = value if isinstance(value, list) else [value]
            return field.is_in(values)

        raise exceptions.UnsupportedFunctionException(type(node.comparator).__name__)

    def visit_BoolOp(self, node: ast.BoolOp) -> ConditionBase:
        ":meta private:"
        left = self.visit(node.left)
        right = self.visit(node.right)

        if isinstance(node.op, ast.And):
            return left & right
        if isinstance(node.op, ast.Or):
            return left | right

        raise exceptions.UnsupportedFunctionException(type(node.op).__name__)

    def visit_UnaryOp(self, node: ast.UnaryOp) -> ConditionBase:
        ":meta private:"
        operand = self.visit(node.operand)
        if isinstance(node.op, ast.Not):
            return ~operand
        raise exceptions.UnsupportedFunctionException(type(node.op).__name__)

    def visit_Call(self, node: ast.Call) -> ConditionBase:
        ":meta private:"
        func_name = node.func.name.lower()

        if func_name == "contains":
            field_name = self._field_name(node.args[0])
            return Attr(field_name).contains(self.visit(node.args[1]))
        if func_name == "startswith":
            field_name = self._field_name(node.args[0])
            return Attr(field_name).begins_with(self.visit(node.args[1]))

        raise exceptions.UnsupportedFunctionException(node.func.name)

    def _field_name(self, node: ast._Node) -> str:
        if isinstance(node, (ast.Identifier, ast.Attribute)):
            return self.visit(node)
        raise exceptions.ArgumentTypeException(
            "field", "Identifier", type(node).__name__
        )


def apply_odata_query(filter_str: str) -> ConditionBase:
    """Parse an OData ``$filter`` string and return a boto3 ``ConditionBase``.

    This is a convenience wrapper around :class:`AstToDynamoConditionVisitor`.

    Args:
        filter_str: OData filter expression, e.g. ``"status eq 'active' and age gt 18"``

    Returns:
        A boto3 ``ConditionBase`` that can be passed directly as
        ``FilterExpression`` to a DynamoDB table query or scan.

    Raises:
        InvalidQueryException: If the filter string cannot be parsed.
        UnsupportedFunctionException: If an unsupported OData function is used.

    Example::

        condition = apply_odata_query("status eq 'active' and age gt 18")
        response = table.query(
            KeyConditionExpression=Key('pk').eq('TENANT#acme'),
            FilterExpression=condition,
        )
    """
    ast_tree = parse_odata(filter_str)
    return AstToDynamoConditionVisitor().visit(ast_tree)
