import datetime as dt
import uuid

import pytest
from django.db.models import F, Q, Value, functions as fn, lookups as lu

from odata_query import exceptions
from odata_query.django import AstToDjangoQVisitor
from odata_query.django.django_q_ext import NotEqual

from .models import BlogPost


def tz(offset: int) -> dt.tzinfo:
    return dt.timezone(dt.timedelta(hours=offset))


@pytest.mark.parametrize(
    "odata_query, expected_q",
    [
        (
            "id eq a7af27e6-f5a0-11e9-9649-0a252986adba",
            Q(
                lu.Exact(
                    F("id"), Value(uuid.UUID("a7af27e6-f5a0-11e9-9649-0a252986adba"))
                )
            ),
        ),
        ("my_app.id eq 1", Q(lu.Exact(F("id"), Value(1)))),
        (
            "id in (a7af27e6-f5a0-11e9-9649-0a252986adba, 800c56e4-354d-11eb-be38-3af9d323e83c)",
            Q(
                lu.In(
                    F("id"),
                    [
                        Value(uuid.UUID("a7af27e6-f5a0-11e9-9649-0a252986adba")),
                        Value(uuid.UUID("800c56e4-354d-11eb-be38-3af9d323e83c")),
                    ],
                ),
            ),
        ),
        ("id eq 4", Q(lu.Exact(F("id"), Value(4)))),
        ("id ne 4", Q(NotEqual(F("id"), Value(4)))),
        ("4 eq id", Q(lu.Exact(Value(4), F("id")))),
        ("4 ne id", Q(NotEqual(Value(4), F("id")))),
        (
            "published_at gt 2018-01-01",
            Q(lu.GreaterThan(F("published_at"), Value(dt.date(2018, 1, 1)))),
        ),
        (
            "published_at ge 2018-01-01",
            Q(lu.GreaterThanOrEqual(F("published_at"), Value(dt.date(2018, 1, 1)))),
        ),
        (
            "published_at lt 2018-01-01",
            Q(lu.LessThan(F("published_at"), Value(dt.date(2018, 1, 1)))),
        ),
        (
            "published_at le 2018-01-01",
            Q(lu.LessThanOrEqual(F("published_at"), Value(dt.date(2018, 1, 1)))),
        ),
        (
            "2018-01-01 gt published_at",
            Q(lu.GreaterThan(Value(dt.date(2018, 1, 1)), F("published_at"))),
        ),
        (
            "2018-01-01 ge published_at",
            Q(lu.GreaterThanOrEqual(Value(dt.date(2018, 1, 1)), F("published_at"))),
        ),
        (
            "published_at gt 2018-01-01T01:02",
            Q(lu.GreaterThan(F("published_at"), Value(dt.datetime(2018, 1, 1, 1, 2)))),
        ),
        (
            "published_at gt 2018-01-01T01:02:03",
            Q(
                lu.GreaterThan(
                    F("published_at"), Value(dt.datetime(2018, 1, 1, 1, 2, 3))
                )
            ),
        ),
        (
            "published_at gt 2018-01-01T01:02:03.123",
            Q(
                lu.GreaterThan(
                    F("published_at"),
                    Value(dt.datetime(2018, 1, 1, 1, 2, 3, 123_000)),
                )
            ),
        ),
        (
            "published_at gt 2018-01-01T01:02:03.123456",
            Q(
                lu.GreaterThan(
                    F("published_at"), Value(dt.datetime(2018, 1, 1, 1, 2, 3, 123_456))
                )
            ),
        ),
        (
            "published_at gt 2018-01-01T01:02Z",
            Q(
                lu.GreaterThan(
                    F("published_at"),
                    Value(dt.datetime(2018, 1, 1, 1, 2, tzinfo=tz(0))),
                )
            ),
        ),
        (
            "published_at gt 2018-01-01T01:02:03Z",
            Q(
                lu.GreaterThan(
                    F("published_at"),
                    Value(dt.datetime(2018, 1, 1, 1, 2, 3, tzinfo=tz(0))),
                )
            ),
        ),
        (
            "published_at gt 2018-01-01T01:02:03.123Z",
            Q(
                lu.GreaterThan(
                    F("published_at"),
                    Value(dt.datetime(2018, 1, 1, 1, 2, 3, 123_000, tzinfo=tz(0))),
                )
            ),
        ),
        (
            "published_at gt 2018-01-01T01:02+02:00",
            Q(
                lu.GreaterThan(
                    F("published_at"),
                    Value(dt.datetime(2018, 1, 1, 1, 2, tzinfo=tz(+2))),
                )
            ),
        ),
        (
            "published_at gt 2018-01-01T01:02-02:00",
            Q(
                lu.GreaterThan(
                    F("published_at"),
                    Value(dt.datetime(2018, 1, 1, 1, 2, tzinfo=tz(-2))),
                )
            ),
        ),
        (
            "id in (1, 2, 3)",
            Q(lu.In(F("id"), [Value(1), Value(2), Value(3)])),
        ),
        ("id eq null", Q(lu.IsNull(F("id"), True))),
        ("id ne null", Q(lu.IsNull(F("id"), False))),
        ("not (id eq 1)", ~Q(lu.Exact(F("id"), Value(1)))),
        (
            "id eq 1 or id eq 2",
            Q(lu.Exact(F("id"), Value(1))) | Q(lu.Exact(F("id"), Value(2))),
        ),
        (
            "id eq 1 and content eq 'executing'",
            Q(lu.Exact(F("id"), Value(1)))
            & Q(lu.Exact(F("content"), Value("executing"))),
        ),
        (
            "id eq 1 and (content eq 'executing' or content eq 'failed')",
            Q(lu.Exact(F("id"), Value(1)))
            & (
                Q(lu.Exact(F("content"), Value("executing")))
                | Q(lu.Exact(F("content"), Value("failed")))
            ),
        ),
        ("id eq 1 add 1", Q(lu.Exact(F("id"), Value(1) + Value(1)))),
        ("id eq 2 sub 1", Q(lu.Exact(F("id"), Value(2) - Value(1)))),
        ("id eq 2 mul 2", Q(lu.Exact(F("id"), Value(2) * Value(2)))),
        ("id eq 2 div 2", Q(lu.Exact(F("id"), Value(2) / Value(2)))),
        ("id eq 5 mod 4", Q(lu.Exact(F("id"), Value(5) % Value(4)))),
        ("id eq 2 add -1", Q(lu.Exact(F("id"), Value(2) + Value(-1)))),
        (
            "id eq id sub 1",
            Q(lu.Exact(F("id"), F("id") - Value(1))),
        ),
        (
            "title eq 'donut' add 'tello'",
            Q(lu.Exact(F("title"), Value("donut") + Value("tello"))),
        ),
        (
            "title eq content add content",
            Q(lu.Exact(F("title"), F("content") + F("content"))),
        ),
        (
            "published_at eq 2019-01-01T00:00:00 add duration'P1DT1H1M1S'",
            Q(
                lu.Exact(
                    F("published_at"),
                    Value(dt.datetime(2019, 1, 1, 0, 0, 0))
                    + Value(dt.timedelta(days=1, hours=1, minutes=1, seconds=1)),
                )
            ),
        ),
        (
            "published_at eq 2019-01-01T00:00:00 add duration'P1Y'",
            Q(
                lu.Exact(
                    F("published_at"),
                    Value(dt.datetime(2019, 1, 1, 0, 0, 0))
                    + Value(dt.timedelta(days=365.25)),
                )
            ),
        ),
        (
            "published_at eq 2019-01-01T00:00:00 add duration'P2M'",
            Q(
                lu.Exact(
                    F("published_at"),
                    Value(dt.datetime(2019, 1, 1, 0, 0, 0))
                    + Value(dt.timedelta(days=60.88)),
                )
            ),
        ),
        ("contains(title, 'copy')", Q(lu.Contains(F("title"), Value("copy")))),
        ("startswith(title, 'copy')", Q(lu.StartsWith(F("title"), Value("copy")))),
        ("endswith(title, 'bla')", Q(lu.EndsWith(F("title"), Value("bla")))),
        (
            "id eq length(title)",
            Q(lu.Exact(F("id"), fn.Length(F("title")))),
        ),
        ("length(title) eq 10", Q(lu.Exact(fn.Length(F("title")), Value(10)))),
        ("10 eq length(title)", Q(lu.Exact(Value(10), fn.Length(F("title"))))),
        (
            "length(title) eq length('flippot')",
            Q(lu.Exact(fn.Length(F("title")), fn.Length(Value("flippot")))),
        ),
        (
            "title eq concat('a', 'b')",
            Q(lu.Exact(F("title"), fn.Concat(Value("a"), Value("b")))),
        ),
        (
            "title eq concat('test', id)",
            Q(lu.Exact(F("title"), fn.Concat(Value("test"), F("id")))),
        ),
        (
            "title eq concat(concat('a', 'b'), 'c')",
            Q(
                lu.Exact(
                    F("title"), fn.Concat(fn.Concat(Value("a"), Value("b")), Value("c"))
                )
            ),
        ),
        (
            "concat(title, 'a') eq 'testa'",
            Q(lu.Exact(fn.Concat(F("title"), Value("a")), Value("testa"))),
        ),
        (
            "indexof(title, 'Copy') eq 6",
            Q(lu.Exact(fn.StrIndex(F("title"), Value("Copy")) - Value(1), Value(6))),
        ),
        (
            "substring(title, 0) eq 'Copy'",
            Q(lu.Exact(fn.Substr(F("title"), Value(0) + Value(1)), Value("Copy"))),
        ),
        (
            "substring(title, 0, 4) eq 'Copy'",
            Q(
                lu.Exact(
                    fn.Substr(F("title"), Value(0) + Value(1), Value(4)), Value("Copy")
                )
            ),
        ),
        ("matchesPattern(title, 'C.py')", Q(lu.Regex(F("title"), Value("C.py")))),
        ("tolower(title) eq 'copy'", Q(lu.Exact(fn.Lower(F("title")), Value("copy")))),
        ("toupper(title) eq 'COPY'", Q(lu.Exact(fn.Upper(F("title")), Value("COPY")))),
        ("trim(title) eq 'copy'", Q(lu.Exact(fn.Trim(F("title")), Value("copy")))),
        (
            "date(published_at) eq 2019-01-01",
            Q(lu.Exact(fn.TruncDate(F("published_at")), Value(dt.date(2019, 1, 1)))),
        ),
        (
            "day(published_at) eq 1",
            Q(lu.Exact(fn.ExtractDay(F("published_at")), Value(1))),
        ),
        (
            "hour(published_at) eq 1",
            Q(lu.Exact(fn.ExtractHour(F("published_at")), Value(1))),
        ),
        (
            "minute(published_at) eq 1",
            Q(lu.Exact(fn.ExtractMinute(F("published_at")), Value(1))),
        ),
        (
            "month(published_at) eq 1",
            Q(lu.Exact(fn.ExtractMonth(F("published_at")), Value(1))),
        ),
        ("published_at eq now()", Q(lu.Exact(F("published_at"), fn.Now()))),
        (
            "second(published_at) eq 1",
            Q(lu.Exact(fn.ExtractSecond(F("published_at")), Value(1))),
        ),
        (
            "time(published_at) eq 14:00:00",
            Q(lu.Exact(fn.TruncTime(F("published_at")), Value(dt.time(14, 0, 0)))),
        ),
        (
            "year(published_at) eq 2019",
            Q(lu.Exact(fn.ExtractYear(F("published_at")), Value(2019))),
        ),
        ("ceiling(id) eq 1", Q(lu.Exact(fn.Ceil(F("id")), Value(1)))),
        ("floor(id) eq 1", Q(lu.Exact(fn.Floor(F("id")), Value(1)))),
        ("round(id) eq 1", Q(lu.Exact(fn.Round(F("id")), Value(1)))),
        (
            "date(published_at) eq 2019-01-01 add duration'P1D'",
            Q(
                lu.Exact(
                    fn.TruncDate(F("published_at")),
                    Value(dt.date(2019, 1, 1)) + Value(dt.timedelta(days=1)),
                )
            ),
        ),
        (
            "date(published_at) eq 2019-01-01 add duration'-P1D'",
            Q(
                lu.Exact(
                    fn.TruncDate(F("published_at")),
                    Value(dt.date(2019, 1, 1)) + Value(-1 * dt.timedelta(days=1)),
                )
            ),
        ),
        ("authors/name eq 'Ruben'", Q(lu.Exact(F("authors__name"), Value("Ruben")))),
        (
            "authors/comments/content eq 'Cool!'",
            Q(lu.Exact(F("authors__comments__content"), Value("Cool!"))),
        ),
        (
            "contains(comments/content, 'Cool')",
            Q(lu.Contains(F("comments__content"), Value("Cool"))),
        ),
        (
            "contains(concat(workflow_version/title, 'TEST'), 'BENCHMARK TEST') "
            "and startswith(created_by/title, 'Ruben') "
            "and 3 eq created_by/id",
            Q(
                lu.Contains(
                    fn.Concat(F("workflow_version__title"), Value("TEST")),
                    Value("BENCHMARK TEST"),
                )
            )
            & Q(lu.StartsWith(F("created_by__title"), Value("Ruben")))
            & Q(lu.Exact(Value(3), F("created_by__id"))),
        ),
        # GITHUB-19
        (
            "contains(title, 'TEST') eq true",
            Q(lu.Exact(lu.Contains(F("title"), Value("TEST")), Value(True))),
        ),
        (
            "contains(title, 'TEST') eq false",
            Q(lu.Exact(lu.Contains(F("title"), Value("TEST")), Value(False))),
        ),
        # GITHUB-47
        (
            "contains(tolower(name), tolower('A'))",
            Q(lu.Contains(fn.Lower(F("name")), fn.Lower(Value("A")))),
        ),
    ],
)
def test_odata_filter_to_django_q(odata_query: str, expected_q: str, lexer, parser):
    ast = parser.parse(lexer.tokenize(odata_query))
    transformer = AstToDjangoQVisitor(BlogPost)
    res_q = transformer.visit(ast)

    assert res_q == expected_q


@pytest.mark.parametrize(
    "odata_query, expected_exception",
    [
        ("published_at lt 2019-02-31", exceptions.ValueException),
        ("published_at lt 2019-02-31T00:00:00", exceptions.ValueException),
    ],
)
def test_exceptions(odata_query: str, expected_exception: type, parser, lexer):
    with pytest.raises(expected_exception):
        ast = parser.parse(lexer.tokenize(odata_query))
        transformer = AstToDjangoQVisitor(BlogPost)
        transformer.visit(ast)
