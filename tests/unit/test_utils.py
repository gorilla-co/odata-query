import pytest

from odata_query import ast, exceptions, utils


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
        (
            ast.Compare(
                ast.In(),
                ast.Attribute(ast.Identifier("id"), "name"),
                ast.List([ast.String("Jozef")]),
            ),
            ast.Compare(
                ast.In(), ast.Identifier("name"), ast.List([ast.String("Jozef")])
            ),
        ),
    ],
)
def test_expression_relative_to_identifier(expression, expected):
    res = utils.expression_relative_to_identifier(ast.Identifier("id"), expression)

    assert res == expected


@pytest.mark.parametrize(
    "top, skip",
    [(None, None), (0, None), (None, 0), (5, 0), (0, 5), (10**12, 10**12)],
)
def test_validate_top_and_skip_accepts_non_negative_integers(top, skip):
    utils.validate_top_and_skip(top, skip)


@pytest.mark.parametrize(
    "top, skip, invalid_option",
    [
        (-1, None, "top"),
        (None, -1, "skip"),
        (5, -1, "skip"),
        (-1, 5, "top"),
        ("5", None, "top"),
        (None, "5", "skip"),
        (1.5, None, "top"),
        (True, None, "top"),
        (None, False, "skip"),
        ([1], None, "top"),
    ],
)
def test_validate_top_and_skip_rejects_anything_else(top, skip, invalid_option):
    with pytest.raises(exceptions.InvalidQueryOptionException) as exc_info:
        utils.validate_top_and_skip(top, skip)

    assert exc_info.value.option_name == invalid_option
