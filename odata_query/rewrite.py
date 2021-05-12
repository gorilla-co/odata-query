from typing import Dict

from . import ast
from .grammar import ODataLexer, ODataParser  # type: ignore
from .visitor import NodeTransformer


class AliasRewriter(NodeTransformer):
    def __init__(
        self, field_aliases: Dict[ast._Node, ast._Node], lexer=None, parser=None
    ):
        self.field_aliases = field_aliases

        if not lexer:
            lexer = ODataLexer()
        if not parser:
            parser = ODataParser()

        self.replacements = {
            parser.parse(lexer.tokenize(k)): parser.parse(lexer.tokenize(v))
            for k, v in self.field_aliases.items()
        }

    def visit_Identifier(self, node: ast.Identifier) -> ast._Node:
        if node in self.replacements:
            return self.replacements[node]
        return node

    def visit_Attribute(self, node: ast.Attribute) -> ast._Node:
        if node in self.replacements:
            return self.replacements[node]
        return node


class IdentifierStripper(NodeTransformer):
    def __init__(self, strip: ast.Identifier):
        self.strip = strip

    def visit_Attribute(self, node: ast.Attribute) -> ast._Node:
        if node.owner == self.strip:
            return ast.Identifier(node.attr)
        elif isinstance(node.owner, ast.Attribute):
            return ast.Attribute(self.visit(node.owner), node.attr)

        return node
