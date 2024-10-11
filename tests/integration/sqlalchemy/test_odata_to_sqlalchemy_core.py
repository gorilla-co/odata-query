import datetime as dt
import uuid

import pytest
from sqlalchemy.sql import functions
from sqlalchemy.sql.expression import cast, extract, literal
from sqlalchemy.types import Date, Time

from odata_query.sqlalchemy import AstToSqlAlchemyCoreVisitor, functions_ext

from . import models

BlogPost = models.Base.metadata.tables["blogpost"]
Author = models.Base.metadata.tables["author"]
Comment = models.Base.metadata.tables["comment"]


def tz(offset: int) -> dt.tzinfo:
    return dt.timezone(dt.timedelta(hours=offset))


@pytest.mark.parametrize(
    "odata_query, expected_q",
    [
        (
            "id eq a7af27e6-f5a0-11e9-9649-0a252986adba",
            BlogPost.c.id == uuid.UUID("a7af27e6-f5a0-11e9-9649-0a252986adba"),
        ),
        ("my_app.c.id eq 1", BlogPost.c.id == 1),
        (
            "id in (a7af27e6-f5a0-11e9-9649-0a252986adba, 800c56e4-354d-11eb-be38-3af9d323e83c)",
            BlogPost.c.id.in_(
                [
                    literal(uuid.UUID("a7af27e6-f5a0-11e9-9649-0a252986adba")),
                    literal(uuid.UUID("800c56e4-354d-11eb-be38-3af9d323e83c")),
                ]
            ),
        ),
        ("id eq 4", BlogPost.c.id == 4),
        ("id ne 4", BlogPost.c.id != 4),
        ("4 eq id", 4 == BlogPost.c.id),
        ("4 ne id", 4 != BlogPost.c.id),
        (
            "published_at gt 2018-01-01",
            BlogPost.c.published_at > dt.date(2018, 1, 1),
        ),
        (
            "published_at ge 2018-01-01",
            BlogPost.c.published_at >= dt.date(2018, 1, 1),
        ),
        (
            "published_at lt 2018-01-01",
            BlogPost.c.published_at < dt.date(2018, 1, 1),
        ),
        (
            "published_at le 2018-01-01",
            BlogPost.c.published_at <= dt.date(2018, 1, 1),
        ),
        (
            "2018-01-01 gt published_at",
            literal(dt.date(2018, 1, 1)) > BlogPost.c.published_at,
        ),
        (
            "2018-01-01 ge published_at",
            literal(dt.date(2018, 1, 1)) >= BlogPost.c.published_at,
        ),
        (
            "published_at gt 2018-01-01T01:02",
            BlogPost.c.published_at > dt.datetime(2018, 1, 1, 1, 2),
        ),
        (
            "published_at gt 2018-01-01T01:02:03",
            BlogPost.c.published_at > dt.datetime(2018, 1, 1, 1, 2, 3),
        ),
        (
            "published_at gt 2018-01-01T01:02:03.123",
            BlogPost.c.published_at > dt.datetime(2018, 1, 1, 1, 2, 3, 123_000),
        ),
        (
            "published_at gt 2018-01-01T01:02:03.123456",
            BlogPost.c.published_at > dt.datetime(2018, 1, 1, 1, 2, 3, 123_456),
        ),
        (
            "published_at gt 2018-01-01T01:02Z",
            BlogPost.c.published_at > dt.datetime(2018, 1, 1, 1, 2, tzinfo=tz(0)),
        ),
        (
            "published_at gt 2018-01-01T01:02:03Z",
            BlogPost.c.published_at > dt.datetime(2018, 1, 1, 1, 2, 3, tzinfo=tz(0)),
        ),
        (
            "published_at gt 2018-01-01T01:02:03.123Z",
            BlogPost.c.published_at
            > dt.datetime(2018, 1, 1, 1, 2, 3, 123_000, tzinfo=tz(0)),
        ),
        (
            "published_at gt 2018-01-01T01:02+02:00",
            BlogPost.c.published_at > dt.datetime(2018, 1, 1, 1, 2, tzinfo=tz(+2)),
        ),
        (
            "published_at gt 2018-01-01T01:02-02:00",
            BlogPost.c.published_at > dt.datetime(2018, 1, 1, 1, 2, tzinfo=tz(-2)),
        ),
        (
            "id in (1, 2, 3)",
            BlogPost.c.id.in_([literal(1), literal(2), literal(3)]),
        ),
        ("id eq null", BlogPost.c.id == None),  # noqa:E711
        ("id ne null", BlogPost.c.id != None),  # noqa:E711
        ("not (id eq 1)", ~(BlogPost.c.id == 1)),
        ("id eq 1 or id eq 2", (BlogPost.c.id == 1) | (BlogPost.c.id == 2)),
        (
            "id eq 1 and content eq 'executing'",
            (BlogPost.c.id == 1) & (BlogPost.c.content == "executing"),
        ),
        (
            "id eq 1 and (content eq 'executing' or content eq 'failed')",
            (BlogPost.c.id == 1)
            & ((BlogPost.c.content == "executing") | (BlogPost.c.content == "failed")),
        ),
        ("id eq 1 add 1", BlogPost.c.id == literal(1) + literal(1)),
        ("id eq 2 sub 1", BlogPost.c.id == literal(2) - literal(1)),
        ("id eq 2 mul 2", BlogPost.c.id == literal(2) * literal(2)),
        ("id eq 2 div 2", BlogPost.c.id == literal(2) / literal(2)),
        ("id eq 5 mod 4", BlogPost.c.id == literal(5) % literal(4)),
        ("id eq 2 add -1", BlogPost.c.id == literal(2) + literal(-1)),
        ("id eq id sub 1", BlogPost.c.id == BlogPost.c.id - literal(1)),
        (
            "title eq 'donut' add 'tello'",
            BlogPost.c.title == literal("donut") + literal("tello"),
        ),
        (
            "title eq content add content",
            BlogPost.c.title == BlogPost.c.content + BlogPost.c.content,
        ),
        (
            "published_at eq 2019-01-01T00:00:00 add duration'P1DT1H1M1S'",
            BlogPost.c.published_at
            == literal(dt.datetime(2019, 1, 1, 0, 0, 0))
            + dt.timedelta(days=1, hours=1, minutes=1, seconds=1),
        ),
        (
            "published_at eq 2019-01-01T00:00:00 add duration'P1Y'",
            BlogPost.c.published_at
            == literal(dt.datetime(2019, 1, 1, 0, 0, 0))
            + dt.timedelta(days=365.25),  # 1 times 365.25 (average year in days)
        ),
        (
            "published_at eq 2019-01-01T00:00:00 add duration'P2M'",
            BlogPost.c.published_at
            == literal(dt.datetime(2019, 1, 1, 0, 0, 0))
            + dt.timedelta(days=60.88),  # 2 times 30.44 (average month in days)
        ),
        ("contains(title, 'copy')", BlogPost.c.title.contains("copy")),
        ("startswith(title, 'copy')", BlogPost.c.title.startswith("copy")),
        ("endswith(title, 'bla')", BlogPost.c.title.endswith("bla")),
        (
            "id eq length(title)",
            BlogPost.c.id == functions.char_length(BlogPost.c.title),
        ),
        ("length(title) eq 10", functions.char_length(BlogPost.c.title) == 10),
        ("10 eq length(title)", 10 == functions.char_length(BlogPost.c.title)),
        (
            "length(title) eq length('flippot')",
            functions.char_length(BlogPost.c.title) == functions.char_length("flippot"),
        ),
        (
            "title eq concat('a', 'b')",
            BlogPost.c.title == functions.concat("a", "b"),
        ),
        (
            "title eq concat('test', id)",
            BlogPost.c.title == functions.concat("test", BlogPost.c.id),
        ),
        (
            "title eq concat(concat('a', 'b'), 'c')",
            BlogPost.c.title == functions.concat(functions.concat("a", "b"), "c"),
        ),
        (
            "concat(title, 'a') eq 'testa'",
            functions.concat(BlogPost.c.title, "a") == "testa",
        ),
        (
            "indexof(title, 'Copy') eq 6",
            functions_ext.strpos(BlogPost.c.title, "Copy") - 1 == 6,
        ),
        (
            "substring(title, 0) eq 'Copy'",
            functions_ext.substr(BlogPost.c.title, literal(0) + 1) == "Copy",
        ),
        (
            "substring(title, 0, 4) eq 'Copy'",
            functions_ext.substr(BlogPost.c.title, literal(0) + 1, 4) == "Copy",
        ),
        (
            "matchesPattern(title, 'C.py')",
            BlogPost.c.title.regexp_match("C.py"),
        ),
        (
            "tolower(title) eq 'copy'",
            functions_ext.lower(BlogPost.c.title) == "copy",
        ),
        (
            "toupper(title) eq 'COPY'",
            functions_ext.upper(BlogPost.c.title) == "COPY",
        ),
        (
            "trim(title) eq 'copy'",
            functions_ext.ltrim(functions_ext.rtrim(BlogPost.c.title)) == "copy",
        ),
        (
            "date(published_at) eq 2019-01-01",
            cast(BlogPost.c.published_at, Date) == dt.date(2019, 1, 1),
        ),
        (
            "day(published_at) eq 1",
            extract("day", BlogPost.c.published_at) == 1,
        ),
        (
            "hour(published_at) eq 1",
            extract("hour", BlogPost.c.published_at) == 1,
        ),
        (
            "minute(published_at) eq 1",
            extract("minute", BlogPost.c.published_at) == 1,
        ),
        (
            "month(published_at) eq 1",
            extract("month", BlogPost.c.published_at) == 1,
        ),
        ("published_at eq now()", BlogPost.c.published_at == functions.now()),
        (
            "second(published_at) eq 1",
            extract("second", BlogPost.c.published_at) == 1,
        ),
        (
            "time(published_at) eq 14:00:00",
            cast(BlogPost.c.published_at, Time) == dt.time(14, 0, 0),
        ),
        (
            "year(published_at) eq 2019",
            extract("year", BlogPost.c.published_at) == 2019,
        ),
        ("ceiling(id) eq 1", functions_ext.ceil(BlogPost.c.id) == 1),
        ("floor(id) eq 1", functions_ext.floor(BlogPost.c.id) == 1),
        ("round(id) eq 1", functions_ext.round(BlogPost.c.id) == 1),
        (
            "date(published_at) eq 2019-01-01 add duration'P1D'",
            cast(BlogPost.c.published_at, Date)
            == literal(dt.date(2019, 1, 1)) + dt.timedelta(days=1),
        ),
        (
            "date(published_at) eq 2019-01-01 add duration'-P1D'",
            cast(BlogPost.c.published_at, Date)
            == literal(dt.date(2019, 1, 1)) + -1 * dt.timedelta(days=1),
        ),
        pytest.param(
            "authors/name eq 'Ruben'",
            Author.c.name == "Ruben",
            marks=pytest.mark.xfail(reason="Not implemented yet."),
        ),
        pytest.param(
            "authors/comments/content eq 'Cool!'",
            Comment.c.content == "Cool!",
            marks=pytest.mark.xfail(reason="Not implemented yet."),
        ),
        pytest.param(
            "contains(comments/content, 'Cool')",
            Comment.c.content.contains("Cool"),
            marks=pytest.mark.xfail(reason="Not implemented yet."),
        ),
        # GITHUB-19
        (
            "contains(title, 'TEST') eq true",
            BlogPost.c.title.contains("TEST") == True,  # noqa:E712
        ),
        # GITHUB-47
        (
            "contains(tolower(title), tolower('A'))",
            functions_ext.lower(BlogPost.c.title).contains(functions_ext.lower("A")),
        ),
    ],
)
def test_odata_filter_to_sqlalchemy_query(
    odata_query: str, expected_q: str, lexer, parser
):
    ast = parser.parse(lexer.tokenize(odata_query))
    transformer = AstToSqlAlchemyCoreVisitor(BlogPost)
    res_q = transformer.visit(ast)

    assert res_q.compare(expected_q), (str(res_q), str(expected_q))
