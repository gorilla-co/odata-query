import pytest

from odata_query.sql import athena


@pytest.mark.parametrize(
    "odata_query, expected_sql",
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
        ("eac gt 1 eq true", '("eac" > 1) = TRUE'),
        ("true eq eac gt 1", 'TRUE = ("eac" > 1)'),
        ("eac add 10 gt 1000", '"eac" + 10 > 1000'),
        ("eac add 10 gt eac sub 10", '"eac" + 10 > "eac" - 10'),
        ("eac mul 10 div 10 eq eac", '"eac" * 10 / 10 = "eac"'),
        ("eac mod 10 add -1 le eac", '"eac" % 10 + -1 <= "eac"'),
        (
            "period_start add duration'P365D' ge period_end",
            '"period_start" + INTERVAL \'365\' DAY >= "period_end"',
        ),
        (
            "period_start add duration'P365DT12H1M1.1S' ge period_end",
            "\"period_start\" + (INTERVAL '365' DAY + INTERVAL '12' HOUR + INTERVAL '1' MINUTE + INTERVAL '1' SECOND + INTERVAL '100' MILLISECOND) >= \"period_end\"",
        ),
        (
            "period_start add duration'PT1S' ge period_end",
            '"period_start" + INTERVAL \'1\' SECOND >= "period_end"',
        ),
        ("year(period_start) eq 2019", 'year("period_start") = 2019'),
        (
            "period_end lt now() sub duration'P365D'",
            "\"period_end\" < CURRENT_TIMESTAMP - INTERVAL '365' DAY",
        ),
        (
            "endswith(meter_id, '999') and floor(value) le 2",
            'strpos("meter_id", \'999\') = length("meter_id") - length(\'999\') + 1 AND floor("value") <= 2',
        ),
        (
            "startswith(trim(meter_id), '999')",
            "strpos(trim(\"meter_id\"), '999') = 1",
        ),
        (
            "year(date(now())) eq 2020",
            "year(date_trunc(day, CURRENT_TIMESTAMP)) = 2020",
        ),
        ("length(concat('abc', 'def')) lt 10", "length(concat('abc', 'def')) < 10"),
        (
            "length(concat(('1', '2'), ('3', '4'))) eq 4",
            "cardinality(concat(('1', '2'), ('3', '4'))) = 4",
        ),
        ("round(floor(123.12)) eq 123", "round(floor(123.12)) = 123"),
        (
            "indexof(substring('abcdefghi', 3), 'hi') gt 1",
            "strpos(substr('abcdefghi', 3 + 1), 'hi') - 1 > 1",
        ),
        (
            "contains(meter_id, sub_meter_id)",
            'strpos("meter_id", "sub_meter_id") > 0',
        ),
        (
            "year(supply_start_date) eq (year(now()) sub 1)",
            'year("supply_start_date") = year(CURRENT_TIMESTAMP) - 1',
        ),
        (
            "measurement_class eq 'C' and endswith(data_collector, 'rie')",
            "\"measurement_class\" = 'C' AND strpos(\"data_collector\", 'rie') = length(\"data_collector\") - length('rie') + 1",
        ),
    ],
)
def test_odata_filter_to_sql(odata_query: str, expected_sql: str, lexer, parser):
    ast = parser.parse(lexer.tokenize(odata_query))
    sql = athena.AstToAthenaSqlVisitor().visit(ast)

    assert sql == expected_sql
