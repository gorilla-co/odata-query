import datetime as dt

import pytest
from sqlalchemy.sql import functions
from sqlalchemy.sql.expression import cast, column, extract, literal
from sqlalchemy.types import Date, Time

from odata_query.sqlalchemy import AstToSqlAlchemyClauseVisitor, functions_ext


def tz(offset: int) -> dt.tzinfo:
    return dt.timezone(dt.timedelta(hours=offset))


@pytest.mark.parametrize(
    "odata_query, expected_q",
    [
        (
            "id eq a7af27e6-f5a0-11e9-9649-0a252986adba",
            column("id") == "a7af27e6-f5a0-11e9-9649-0a252986adba",
        ),
        ("version_id eq 4", column("version_id") == 4),
        ("version_id ne 4", column("version_id") != 4),
        ("4 eq version_id", 4 == column("version_id")),
        ("4 ne version_id", 4 != column("version_id")),
        ("created_at gt 2018-01-01", column("created_at") > dt.date(2018, 1, 1)),
        ("created_at ge 2018-01-01", column("created_at") >= dt.date(2018, 1, 1)),
        ("created_at lt 2018-01-01", column("created_at") < dt.date(2018, 1, 1)),
        ("created_at le 2018-01-01", column("created_at") <= dt.date(2018, 1, 1)),
        (
            "2018-01-01 gt created_at",
            literal(dt.date(2018, 1, 1)) > column("created_at"),
        ),
        (
            "2018-01-01 ge created_at",
            literal(dt.date(2018, 1, 1)) >= column("created_at"),
        ),
        (
            "created_at gt 2018-01-01T01:02",
            column("created_at") > dt.datetime(2018, 1, 1, 1, 2),
        ),
        (
            "created_at gt 2018-01-01T01:02:03",
            column("created_at") > dt.datetime(2018, 1, 1, 1, 2, 3),
        ),
        (
            "created_at gt 2018-01-01T01:02:03.123",
            column("created_at") > dt.datetime(2018, 1, 1, 1, 2, 3, 123_000),
        ),
        (
            "created_at gt 2018-01-01T01:02:03.123456",
            column("created_at") > dt.datetime(2018, 1, 1, 1, 2, 3, 123_456),
        ),
        (
            "created_at gt 2018-01-01T01:02Z",
            column("created_at") > dt.datetime(2018, 1, 1, 1, 2, tzinfo=tz(0)),
        ),
        (
            "created_at gt 2018-01-01T01:02:03Z",
            column("created_at") > dt.datetime(2018, 1, 1, 1, 2, 3, tzinfo=tz(0)),
        ),
        (
            "created_at gt 2018-01-01T01:02:03.123Z",
            column("created_at")
            > dt.datetime(2018, 1, 1, 1, 2, 3, 123_000, tzinfo=tz(0)),
        ),
        (
            "created_at gt 2018-01-01T01:02+02:00",
            column("created_at") > dt.datetime(2018, 1, 1, 1, 2, tzinfo=tz(+2)),
        ),
        (
            "created_at gt 2018-01-01T01:02-02:00",
            column("created_at") > dt.datetime(2018, 1, 1, 1, 2, tzinfo=tz(-2)),
        ),
        (
            "version_id in (1, 2, 3)",
            column("version_id").in_([literal(1), literal(2), literal(3)]),
        ),
        ("version_id eq null", column("version_id") == None),  # noqa:E711
        ("version_id ne null", column("version_id") != None),  # noqa:E711
        ("not (version_id eq 1)", ~(column("version_id") == 1)),
        (
            "version_id eq 1 or version_id eq 2",
            (column("version_id") == 1) | (column("version_id") == 2),
        ),
        (
            "version_id eq 1 and status eq 'executing'",
            (column("version_id") == 1) & (column("status") == "executing"),
        ),
        (
            "version_id eq 1 and (status eq 'executing' or status eq 'failed')",
            (column("version_id") == 1)
            & ((column("status") == "executing") | (column("status") == "failed")),
        ),
        ("version_id eq 1 add 1", column("version_id") == literal(1) + literal(1)),
        ("version_id eq 2 sub 1", column("version_id") == literal(2) - literal(1)),
        ("version_id eq 2 mul 2", column("version_id") == literal(2) * literal(2)),
        ("version_id eq 2 div 2", column("version_id") == literal(2) / literal(2)),
        ("version_id eq 5 mod 4", column("version_id") == literal(5) % literal(4)),
        ("version_id eq 2 add -1", column("version_id") == literal(2) + literal(-1)),
        (
            "version_id eq n_versions sub 1",
            column("version_id") == column("n_versions") - literal(1),
        ),
        (
            "name eq 'donut' add 'tello'",
            column("name") == literal("donut") + literal("tello"),
        ),
        (
            "name eq donut add tello",
            column("name") == column("donut") + column("tello"),
        ),
        ("contains(name, 'copy')", column("name").contains("copy")),
        ("startswith(name, 'copy')", column("name").startswith("copy")),
        ("endswith(name, 'bla')", column("name").endswith("bla")),
        (
            "version_id eq length(name)",
            column("version_id") == functions.char_length(column("name")),
        ),
        ("length(name) eq 10", functions.char_length(column("name")) == 10),
        ("10 eq length(name)", 10 == functions.char_length(column("name"))),
        (
            "length(name) eq length('flippot')",
            functions.char_length(column("name")) == functions.char_length("flippot"),
        ),
        ("name eq concat('a', 'b')", column("name") == functions.concat("a", "b")),
        (
            "name eq concat('test', version_id)",
            column("name") == functions.concat("test", column("version_id")),
        ),
        (
            "name eq concat(concat('a', 'b'), 'c')",
            column("name") == functions.concat(functions.concat("a", "b"), "c"),
        ),
        (
            "concat(name, 'a') eq 'testa'",
            functions.concat(column("name"), "a") == "testa",
        ),
        (
            "indexof(name, 'Copy') eq 6",
            functions_ext.strpos(column("name"), "Copy") - 1 == 6,
        ),
        (
            "substring(name, 0) eq 'Copy'",
            functions_ext.substr(column("name"), literal(0) + 1) == "Copy",
        ),
        (
            "substring(name, 0, 4) eq 'Copy'",
            functions_ext.substr(column("name"), literal(0) + 1, 4) == "Copy",
        ),
        ("matchesPattern(name, 'C.py')", column("name").regexp_match("C.py")),
        ("tolower(name) eq 'copy'", functions_ext.lower(column("name")) == "copy"),
        ("toupper(name) eq 'COPY'", functions_ext.upper(column("name")) == "COPY"),
        (
            "trim(name) eq 'copy'",
            functions_ext.ltrim(functions_ext.rtrim(column("name"))) == "copy",
        ),
        (
            "date(created_at) eq 2019-01-01",
            cast(column("created_at"), Date) == dt.date(2019, 1, 1),
        ),
        ("day(created_at) eq 1", extract(column("created_at"), "day") == 1),
        ("hour(created_at) eq 1", extract(column("created_at"), "hour") == 1),
        ("minute(created_at) eq 1", extract(column("created_at"), "minute") == 1),
        ("month(created_at) eq 1", extract(column("created_at"), "month") == 1),
        ("created_at eq now()", column("created_at") == functions.now()),
        ("second(created_at) eq 1", extract(column("created_at"), "second") == 1),
        (
            "time(created_at) eq 14:00:00",
            cast(column("created_at"), Time) == dt.time(14, 0, 0),
        ),
        ("year(created_at) eq 2019", extract(column("created_at"), "year") == 2019),
    ],
)
def test_odata_filter_to_sqlalchemy_query(
    odata_query: str, expected_q: str, lexer, parser
):
    ast = parser.parse(lexer.tokenize(odata_query))
    transformer = AstToSqlAlchemyClauseVisitor()
    res_q = transformer.visit(ast)

    assert res_q.compare(expected_q), (str(res_q), str(expected_q))
