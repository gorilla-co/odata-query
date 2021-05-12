from copy import deepcopy
from unittest import mock

import pytest

from odata_query import ast, visitor


@pytest.fixture()
def simple_ast():
    return ast.Compare(
        ast.Eq(),
        ast.BoolOp(
            ast.And(),
            ast.Compare(ast.Eq(), ast.Identifier("meter_id"), ast.String("123")),
            ast.Compare(
                ast.In(), ast.Identifier("category"), ast.List([ast.String("Gas")])
            ),
        ),
        ast.Boolean("true"),
    )


def test_generic_visitor_calls_methods_based_on_node_class(simple_ast):
    _visitor = visitor.NodeVisitor()
    _visitor.visit_Identifier = mock.MagicMock()
    _visitor.visit(simple_ast)
    assert _visitor.visit_Identifier.call_count == 2


def test_node_transformer_without_methods_doesnt_modify_tree(simple_ast):
    transformer = visitor.NodeTransformer()
    new_tree = transformer.visit(deepcopy(simple_ast))
    assert simple_ast == new_tree


def test_node_transformer_simple(simple_ast):
    class Inverter(visitor.NodeTransformer):
        """Simple transformer that inverts equality checks"""

        def visit_Compare(self, node: ast.Compare) -> ast.Compare:
            left = self.visit(node.left)
            right = self.visit(node.right)
            if isinstance(node.comparator, ast.Eq):
                return ast.Compare(ast.NotEq(), left, right)
            elif isinstance(node.comparator, ast.NotEq):
                return ast.Compare(ast.Eq(), left, right)
            return ast.Compare(node.comparator, left, right)

    transformer = Inverter()
    new_tree = transformer.visit(deepcopy(simple_ast))

    assert simple_ast != new_tree
    assert isinstance(new_tree.comparator, ast.NotEq)
    assert isinstance(new_tree.left.left.comparator, ast.NotEq)

    roundtrip_tree = transformer.visit(deepcopy(new_tree))
    assert simple_ast == roundtrip_tree
