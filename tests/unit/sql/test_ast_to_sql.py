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
    visitor = sql.AstToSqlVisitor()
    res = visitor.visit(ast_input)

    assert res == sql_expected


@pytest.mark.parametrize(
    "func_name, args, sql_expected",
    [
        ("concat", [ast.String("ab"), ast.String("cd")], "'ab' || 'cd'"),
        (
            "contains",
            [ast.String("abc"), ast.String("b")],
            "'abc' LIKE '%b%'",
        ),
        (
            "endswith",
            [ast.String("abc"), ast.String("bc")],
            "'abc' LIKE '%bc'",
        ),
        (
            "indexof",
            [ast.String("abc"), ast.String("bc")],
            "POSITION('bc' IN 'abc') - 1",
        ),
        ("length", [ast.String("abc")], "CHAR_LENGTH('abc')"),
        (
            "length",
            [ast.List([ast.String("a"), ast.String("b")])],
            "CARDINALITY(('a', 'b'))",
        ),
        (
            "startswith",
            [ast.String("abc"), ast.String("ab")],
            "'abc' LIKE 'ab%'",
        ),
        (
            "substring",
            [ast.String("abc"), ast.Integer("1")],
            "SUBSTRING('abc' FROM 1 + 1)",
        ),
        (
            "substring",
            [ast.String("abcdef"), ast.Integer("1"), ast.Integer("2")],
            "SUBSTRING('abcdef' FROM 1 + 1 FOR 2)",
        ),
        ("tolower", [ast.String("ABC")], "LOWER('ABC')"),
        ("toupper", [ast.String("abc")], "UPPER('abc')"),
        ("trim", [ast.String(" abc ")], "TRIM(' abc ')"),
        (
            "year",
            [ast.DateTime("2018-01-01T10:00:00")],
            "EXTRACT (YEAR FROM TIMESTAMP '2018-01-01 10:00:00')",
        ),
        (
            "month",
            [ast.DateTime("2018-01-01T10:00:00")],
            "EXTRACT (MONTH FROM TIMESTAMP '2018-01-01 10:00:00')",
        ),
        (
            "day",
            [ast.DateTime("2018-01-01T10:00:00")],
            "EXTRACT (DAY FROM TIMESTAMP '2018-01-01 10:00:00')",
        ),
        (
            "hour",
            [ast.DateTime("2018-01-01T10:00:00")],
            "EXTRACT (HOUR FROM TIMESTAMP '2018-01-01 10:00:00')",
        ),
        (
            "minute",
            [ast.DateTime("2018-01-01T10:00:00")],
            "EXTRACT (MINUTE FROM TIMESTAMP '2018-01-01 10:00:00')",
        ),
        (
            "date",
            [ast.DateTime("2018-01-01T10:00:00")],
            "CAST (TIMESTAMP '2018-01-01 10:00:00' AS DATE)",
        ),
        ("now", [], "CURRENT_TIMESTAMP"),
        ("round", [ast.Float("123.12")], "CAST (123.12 + 0.5 AS INTEGER)"),
        (
            "floor",
            [ast.Float("123.12")],
            """CASE 123.12
    WHEN > 0 CAST (123.12 AS INTEGER)
    WHEN < 0 CAST (0 - (ABS(123.12) + 0.5) AS INTEGER))
    ELSE 123.12
END""",
        ),
        (
            "ceiling",
            [ast.Float("123.12")],
            """CASE 123.12 - CAST (123.12 AS INTEGER)
    WHEN > 0 123.12+1
    WHEN < 0 123.12-1
    ELSE 123.12
END""",
        ),
    ],
)
def test_ast_to_sql_functions(func_name: str, args: List[ast._Node], sql_expected: str):
    inp_ast = ast.Call(ast.Identifier(func_name), args)
    visitor = sql.AstToSqlVisitor()
    res = visitor.visit(inp_ast)

    assert res == sql_expected
