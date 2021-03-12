from typing import List

import pytest

from odata_query import ast, sql


@pytest.mark.parametrize(
    "ast_input, sql_expected",
    [
        (ast.Compare(ast.Eq(), ast.Integer("1"), ast.Integer("1")), "1 = 1"),
        (
            ast.Compare(ast.NotEq(), ast.Boolean("true"), ast.Boolean("false")),
            "TRUE != FALSE",
        ),
        (
            ast.Compare(ast.LtE(), ast.Identifier("eac"), ast.Float("123.12")),
            '"eac" <= 123.12',
        ),
        (
            ast.Compare(
                ast.Lt(), ast.Identifier("period_start"), ast.Date("2019-01-01")
            ),
            "\"period_start\" < DATE '2019-01-01'",
        ),
        (
            ast.BoolOp(
                ast.And(),
                ast.Compare(ast.GtE(), ast.Identifier("eac"), ast.Float("123.12")),
                ast.Compare(
                    ast.In(),
                    ast.Identifier("meter_id"),
                    ast.List([ast.String("1"), ast.String("2"), ast.String("3")]),
                ),
            ),
            "\"eac\" >= 123.12 AND \"meter_id\" IN ('1', '2', '3')",
        ),
        (
            ast.BoolOp(
                ast.And(),
                ast.Compare(ast.Eq(), ast.Identifier("a"), ast.String("1")),
                ast.BoolOp(
                    ast.Or(),
                    ast.Compare(ast.LtE(), ast.Identifier("eac"), ast.Float("10.0")),
                    ast.Compare(ast.GtE(), ast.Identifier("eac"), ast.Float("1.0")),
                ),
            ),
            '"a" = \'1\' AND ("eac" <= 10.0 OR "eac" >= 1.0)',
        ),
    ],
)
def test_ast_to_sql(ast_input: ast._Node, sql_expected: str):
    visitor = sql.AstToAthenaSqlVisitor()
    res = visitor.visit(ast_input)

    assert res == sql_expected


@pytest.mark.parametrize(
    "func_name, args, sql_expected",
    [
        ("concat", [ast.String("ab"), ast.String("cd")], "concat('ab', 'cd')"),
        (
            "concat",
            [
                ast.List([ast.String("a"), ast.String("b")]),
                ast.List([ast.String("c")]),
            ],
            "concat(('a', 'b'), ('c'))",
        ),
        (
            "contains",
            [ast.String("abc"), ast.String("b")],
            "strpos('abc', 'b') > 0",
        ),
        (
            "endswith",
            [ast.String("abc"), ast.String("bc")],
            "strpos('abc', 'bc') = length('abc') - length('bc') + 1",
        ),
        (
            "indexof",
            [ast.String("abc"), ast.String("bc")],
            "strpos('abc', 'bc') - 1",
        ),
        ("length", [ast.String("abc")], "length('abc')"),
        (
            "length",
            [ast.List([ast.String("a"), ast.String("b")])],
            "cardinality(('a', 'b'))",
        ),
        (
            "startswith",
            [ast.String("abc"), ast.String("ab")],
            "strpos('abc', 'ab') = 1",
        ),
        (
            "substring",
            [ast.String("abc"), ast.Integer("1")],
            "substr('abc', 1 + 1)",
        ),
        (
            "substring",
            [ast.String("abcdef"), ast.Integer("1"), ast.Integer("2")],
            "substr('abcdef', 1 + 1, 2)",
        ),
        (
            "substring",
            [ast.List([ast.String("a"), ast.String("b")]), ast.Integer("1")],
            "slice(('a', 'b'), 1)",
        ),
        (
            "substring",
            [
                ast.List([ast.String("a"), ast.String("b")]),
                ast.Integer("1"),
                ast.Integer("2"),
            ],
            "slice(('a', 'b'), 1, 2)",
        ),
        ("tolower", [ast.String("ABC")], "lower('ABC')"),
        ("toupper", [ast.String("abc")], "upper('abc')"),
        ("trim", [ast.String(" abc ")], "trim(' abc ')"),
        (
            "year",
            [ast.DateTime("2018-01-01T10:00:00")],
            "year(from_iso8601_timestamp('2018-01-01T10:00:00'))",
        ),
        (
            "month",
            [ast.DateTime("2018-01-01T10:00:00")],
            "month(from_iso8601_timestamp('2018-01-01T10:00:00'))",
        ),
        (
            "day",
            [ast.DateTime("2018-01-01T10:00:00")],
            "day(from_iso8601_timestamp('2018-01-01T10:00:00'))",
        ),
        (
            "hour",
            [ast.DateTime("2018-01-01T10:00:00")],
            "hour(from_iso8601_timestamp('2018-01-01T10:00:00'))",
        ),
        (
            "minute",
            [ast.DateTime("2018-01-01T10:00:00")],
            "minute(from_iso8601_timestamp('2018-01-01T10:00:00'))",
        ),
        (
            "date",
            [ast.DateTime("2018-01-01T10:00:00")],
            "date_trunc(day, from_iso8601_timestamp('2018-01-01T10:00:00'))",
        ),
        ("now", [], "CURRENT_TIMESTAMP"),
        ("round", [ast.Float("123.12")], "round(123.12)"),
        ("floor", [ast.Float("123.12")], "floor(123.12)"),
        ("ceiling", [ast.Float("123.12")], "ceiling(123.12)"),
        (
            "hassubset",
            [
                ast.List([ast.String("a"), ast.String("b")]),
                ast.List([ast.String("a")]),
            ],
            "cardinality(array_intersect(('a', 'b'), ('a'))) = cardinality(('a'))",
        ),
    ],
)
def test_ast_to_sql_functions(func_name: str, args: List[ast._Node], sql_expected: str):
    inp_ast = ast.Call(ast.Identifier(func_name), args)
    visitor = sql.AstToAthenaSqlVisitor()
    res = visitor.visit(inp_ast)

    assert res == sql_expected
