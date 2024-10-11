import datetime as dt
import uuid

import pytest
from sqlalchemy.sql import functions
from sqlalchemy.sql.expression import cast, extract, literal
from sqlalchemy.types import Date, Time

from odata_query.sqlalchemy import AstToSqlAlchemyOrmVisitor, functions_ext

from .models import Author, BlogPost, Comment


def tz(offset: int) -> dt.tzinfo:
    return dt.timezone(dt.timedelta(hours=offset))


@pytest.mark.parametrize(
    "odata_query, expected_q",
    [
        (
            "id eq a7af27e6-f5a0-11e9-9649-0a252986adba",
            BlogPost.id == uuid.UUID("a7af27e6-f5a0-11e9-9649-0a252986adba"),
        ),
        ("my_app.id eq 1", BlogPost.id == 1),
        (
            "id in (a7af27e6-f5a0-11e9-9649-0a252986adba, 800c56e4-354d-11eb-be38-3af9d323e83c)",
            BlogPost.id.in_(
                [
                    literal(uuid.UUID("a7af27e6-f5a0-11e9-9649-0a252986adba")),
                    literal(uuid.UUID("800c56e4-354d-11eb-be38-3af9d323e83c")),
                ]
            ),
        ),
        ("id eq 4", BlogPost.id == 4),
        ("id ne 4", BlogPost.id != 4),
        ("4 eq id", 4 == BlogPost.id),
        ("4 ne id", 4 != BlogPost.id),
        ("published_at gt 2018-01-01", BlogPost.published_at > dt.date(2018, 1, 1)),
        ("published_at ge 2018-01-01", BlogPost.published_at >= dt.date(2018, 1, 1)),
        ("published_at lt 2018-01-01", BlogPost.published_at < dt.date(2018, 1, 1)),
        ("published_at le 2018-01-01", BlogPost.published_at <= dt.date(2018, 1, 1)),
        (
            "2018-01-01 gt published_at",
            literal(dt.date(2018, 1, 1)) > BlogPost.published_at,
        ),
        (
            "2018-01-01 ge published_at",
            literal(dt.date(2018, 1, 1)) >= BlogPost.published_at,
        ),
        (
            "published_at gt 2018-01-01T01:02",
            BlogPost.published_at > dt.datetime(2018, 1, 1, 1, 2),
        ),
        (
            "published_at gt 2018-01-01T01:02:03",
            BlogPost.published_at > dt.datetime(2018, 1, 1, 1, 2, 3),
        ),
        (
            "published_at gt 2018-01-01T01:02:03.123",
            BlogPost.published_at > dt.datetime(2018, 1, 1, 1, 2, 3, 123_000),
        ),
        (
            "published_at gt 2018-01-01T01:02:03.123456",
            BlogPost.published_at > dt.datetime(2018, 1, 1, 1, 2, 3, 123_456),
        ),
        (
            "published_at gt 2018-01-01T01:02Z",
            BlogPost.published_at > dt.datetime(2018, 1, 1, 1, 2, tzinfo=tz(0)),
        ),
        (
            "published_at gt 2018-01-01T01:02:03Z",
            BlogPost.published_at > dt.datetime(2018, 1, 1, 1, 2, 3, tzinfo=tz(0)),
        ),
        (
            "published_at gt 2018-01-01T01:02:03.123Z",
            BlogPost.published_at
            > dt.datetime(2018, 1, 1, 1, 2, 3, 123_000, tzinfo=tz(0)),
        ),
        (
            "published_at gt 2018-01-01T01:02+02:00",
            BlogPost.published_at > dt.datetime(2018, 1, 1, 1, 2, tzinfo=tz(+2)),
        ),
        (
            "published_at gt 2018-01-01T01:02-02:00",
            BlogPost.published_at > dt.datetime(2018, 1, 1, 1, 2, tzinfo=tz(-2)),
        ),
        ("id in (1, 2, 3)", BlogPost.id.in_([literal(1), literal(2), literal(3)])),
        ("id eq null", BlogPost.id == None),  # noqa:E711
        ("id ne null", BlogPost.id != None),  # noqa:E711
        ("not (id eq 1)", ~(BlogPost.id == 1)),
        ("id eq 1 or id eq 2", (BlogPost.id == 1) | (BlogPost.id == 2)),
        (
            "id eq 1 and content eq 'executing'",
            (BlogPost.id == 1) & (BlogPost.content == "executing"),
        ),
        (
            "id eq 1 and (content eq 'executing' or content eq 'failed')",
            (BlogPost.id == 1)
            & ((BlogPost.content == "executing") | (BlogPost.content == "failed")),
        ),
        ("id eq 1 add 1", BlogPost.id == literal(1) + literal(1)),
        ("id eq 2 sub 1", BlogPost.id == literal(2) - literal(1)),
        ("id eq 2 mul 2", BlogPost.id == literal(2) * literal(2)),
        ("id eq 2 div 2", BlogPost.id == literal(2) / literal(2)),
        ("id eq 5 mod 4", BlogPost.id == literal(5) % literal(4)),
        ("id eq 2 add -1", BlogPost.id == literal(2) + literal(-1)),
        ("id eq id sub 1", BlogPost.id == BlogPost.id - literal(1)),
        (
            "title eq 'donut' add 'tello'",
            BlogPost.title == literal("donut") + literal("tello"),
        ),
        (
            "title eq content add content",
            BlogPost.title == BlogPost.content + BlogPost.content,
        ),
        (
            "published_at eq 2019-01-01T00:00:00 add duration'P1DT1H1M1S'",
            BlogPost.published_at
            == literal(dt.datetime(2019, 1, 1, 0, 0, 0))
            + dt.timedelta(days=1, hours=1, minutes=1, seconds=1),
        ),
        (
            "published_at eq 2019-01-01T00:00:00 add duration'P1Y'",
            BlogPost.published_at
            == literal(dt.datetime(2019, 1, 1, 0, 0, 0))
            + dt.timedelta(days=365.25),  # 1 times 365.25 (average year in days)
        ),
        (
            "published_at eq 2019-01-01T00:00:00 add duration'P2M'",
            BlogPost.published_at
            == literal(dt.datetime(2019, 1, 1, 0, 0, 0))
            + dt.timedelta(days=60.88),  # 2 times 30.44 (average month in days)
        ),
        ("contains(title, 'copy')", BlogPost.title.contains("copy")),
        ("startswith(title, 'copy')", BlogPost.title.startswith("copy")),
        ("endswith(title, 'bla')", BlogPost.title.endswith("bla")),
        ("id eq length(title)", BlogPost.id == functions.char_length(BlogPost.title)),
        ("length(title) eq 10", functions.char_length(BlogPost.title) == 10),
        ("10 eq length(title)", 10 == functions.char_length(BlogPost.title)),
        (
            "length(title) eq length('flippot')",
            functions.char_length(BlogPost.title) == functions.char_length("flippot"),
        ),
        ("title eq concat('a', 'b')", BlogPost.title == functions.concat("a", "b")),
        (
            "title eq concat('test', id)",
            BlogPost.title == functions.concat("test", BlogPost.id),
        ),
        (
            "title eq concat(concat('a', 'b'), 'c')",
            BlogPost.title == functions.concat(functions.concat("a", "b"), "c"),
        ),
        (
            "concat(title, 'a') eq 'testa'",
            functions.concat(BlogPost.title, "a") == "testa",
        ),
        (
            "indexof(title, 'Copy') eq 6",
            functions_ext.strpos(BlogPost.title, "Copy") - 1 == 6,
        ),
        (
            "substring(title, 0) eq 'Copy'",
            functions_ext.substr(BlogPost.title, literal(0) + 1) == "Copy",
        ),
        (
            "substring(title, 0, 4) eq 'Copy'",
            functions_ext.substr(BlogPost.title, literal(0) + 1, 4) == "Copy",
        ),
        ("matchesPattern(title, 'C.py')", BlogPost.title.regexp_match("C.py")),
        ("tolower(title) eq 'copy'", functions_ext.lower(BlogPost.title) == "copy"),
        ("toupper(title) eq 'COPY'", functions_ext.upper(BlogPost.title) == "COPY"),
        (
            "trim(title) eq 'copy'",
            functions_ext.ltrim(functions_ext.rtrim(BlogPost.title)) == "copy",
        ),
        (
            "date(published_at) eq 2019-01-01",
            cast(BlogPost.published_at, Date) == dt.date(2019, 1, 1),
        ),
        ("day(published_at) eq 1", extract("day", BlogPost.published_at) == 1),
        ("hour(published_at) eq 1", extract("hour", BlogPost.published_at) == 1),
        ("minute(published_at) eq 1", extract("minute", BlogPost.published_at) == 1),
        ("month(published_at) eq 1", extract("month", BlogPost.published_at) == 1),
        ("published_at eq now()", BlogPost.published_at == functions.now()),
        ("second(published_at) eq 1", extract("second", BlogPost.published_at) == 1),
        (
            "time(published_at) eq 14:00:00",
            cast(BlogPost.published_at, Time) == dt.time(14, 0, 0),
        ),
        ("year(published_at) eq 2019", extract("year", BlogPost.published_at) == 2019),
        ("ceiling(id) eq 1", functions_ext.ceil(BlogPost.id) == 1),
        ("floor(id) eq 1", functions_ext.floor(BlogPost.id) == 1),
        ("round(id) eq 1", functions_ext.round(BlogPost.id) == 1),
        (
            "date(published_at) eq 2019-01-01 add duration'P1D'",
            cast(BlogPost.published_at, Date)
            == literal(dt.date(2019, 1, 1)) + dt.timedelta(days=1),
        ),
        (
            "date(published_at) eq 2019-01-01 add duration'-P1D'",
            cast(BlogPost.published_at, Date)
            == literal(dt.date(2019, 1, 1)) + -1 * dt.timedelta(days=1),
        ),
        ("authors/name eq 'Ruben'", Author.name == "Ruben"),
        ("authors/comments/content eq 'Cool!'", Comment.content == "Cool!"),
        ("contains(comments/content, 'Cool')", Comment.content.contains("Cool")),
        # GITHUB-19
        (
            "contains(title, 'TEST') eq true",
            BlogPost.title.contains("TEST") == True,  # noqa:E712
        ),
        # GITHUB-47
        (
            "contains(tolower(title), tolower('A'))",
            functions_ext.lower(BlogPost.title).contains(functions_ext.lower("A")),
        ),
    ],
)
def test_odata_filter_to_sqlalchemy_query(
    odata_query: str, expected_q: str, lexer, parser
):
    ast = parser.parse(lexer.tokenize(odata_query))
    transformer = AstToSqlAlchemyOrmVisitor(BlogPost)
    res_q = transformer.visit(ast)

    assert res_q.compare(expected_q), (str(res_q), str(expected_q))
