from typing import Type

import pytest

from odata_query import ast, typing


@pytest.mark.parametrize(
    "input_node, expected_type",
    [
        (ast.String("abc"), ast.String),
        (ast.Compare(ast.Eq(), ast.String("abc"), ast.String("def")), ast.Boolean),
        (
            ast.Call(ast.Identifier("contains"), [ast.String("abc"), ast.String("b")]),
            ast.Boolean,
        ),
        (ast.Identifier("a"), None),
    ],
)
def test_infer_type_of_node(input_node: ast._Node, expected_type: Type[ast._Node]):
    res = typing.infer_type(input_node)

    assert res is expected_type


@pytest.mark.parametrize(
    "input_node, expected_type",
    [
        (
            ast.Call(ast.Identifier("contains"), [ast.String("abc"), ast.String("b")]),
            ast.Boolean,
        ),
        (
            ast.Call(ast.Identifier("indexof"), [ast.String("abc"), ast.String("b")]),
            ast.Integer,
        ),
        (
            ast.Call(ast.Identifier("floor"), [ast.Float("10.32")]),
            ast.Float,
        ),
        (
            ast.Call(ast.Identifier("date"), [ast.DateTime("2020-01-01T10:10:10")]),
            ast.Date,
        ),
        (
            ast.Call(ast.Identifier("maxdatetime"), []),
            ast.DateTime,
        ),
        (
            ast.Call(ast.Identifier("unknown_function"), []),
            None,
        ),
    ],
)
def test_infer_return_type_of_call(
    input_node: ast.Call, expected_type: Type[ast._Node]
):
    res = typing.infer_type(input_node)

    assert res is expected_type
