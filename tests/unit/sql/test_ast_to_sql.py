from typing import List

import pytest

from odata_query import ast, exceptions, sql
from odata_query.grammar import parse_orderby


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
            "contains",
            [ast.String("abc"), ast.String("o'b")],
            "'abc' LIKE '%o''b%'",
        ),
        (
            "endswith",
            [ast.String("abc"), ast.String("bc")],
            "'abc' LIKE '%bc'",
        ),
        (
            "endswith",
            [ast.String("abc"), ast.String("o'c")],
            "'abc' LIKE '%o''c'",
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
            "startswith",
            [ast.String("abc"), ast.String("a'b")],
            "'abc' LIKE 'a''b%'",
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


@pytest.mark.parametrize(
    "ast_input",
    [
        ast.Attribute(ast.Identifier("author"), "name"),
        ast.Compare(
            ast.Eq(),
            ast.Attribute(ast.Identifier("author"), "name"),
            ast.String("Gorilla"),
        ),
        ast.CollectionLambda(ast.Identifier("authors"), ast.Any(), None),
    ],
)
def test_relationships_are_not_silently_dropped(ast_input: ast._Node):
    with pytest.raises(NotImplementedError):
        sql.AstToSqlVisitor().visit(ast_input)


ORDERBY_CASES = [
    # (OData $orderby, standard SQL, SQLite, Athena)
    (
        "name",
        '"name" ASC NULLS FIRST',
        '"name" ASC',
        '"name" ASC NULLS FIRST',
    ),
    (
        "name asc",
        '"name" ASC NULLS FIRST',
        '"name" ASC',
        '"name" ASC NULLS FIRST',
    ),
    (
        "name desc",
        '"name" DESC NULLS LAST',
        '"name" DESC',
        '"name" DESC NULLS LAST',
    ),
    (
        "name, age desc, id",
        '"name" ASC NULLS FIRST, "age" DESC NULLS LAST, "id" ASC NULLS FIRST',
        '"name" ASC, "age" DESC, "id" ASC',
        '"name" ASC NULLS FIRST, "age" DESC NULLS LAST, "id" ASC NULLS FIRST',
    ),
    (
        "tolower(name) desc",
        'LOWER("name") DESC NULLS LAST',
        'LOWER("name") DESC',
        'LOWER("name") DESC NULLS LAST',
    ),
    (
        "age add 1 desc, concat(first, 'x, y') asc",
        '"age" + 1 DESC NULLS LAST, "first" || \'x, y\' ASC NULLS FIRST',
        '"age" + 1 DESC, "first" || \'x, y\' ASC',
        '"age" + 1 DESC NULLS LAST, "first" || \'x, y\' ASC NULLS FIRST',
    ),
    (
        "age gt 5 desc",
        '"age" > 5 DESC NULLS LAST',
        '"age" > 5 DESC',
        '"age" > 5 DESC NULLS LAST',
    ),
]


@pytest.mark.parametrize(
    "visitor_cls, expected_column",
    [
        (sql.AstToSqlVisitor, 1),
        (sql.AstToSqliteSqlVisitor, 2),
        (sql.AstToAthenaSqlVisitor, 3),
    ],
)
@pytest.mark.parametrize("case", ORDERBY_CASES, ids=[c[0] for c in ORDERBY_CASES])
def test_orderby_to_sql(visitor_cls, expected_column, case):
    ast_input = parse_orderby(case[0])
    visitor = visitor_cls()

    assert visitor.visit(ast_input) == case[expected_column]


def test_orderby_to_sql_uses_the_table_alias():
    visitor = sql.AstToSqlVisitor(table_alias="t")

    res = visitor.visit(parse_orderby("name, id desc"))

    assert res == '"t"."name" ASC NULLS FIRST, "t"."id" DESC NULLS LAST'


def test_orderby_on_relationships_is_not_supported():
    with pytest.raises(NotImplementedError):
        sql.AstToSqlVisitor().visit(parse_orderby("author/name"))


PAGING_CASES = [
    # (top, skip, standard SQL, SQLite, Athena)
    (None, None, "", "", ""),
    (5, None, "OFFSET 0 ROWS FETCH NEXT 5 ROWS ONLY", "LIMIT 5", "LIMIT 5"),
    (None, 2, "OFFSET 2 ROWS", "LIMIT -1 OFFSET 2", "OFFSET 2"),
    (
        5,
        2,
        "OFFSET 2 ROWS FETCH NEXT 5 ROWS ONLY",
        "LIMIT 5 OFFSET 2",
        "OFFSET 2 LIMIT 5",
    ),
    (0, None, "OFFSET 0 ROWS FETCH NEXT 0 ROWS ONLY", "LIMIT 0", "LIMIT 0"),
    (None, 0, "OFFSET 0 ROWS", "LIMIT -1 OFFSET 0", "OFFSET 0"),
    (
        0,
        0,
        "OFFSET 0 ROWS FETCH NEXT 0 ROWS ONLY",
        "LIMIT 0 OFFSET 0",
        "OFFSET 0 LIMIT 0",
    ),
    (
        0,
        3,
        "OFFSET 3 ROWS FETCH NEXT 0 ROWS ONLY",
        "LIMIT 0 OFFSET 3",
        "OFFSET 3 LIMIT 0",
    ),
]


@pytest.mark.parametrize(
    "visitor_cls, expected_column",
    [
        (sql.AstToSqlVisitor, 2),
        (sql.AstToSqliteSqlVisitor, 3),
        (sql.AstToAthenaSqlVisitor, 4),
    ],
)
@pytest.mark.parametrize("case", PAGING_CASES, ids=[str(c[:2]) for c in PAGING_CASES])
def test_paging_clause(visitor_cls, expected_column, case):
    top, skip = case[:2]

    assert visitor_cls().paging_clause(top, skip) == case[expected_column]


@pytest.mark.parametrize(
    "top, skip",
    [
        (-1, None),
        (None, -1),
        (5, -1),
        ("5", None),
        (None, "1; DROP TABLE x"),
        (True, 1),
    ],
)
def test_paging_clause_rejects_invalid_values(top, skip):
    with pytest.raises(exceptions.InvalidQueryOptionException):
        sql.AstToSqlVisitor().paging_clause(top, skip)
