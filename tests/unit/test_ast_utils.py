import pytest

from odata_query import ast, utils


@pytest.mark.parametrize(
    "expression, expected",
    [
        (ast.Attribute(ast.Identifier("id"), "name"), ast.Identifier("name")),
        (
            ast.Attribute(ast.Attribute(ast.Identifier("id"), "user"), "name"),
            ast.Attribute(ast.Identifier("user"), "name"),
        ),
        (
            ast.Attribute(ast.Identifier("something else"), "whatever"),
            ast.Attribute(ast.Identifier("something else"), "whatever"),
        ),
        (
            ast.Compare(
                ast.Eq(),
                ast.Attribute(ast.Identifier("id"), "name"),
                ast.String("Jozef"),
            ),
            ast.Compare(ast.Eq(), ast.Identifier("name"), ast.String("Jozef")),
        ),
    ],
)
def test_expression_relative_to_identifier(expression, expected):
    res = utils.expression_relative_to_identifier(ast.Identifier("id"), expression)

    assert res == expected
