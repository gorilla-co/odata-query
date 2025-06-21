from datetime import date, datetime
from typing import List

import pytest

from odata_query import ast, sql


class CustomParametrizationHandler(sql.base.ParametrizationHandler):
    template = "%s"


class PositionalParametrizationHandler(sql.base.PositionalParametrizationHandler):
    template = "${}"


@pytest.mark.parametrize(
    "node, expected",
    [
        (ast.String("value"), "'value'"),
        (ast.String("o'reilly"), "'o''reilly'"),
        (ast.Integer("1"), "1"),
        (ast.Float("1.0"), "1.0"),
        (ast.Date("2025-01-02"), "DATE '2025-01-02'"),
        (ast.DateTime("2025-01-02T03:04:05"), "TIMESTAMP '2025-01-02 03:04:05'"),
        (
            ast.GUID("91a26b13-39cb-4607-aa43-1ed0efb12abe"),
            "'91a26b13-39cb-4607-aa43-1ed0efb12abe'",
        ),
    ],
)
def test_no_parametrization_sql_injection_protection(node, expected):
    handler = sql.base.RawSqlHandler()
    ph = handler.add_parameter(node)
    assert ph == expected


def test_parametrization_handler():
    handler = sql.base.ParametrizationHandler()
    ph = handler.add_parameter(ast.String("value"))
    assert handler.params == ["value"]
    assert ph == "?"


def test_parametrization_handler_duplicate_param():
    handler = sql.base.ParametrizationHandler()
    ph1 = handler.add_parameter(ast.String("value"))
    ph2 = handler.add_parameter(ast.String("value"))
    assert handler.params == ["value", "value"]
    assert ph1 == "?"
    assert ph2 == "?"


def test_custom_parametrization_handler():
    handler = CustomParametrizationHandler()
    ph = handler.add_parameter(ast.String("value"))
    assert handler.params == ["value"]
    assert ph == "%s"


def test_positional_parametrization_handler():
    handler = PositionalParametrizationHandler()
    ph = handler.add_parameter(ast.String("value"))
    assert handler.params == ["value"]
    assert ph == "$1"


def test_positional_parametrization_handler_duplicate_param():
    handler = PositionalParametrizationHandler()
    ph1 = handler.add_parameter(ast.String("value"))
    ph2 = handler.add_parameter(ast.String("value"))

    assert handler.params == ["value"]
    assert ph1 == "$1"
    assert ph2 == "$1"


@pytest.mark.parametrize(
    "ast_input, sql_expected",
    [
        (ast.Compare(ast.Eq(), ast.Integer("1"), ast.Integer("2")), "1 = 2"),
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


def test_ast_to_sql_mapping():
    ast_input = ast.BoolOp(
        ast.And(),
        ast.Compare(ast.Eq(), ast.Identifier("a"), ast.String("1")),
        ast.BoolOp(
            ast.Or(),
            ast.Compare(ast.LtE(), ast.Identifier("total_users"), ast.Integer("10")),
            ast.Compare(ast.GtE(), ast.Identifier("total_meters"), ast.Integer("1")),
        ),
    )
    sql_expected = '"table"."a_column" = \'1\' AND (sum("user_id") <= 10 OR sum("meter_id") >= 1)'

    visitor = sql.AstToSqlVisitor(column_mapping={"total_users": 'sum("user_id")', "total_meters": 'sum("meter_id")', "a": '"table"."a_column"'})
    res = visitor.visit(ast_input)

    assert res == sql_expected


@pytest.mark.parametrize(
    "ast_input, sql_expected, params",
    [
        (ast.Compare(ast.Eq(), ast.Integer("1"), ast.Integer("2")), "$1 = $2", [1, 2]),
        (
            ast.Compare(ast.NotEq(), ast.Boolean("true"), ast.Boolean("false")),
            "$1 != $2",
            [True, False],
        ),
        (
            ast.Compare(ast.LtE(), ast.Identifier("eac"), ast.Float("123.12")),
            '"eac" <= $1',
            [123.12],
        ),
        (
            ast.Compare(
                ast.Lt(), ast.Identifier("period_start"), ast.Date("2019-01-01")
            ),
            '"period_start" < $1',
            [date(2019, 1, 1)],
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
            '"eac" >= $1 AND "meter_id" IN ($2, $3, $4)',
            [123.12, "1", "2", "3"],
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
            '"a" = $1 AND ("eac" <= $2 OR "eac" >= $3)',
            ["1", 10.0, 1.0],
        ),
    ],
)
def test_ast_to_sql_positional(
    ast_input: ast._Node, sql_expected: str, params: List[sql.base.ParameterValue]
):
    visitor = sql.AstToSqlVisitor(phandler=PositionalParametrizationHandler())
    res = visitor.visit(ast_input)

    assert res == sql_expected
    assert visitor.params == params


@pytest.mark.parametrize(
    "ast_input, sql_expected, params",
    [
        (ast.Compare(ast.Eq(), ast.Integer("1"), ast.Integer("1")), "? = ?", [1, 1]),
        (
            ast.Compare(ast.NotEq(), ast.Boolean("true"), ast.Boolean("false")),
            "? != ?",
            [True, False],
        ),
        (
            ast.Compare(ast.LtE(), ast.Identifier("eac"), ast.Float("123.12")),
            '"eac" <= ?',
            [123.12],
        ),
        (
            ast.Compare(
                ast.Lt(), ast.Identifier("period_start"), ast.Date("2019-01-01")
            ),
            '"period_start" < ?',
            [date(2019, 1, 1)],
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
            '"eac" >= ? AND "meter_id" IN (?, ?, ?)',
            [123.12, "1", "2", "3"],
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
            '"a" = ? AND ("eac" <= ? OR "eac" >= ?)',
            ["1", 10.0, 1.0],
        ),
    ],
)
def test_ast_to_sql_parametrized(
    ast_input: ast._Node, sql_expected: str, params: List[sql.base.ParameterValue]
):
    visitor = sql.AstToSqlVisitor(phandler=sql.base.ParametrizationHandler())
    res = visitor.visit(ast_input)

    assert res == sql_expected
    assert visitor.params == params


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
    WHEN > 0 CAST (123.12 AS INTEGER) + 1
    WHEN < 0 CAST (123.12 AS INTEGER) - 1
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


@pytest.mark.parametrize(
    "func_name, args, sql_expected, params",
    [
        ("concat", [ast.String("ab"), ast.String("cd")], "? || ?", ["ab", "cd"]),
        (
            "contains",
            [ast.String("abc"), ast.String("b")],
            "? LIKE ?",
            ["abc", "%b%"],
        ),
        (
            "endswith",
            [ast.String("abc"), ast.String("bc")],
            "? LIKE ?",
            ["abc", "%bc"],
        ),
        (
            "indexof",
            [ast.String("abc"), ast.String("bc")],
            "POSITION(? IN ?) - 1",
            ["bc", "abc"],
        ),
        ("length", [ast.String("abc")], "CHAR_LENGTH(?)", ["abc"]),
        (
            "length",
            [ast.List([ast.String("a"), ast.String("b")])],
            "CARDINALITY((?, ?))",
            ["a", "b"],
        ),
        (
            "startswith",
            [ast.String("abc"), ast.String("ab")],
            "? LIKE ?",
            ["abc", "ab%"],
        ),
        (
            "substring",
            [ast.String("abc"), ast.Integer("1")],
            "SUBSTRING(? FROM ? + 1)",
            ["abc", 1],
        ),
        (
            "substring",
            [ast.String("abcdef"), ast.Integer("1"), ast.Integer("2")],
            "SUBSTRING(? FROM ? + 1 FOR ?)",
            ["abcdef", 1, 2],
        ),
        ("tolower", [ast.String("ABC")], "LOWER(?)", ["ABC"]),
        ("toupper", [ast.String("abc")], "UPPER(?)", ["abc"]),
        ("trim", [ast.String(" abc ")], "TRIM(?)", [" abc "]),
        (
            "year",
            [ast.DateTime("2018-01-01T10:00:00")],
            "EXTRACT (YEAR FROM ?)",
            [datetime(2018, 1, 1, 10, 0, 0)],
        ),
        (
            "month",
            [ast.DateTime("2018-01-01T10:00:00")],
            "EXTRACT (MONTH FROM ?)",
            [datetime(2018, 1, 1, 10, 0, 0)],
        ),
        (
            "day",
            [ast.DateTime("2018-01-01T10:00:00")],
            "EXTRACT (DAY FROM ?)",
            [datetime(2018, 1, 1, 10, 0, 0)],
        ),
        (
            "hour",
            [ast.DateTime("2018-01-01T10:00:00")],
            "EXTRACT (HOUR FROM ?)",
            [datetime(2018, 1, 1, 10, 0, 0)],
        ),
        (
            "minute",
            [ast.DateTime("2018-01-01T10:00:00")],
            "EXTRACT (MINUTE FROM ?)",
            [datetime(2018, 1, 1, 10, 0, 0)],
        ),
        (
            "date",
            [ast.DateTime("2018-01-01T10:00:00")],
            "CAST (? AS DATE)",
            [datetime(2018, 1, 1, 10, 0, 0)],
        ),
        ("now", [], "CURRENT_TIMESTAMP", []),
        ("round", [ast.Float("123.12")], "CAST (? + 0.5 AS INTEGER)", [123.12]),
        (
            "floor",
            [ast.Float("123.12")],
            """CASE ?
    WHEN > 0 CAST (? AS INTEGER)
    WHEN < 0 CAST (0 - (ABS(?) + 0.5) AS INTEGER))
    ELSE ?
END""",
            [123.12, 123.12, 123.12, 123.12],
        ),
        (
            "ceiling",
            [ast.Float("123.12")],
            """CASE ? - CAST (? AS INTEGER)
    WHEN > 0 CAST (? AS INTEGER) + 1
    WHEN < 0 CAST (? AS INTEGER) - 1
    ELSE ?
END""",
            [123.12, 123.12, 123.12, 123.12, 123.12],
        ),
    ],
)
def test_ast_to_sql_functions_parametrized(
    func_name: str,
    args: List[ast._Node],
    sql_expected: str,
    params: List[sql.base.ParameterValue],
):
    inp_ast = ast.Call(ast.Identifier(func_name), args)
    visitor = sql.AstToSqlVisitor(phandler=sql.base.ParametrizationHandler())
    res = visitor.visit(inp_ast)

    assert res == sql_expected
    assert visitor.params == params


@pytest.mark.parametrize(
    "func_name, args, sql_expected, params",
    [
        ("concat", [ast.String("ab"), ast.String("cd")], "$1 || $2", ["ab", "cd"]),
        (
            "contains",
            [ast.String("abc"), ast.String("b")],
            "$1 LIKE $2",
            ["abc", "%b%"],
        ),
        (
            "endswith",
            [ast.String("abc"), ast.String("bc")],
            "$1 LIKE $2",
            ["abc", "%bc"],
        ),
        (
            "indexof",
            [ast.String("abc"), ast.String("bc")],
            "POSITION($1 IN $2) - 1",
            ["bc", "abc"],
        ),
        ("length", [ast.String("abc")], "CHAR_LENGTH($1)", ["abc"]),
        (
            "length",
            [ast.List([ast.String("a"), ast.String("b")])],
            "CARDINALITY(($1, $2))",
            ["a", "b"],
        ),
        (
            "startswith",
            [ast.String("abc"), ast.String("ab")],
            "$1 LIKE $2",
            ["abc", "ab%"],
        ),
        (
            "substring",
            [ast.String("abc"), ast.Integer("1")],
            "SUBSTRING($1 FROM $2 + 1)",
            ["abc", 1],
        ),
        (
            "substring",
            [ast.String("abcdef"), ast.Integer("1"), ast.Integer("2")],
            "SUBSTRING($1 FROM $2 + 1 FOR $3)",
            ["abcdef", 1, 2],
        ),
        ("tolower", [ast.String("ABC")], "LOWER($1)", ["ABC"]),
        ("toupper", [ast.String("abc")], "UPPER($1)", ["abc"]),
        ("trim", [ast.String(" abc ")], "TRIM($1)", [" abc "]),
        (
            "year",
            [ast.DateTime("2018-01-01T10:00:00")],
            "EXTRACT (YEAR FROM $1)",
            [datetime(2018, 1, 1, 10, 0, 0)],
        ),
        (
            "month",
            [ast.DateTime("2018-01-01T10:00:00")],
            "EXTRACT (MONTH FROM $1)",
            [datetime(2018, 1, 1, 10, 0, 0)],
        ),
        (
            "day",
            [ast.DateTime("2018-01-01T10:00:00")],
            "EXTRACT (DAY FROM $1)",
            [datetime(2018, 1, 1, 10, 0, 0)],
        ),
        (
            "hour",
            [ast.DateTime("2018-01-01T10:00:00")],
            "EXTRACT (HOUR FROM $1)",
            [datetime(2018, 1, 1, 10, 0, 0)],
        ),
        (
            "minute",
            [ast.DateTime("2018-01-01T10:00:00")],
            "EXTRACT (MINUTE FROM $1)",
            [datetime(2018, 1, 1, 10, 0, 0)],
        ),
        (
            "date",
            [ast.DateTime("2018-01-01T10:00:00")],
            "CAST ($1 AS DATE)",
            [datetime(2018, 1, 1, 10, 0, 0)],
        ),
        ("now", [], "CURRENT_TIMESTAMP", []),
        ("round", [ast.Float("123.12")], "CAST ($1 + 0.5 AS INTEGER)", [123.12]),
        (
            "floor",
            [ast.Float("123.12")],
            """CASE $1
    WHEN > 0 CAST ($1 AS INTEGER)
    WHEN < 0 CAST (0 - (ABS($1) + 0.5) AS INTEGER))
    ELSE $1
END""",
            [123.12],
        ),
        (
            "ceiling",
            [ast.Float("123.12")],
            """CASE $1 - CAST ($1 AS INTEGER)
    WHEN > 0 CAST ($1 AS INTEGER) + 1
    WHEN < 0 CAST ($1 AS INTEGER) - 1
    ELSE $1
END""",
            [123.12],
        ),
    ],
)
def test_ast_to_sql_functions_positional(
    func_name: str,
    args: List[ast._Node],
    sql_expected: str,
    params: List[sql.base.ParameterValue],
):
    inp_ast = ast.Call(ast.Identifier(func_name), args)
    visitor = sql.AstToSqlVisitor(phandler=PositionalParametrizationHandler())
    res = visitor.visit(inp_ast)

    assert res == sql_expected
    assert visitor.params == params
