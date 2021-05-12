from odata_query import ast
from odata_query.rewrite import AliasRewriter


def test_identifier_rewrite():
    rewriter = AliasRewriter({"a": "author"})
    _ast = ast.Compare(ast.Eq(), ast.Identifier("a"), ast.String("Bobby"))
    exp = ast.Compare(ast.Eq(), ast.Identifier("author"), ast.String("Bobby"))

    res = rewriter.visit(_ast)
    assert res == exp


def test_identifier_to_attribute_rewrite():
    rewriter = AliasRewriter({"a": "author/name"})
    _ast = ast.Compare(ast.Eq(), ast.Identifier("a"), ast.String("Bobby"))
    exp = ast.Compare(
        ast.Eq(), ast.Attribute(ast.Identifier("author"), "name"), ast.String("Bobby")
    )

    res = rewriter.visit(_ast)
    assert res == exp


def test_attribute_to_identifier_rewrite():
    rewriter = AliasRewriter({"author/name": "author_name"})
    _ast = ast.Compare(
        ast.Eq(), ast.Attribute(ast.Identifier("author"), "name"), ast.String("Bobby")
    )
    exp = ast.Compare(ast.Eq(), ast.Identifier("author_name"), ast.String("Bobby"))

    res = rewriter.visit(_ast)
    assert res == exp


def test_attribute_to_attribute_rewrite():
    rewriter = AliasRewriter({"author/name": "author/info/name"})
    _ast = ast.Compare(
        ast.Eq(), ast.Attribute(ast.Identifier("author"), "name"), ast.String("Bobby")
    )
    exp = ast.Compare(
        ast.Eq(),
        ast.Attribute(ast.Attribute(ast.Identifier("author"), "info"), "name"),
        ast.String("Bobby"),
    )

    res = rewriter.visit(_ast)
    assert res == exp


def test_identifier_to_function_rewrite():
    rewriter = AliasRewriter({"author_length": "length(author)"})
    _ast = ast.Compare(ast.Eq(), ast.Identifier("author_length"), ast.Integer(10))
    exp = ast.Compare(
        ast.Eq(),
        ast.Call(ast.Identifier("length"), [ast.Identifier("author")]),
        ast.Integer(10),
    )

    res = rewriter.visit(_ast)
    assert res == exp
