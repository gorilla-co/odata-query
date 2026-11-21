import pytest

from odata_query import ast, exceptions
from odata_query.grammar import parse_orderby


def _ident(name: str) -> ast.Identifier:
    return ast.Identifier(name)


@pytest.mark.parametrize(
    "orderby, expected_items",
    [
        ("name", [ast.OrderByItem(_ident("name"))]),
        ("name asc", [ast.OrderByItem(_ident("name"), ascending=True)]),
        ("name desc", [ast.OrderByItem(_ident("name"), ascending=False)]),
        # 4.01: direction keywords are case-insensitive
        ("name ASC", [ast.OrderByItem(_ident("name"), ascending=True)]),
        ("name DeSc", [ast.OrderByItem(_ident("name"), ascending=False)]),
        # Whitespace
        ("  name  desc  ", [ast.OrderByItem(_ident("name"), ascending=False)]),
        ("name\tdesc", [ast.OrderByItem(_ident("name"), ascending=False)]),
        (
            "name desc , other",
            [
                ast.OrderByItem(_ident("name"), ascending=False),
                ast.OrderByItem(_ident("other")),
            ],
        ),
        (
            "name ,other ",
            [
                ast.OrderByItem(_ident("name")),
                ast.OrderByItem(_ident("other")),
            ],
        ),
        (
            "name desc,other asc",
            [
                ast.OrderByItem(_ident("name"), ascending=False),
                ast.OrderByItem(_ident("other"), ascending=True),
            ],
        ),
        # Paths
        (
            "author/name desc",
            [ast.OrderByItem(ast.Attribute(_ident("author"), "name"), ascending=False)],
        ),
        # Expressions
        (
            "tolower(name) desc",
            [
                ast.OrderByItem(
                    ast.Call(ast.Identifier("tolower"), [_ident("name")]),
                    ascending=False,
                )
            ],
        ),
        (
            "price add tax desc",
            [
                ast.OrderByItem(
                    ast.BinOp(ast.Add(), _ident("price"), _ident("tax")),
                    ascending=False,
                )
            ],
        ),
        # Commas inside function arguments and lists do not split items:
        (
            "concat(first, last) desc, id",
            [
                ast.OrderByItem(
                    ast.Call(
                        ast.Identifier("concat"), [_ident("first"), _ident("last")]
                    ),
                    ascending=False,
                ),
                ast.OrderByItem(_ident("id")),
            ],
        ),
        # ... nor do commas inside string literals:
        (
            "concat(name, ', ') desc",
            [
                ast.OrderByItem(
                    ast.Call(
                        ast.Identifier("concat"), [_ident("name"), ast.String(", ")]
                    ),
                    ascending=False,
                )
            ],
        ),
        # asc and desc are not reserved words:
        ("asc", [ast.OrderByItem(_ident("asc"))]),
        ("desc", [ast.OrderByItem(_ident("desc"))]),
        ("asc desc", [ast.OrderByItem(_ident("asc"), ascending=False)]),
        ("desc asc", [ast.OrderByItem(_ident("desc"), ascending=True)]),
        (
            "desc asc, asc desc",
            [
                ast.OrderByItem(_ident("desc"), ascending=True),
                ast.OrderByItem(_ident("asc"), ascending=False),
            ],
        ),
        (
            "name eq asc",
            [
                ast.OrderByItem(
                    ast.Compare(ast.Eq(), _ident("name"), _ident("asc")),
                )
            ],
        ),
        (
            "name eq asc desc",
            [
                ast.OrderByItem(
                    ast.Compare(ast.Eq(), _ident("name"), _ident("asc")),
                    ascending=False,
                )
            ],
        ),
    ],
)
def test_parse_orderby(orderby, expected_items):
    assert parse_orderby(orderby) == ast.OrderBy(expected_items)


@pytest.mark.parametrize(
    "orderby",
    [
        "",
        "   ",
        ",",
        "name,",
        ",name",
        "a,,b",
        "a, ,b",
        "name desc desc",
        "name asc desc",
        "name descending",
        "name desc,",
        "desc name",
        "name desc other",
        "tolower(name",
        "tolower(name))",
        "name eq",
        "name nonsense",
    ],
)
def test_parse_orderby_rejects_invalid_syntax(orderby):
    with pytest.raises(exceptions.ParsingException):
        parse_orderby(orderby)


def test_parse_orderby_rejects_untokenizable_input():
    with pytest.raises(exceptions.TokenizingException):
        parse_orderby("name #")


@pytest.mark.parametrize(
    "orderby, expected_exception",
    [
        ("unknown(name) desc", exceptions.UnknownFunctionException),
        ("concat(name) desc", exceptions.ArgumentCountException),
    ],
)
def test_parse_orderby_reports_function_errors_in_items(orderby, expected_exception):
    with pytest.raises(expected_exception):
        parse_orderby(orderby)
