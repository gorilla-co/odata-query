from . import ast
from .visitor import NodeVisitor, iter_dataclass_fields


def expression_relative_to_identifier(
    identifier: ast.Identifier, expression: ast._Node
) -> ast._Node:
    stripper = IdentifierStripper(identifier)
    result = stripper.visit(expression)
    return result


class IdentifierStripper(NodeVisitor):
    def __init__(self, strip: ast.Identifier):
        self.strip = strip

    def generic_visit(self, node):
        """
        Same as the normal generic_visit, but replaces nodes with the returned values.
        """
        for field, value in iter_dataclass_fields(node):
            if isinstance(value, list):
                res = []
                for item in value:
                    if isinstance(item, ast._Node):
                        res.append(self.visit(item))
                    else:
                        res.append(item)
            elif isinstance(value, ast._Node):
                res = self.visit(value)
            else:
                res = value

            setattr(node, field, res)

        return node

    def visit_Attribute(self, node: ast.Attribute) -> ast._Node:
        if node.owner == self.strip:
            return ast.Identifier(node.attr)
        elif isinstance(node.owner, ast.Attribute):
            node.owner = self.visit(node.owner)

        return node
