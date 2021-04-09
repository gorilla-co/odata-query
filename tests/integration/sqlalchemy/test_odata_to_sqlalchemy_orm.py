import datetime as dt

import pytest
from sqlalchemy.sql.expression import column, literal

from odata_query.sqlalchemy import AstToSqlAlchemyClauseVisitor


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
    ],
)
def test_odata_filter_to_sqlalchemy_orm_query(
    odata_query: str, expected_q: str, lexer, parser
):
    ast = parser.parse(lexer.tokenize(odata_query))
    transformer = AstToSqlAlchemyClauseVisitor()
    res_q = transformer.visit(ast)

    assert res_q.compare(expected_q), (str(res_q), str(expected_q))
