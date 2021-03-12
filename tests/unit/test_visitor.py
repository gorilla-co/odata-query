from unittest import mock

from odata_query import ast, visitor


def test_generic_visitor():
    _ast = ast.Compare(
        ast.Eq(),
        ast.BoolOp(
            ast.And(),
            ast.Compare(ast.Eq(), ast.Identifier("meter_id"), ast.String("123")),
            ast.Compare(ast.Lt(), ast.Identifier("eac"), ast.Float("123.12")),
        ),
        ast.Boolean("true"),
    )

    _visitor = visitor.NodeVisitor()
    _visitor.visit_Identifier = mock.MagicMock()

    _visitor.visit(_ast)

    assert _visitor.visit_Identifier.call_count == 2
