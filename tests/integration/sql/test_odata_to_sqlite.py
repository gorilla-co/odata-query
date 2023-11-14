import pytest

from odata_query import exceptions as ex, sql


@pytest.mark.parametrize(
    "odata_query, expected",
    [
        ("meter_id eq '1'", "\"meter_id\" = '1'"),
        ("meter_id ne '1'", "\"meter_id\" != '1'"),
        ("meter_id eq 'o''reilly'''", "\"meter_id\" = 'o''reilly'''"),
        (
            "meter_id eq 6c0e37e3-e856-45ee-bd58-484b11882c67",
            "\"meter_id\" = '6c0e37e3-e856-45ee-bd58-484b11882c67'",
        ),
        ("meter_id in ('1',)", "\"meter_id\" IN ('1')"),
        ("meter_id in ('1', '2')", "\"meter_id\" IN ('1', '2')"),
        ("not (meter_id in ('1', '2'))", "NOT \"meter_id\" IN ('1', '2')"),
        ("meter_id eq null", '"meter_id" IS NULL'),
        ("meter_id ne null", '"meter_id" IS NOT NULL'),
        ("eac gt 10", '"eac" > 10'),
        ("eac ge 10", '"eac" >= 10'),
        ("eac lt 10", '"eac" < 10'),
        ("eac le 10", '"eac" <= 10'),
        ("eac gt 1.0 and eac lt 10.0", '"eac" > 1.0 AND "eac" < 10.0'),
        ("eac ge 1.0 and eac le 10.0", '"eac" >= 1.0 AND "eac" <= 10.0'),
        (
            "eac gt 1 and eac lt 1 and meter_id eq '1'",
            '"eac" > 1 AND "eac" < 1 AND "meter_id" = \'1\'',
        ),
        # OData spec defines AND with higher precedence than OR:
        (
            "eac gt 1 and eac lt 10 or eac eq 5 and eac ne 10",
            '("eac" > 1 AND "eac" < 10) OR ("eac" = 5 AND "eac" != 10)',
        ),
        # Unless overridden by parentheses:
        (
            "eac gt 1 and (eac lt 10 or eac eq 5) and eac ne 10",
            '"eac" > 1 AND ("eac" < 10 OR "eac" = 5) AND "eac" != 10',
        ),
        ("not (eac gt 10 and eac lt 20)", 'NOT ("eac" > 10 AND "eac" < 20)'),
        ("eac gt 1 eq true", '("eac" > 1) = 1'),
        ("true eq eac gt 1", '1 = ("eac" > 1)'),
        ("eac add 10 gt 1000", '"eac" + 10 > 1000'),
        ("eac add 10 gt eac sub 10", '"eac" + 10 > "eac" - 10'),
        ("eac mul 10 div 10 eq eac", '"eac" * 10 / 10 = "eac"'),
        ("eac mod 10 add -1 le eac", '"eac" % 10 + -1 <= "eac"'),
        (
            "period_start gt 2020-01-01T00:00:00",
            "\"period_start\" > DATETIME('2020-01-01T00:00:00')",
        ),
        (
            "period_start add duration'P365D' ge period_end",
            '"period_start" + INTERVAL \'365\' DAY >= "period_end"',
        ),
        (
            "period_start add duration'P365DT12H1M1.1S' ge period_end",
            "\"period_start\" + (INTERVAL '365' DAY + INTERVAL '12' HOUR + INTERVAL '1' MINUTE + INTERVAL '1.1' SECOND) >= \"period_end\"",
        ),
        (
            "period_start add duration'PT1S' ge period_end",
            '"period_start" + INTERVAL \'1\' SECOND >= "period_end"',
        ),
        (
            "year(period_start) eq 2019",
            "CAST(STRFTIME('%Y', \"period_start\") AS INTEGER) = 2019",
        ),
        (
            "period_end lt now() sub duration'P365D'",
            "\"period_end\" < DATETIME('now') - INTERVAL '365' DAY",
        ),
        (
            "startswith(trim(meter_id), '999')",
            "TRIM(\"meter_id\") LIKE '999%'",
        ),
        (
            "year(date(now())) eq 2020",
            "CAST(STRFTIME('%Y', DATE(DATETIME('now'))) AS INTEGER) = 2020",
        ),
        ("length(concat('abc', 'def')) lt 10", "LENGTH('abc' || 'def') < 10"),
        (
            "length(concat(('1', '2'), ('3', '4'))) eq 4",
            "LENGTH(('1', '2') || ('3', '4')) = 4",
        ),
        (
            "indexof(substring('abcdefghi', 3), 'hi') gt 1",
            "INSTR(SUBSTR('abcdefghi', 3 + 1), 'hi') - 1 > 1",
        ),
        (
            "substring('hello', 1, 3) eq 'ell'",
            "SUBSTR('hello', 1 + 1, 3) = 'ell'",
        ),
        ("substring((1, 2, 3), 1)", ex.UnsupportedFunctionException),
        ("substring((1, 2, 3), 1, 1)", ex.UnsupportedFunctionException),
        (
            "contains(meter_id, sub_meter_id)",
            "\"meter_id\" LIKE '%' || \"sub_meter_id\" || '%'",
        ),
        (
            "year(supply_start_date) eq (year(now()) sub 1)",
            "CAST(STRFTIME('%Y', \"supply_start_date\") AS INTEGER) = CAST(STRFTIME('%Y', DATETIME('now')) AS INTEGER) - 1",
        ),
        (
            "measurement_class eq 'C' and endswith(data_collector, 'rie')",
            "\"measurement_class\" = 'C' AND \"data_collector\" LIKE '%rie'",
        ),
        # GITHUB-47
        (
            "contains(tolower(name), tolower('A'))",
            "LOWER(\"name\") LIKE '%' || LOWER('A') || '%'",
        ),
    ],
)
def test_odata_filter_to_sql(odata_query: str, expected: str, lexer, parser):
    ast = parser.parse(lexer.tokenize(odata_query))
    visitor = sql.AstToSqliteSqlVisitor()

    if isinstance(expected, str):
        res = visitor.visit(ast)
        assert res == expected
    else:
        with pytest.raises(expected):
            res = visitor.visit(ast)
