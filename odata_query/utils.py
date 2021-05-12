from . import ast
from .rewrite import IdentifierStripper


def expression_relative_to_identifier(
    identifier: ast.Identifier, expression: ast._Node
) -> ast._Node:
    stripper = IdentifierStripper(identifier)
    result = stripper.visit(expression)
    return result
