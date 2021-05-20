from typing import Dict

from . import ast
from .grammar import ODataLexer, ODataParser  # type: ignore
from .visitor import NodeTransformer


class AliasRewriter(NodeTransformer):
    """
    A :class:`NodeTransformer` that replaces aliases in the :term:`AST` with their
    aliased identifiers or attributes.

    Args:
        field_aliases: A mapping of aliases to their full name. These can
            be identifiers, attributes, and even function calls in odata
            syntax.
        lexer: Optional lexer instance to use. If not passed, will construct
            the default one.
        parser: Optional parser instance to use. If not passed, will construct
            the default one.
    """

    def __init__(self, field_aliases: Dict[str, str], lexer=None, parser=None):
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
        """
        :meta private:
        """
        if node in self.replacements:
            return self.replacements[node]
        return node

    def visit_Attribute(self, node: ast.Attribute) -> ast._Node:
        """
        :meta private:
        """
        if node in self.replacements:
            return self.replacements[node]
        else:
            new_owner = self.visit(node.owner)
            return ast.Attribute(new_owner, node.attr)


class IdentifierStripper(NodeTransformer):
    """
    A :class:`NodeTransformer` that strips the given identifier off of
    attributes. E.g. ``author/name`` -> ``name``.

    Args:
        strip: The identifier to strip off of all attributes in the :term:`AST`
    """

    def __init__(self, strip: ast.Identifier):
        self.strip = strip

    def visit_Attribute(self, node: ast.Attribute) -> ast._Node:
        """
        :meta private:
        """
        if node.owner == self.strip:
            return ast.Identifier(node.attr)
        elif isinstance(node.owner, ast.Attribute):
            return ast.Attribute(self.visit(node.owner), node.attr)

        return node
