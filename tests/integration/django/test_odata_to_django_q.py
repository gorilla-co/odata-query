import datetime as dt
import uuid

import pytest
from django.db.models import Exists, F, Q, Value, functions

from odata_query import exceptions
from odata_query.django import AstToDjangoQVisitor, SubQueryToken


def tz(offset: int) -> dt.tzinfo:
    return dt.timezone(dt.timedelta(hours=offset))


@pytest.mark.parametrize(
    "odata_query, expected_q",
    [
        (
            "id eq a7af27e6-f5a0-11e9-9649-0a252986adba",
            Q(id__exact=uuid.UUID("a7af27e6-f5a0-11e9-9649-0a252986adba")),
        ),
        (
            "id in (a7af27e6-f5a0-11e9-9649-0a252986adba, 800c56e4-354d-11eb-be38-3af9d323e83c)",
            Q(
                id__in=[
                    uuid.UUID("a7af27e6-f5a0-11e9-9649-0a252986adba"),
                    uuid.UUID("800c56e4-354d-11eb-be38-3af9d323e83c"),
                ]
            ),
        ),
        ("id eq 4", Q(id__exact=Value(4))),
        ("id ne 4", Q(id__ne=Value(4))),
        ("4 eq id", Q(id__exact=Value(4))),
        ("4 ne id", Q(id__ne=Value(4))),
        ("published_at gt 2018-01-01", Q(published_at__gt=Value(dt.date(2018, 1, 1)))),
        ("published_at ge 2018-01-01", Q(published_at__gte=Value(dt.date(2018, 1, 1)))),
        ("published_at lt 2018-01-01", Q(published_at__lt=Value(dt.date(2018, 1, 1)))),
        ("published_at le 2018-01-01", Q(published_at__lte=Value(dt.date(2018, 1, 1)))),
        ("2018-01-01 gt published_at", Q(published_at__lt=Value(dt.date(2018, 1, 1)))),
        ("2018-01-01 ge published_at", Q(published_at__lte=Value(dt.date(2018, 1, 1)))),
        (
            "published_at gt 2018-01-01T01:02",
            Q(published_at__gt=Value(dt.datetime(2018, 1, 1, 1, 2))),
        ),
        (
            "published_at gt 2018-01-01T01:02:03",
            Q(published_at__gt=Value(dt.datetime(2018, 1, 1, 1, 2, 3))),
        ),
        (
            "published_at gt 2018-01-01T01:02:03.123",
            Q(published_at__gt=Value(dt.datetime(2018, 1, 1, 1, 2, 3, 123_000))),
        ),
        (
            "published_at gt 2018-01-01T01:02:03.123456",
            Q(published_at__gt=Value(dt.datetime(2018, 1, 1, 1, 2, 3, 123_456))),
        ),
        (
            "published_at gt 2018-01-01T01:02Z",
            Q(published_at__gt=Value(dt.datetime(2018, 1, 1, 1, 2, tzinfo=tz(0)))),
        ),
        (
            "published_at gt 2018-01-01T01:02:03Z",
            Q(published_at__gt=Value(dt.datetime(2018, 1, 1, 1, 2, 3, tzinfo=tz(0)))),
        ),
        (
            "published_at gt 2018-01-01T01:02:03.123Z",
            Q(
                published_at__gt=Value(
                    dt.datetime(2018, 1, 1, 1, 2, 3, 123_000, tzinfo=tz(0))
                )
            ),
        ),
        (
            "published_at gt 2018-01-01T01:02+02:00",
            Q(published_at__gt=Value(dt.datetime(2018, 1, 1, 1, 2, tzinfo=tz(+2)))),
        ),
        (
            "published_at gt 2018-01-01T01:02-02:00",
            Q(published_at__gt=Value(dt.datetime(2018, 1, 1, 1, 2, tzinfo=tz(-2)))),
        ),
        (
            "id in (1, 2, 3)",
            Q(id__in=[Value(1), Value(2), Value(3)]),
        ),
        ("id eq null", Q(id__isnull=Value(True))),
        ("id ne null", Q(id__isnull=Value(False))),
        ("not (id eq 1)", ~Q(id__exact=Value(1))),
        (
            "id eq 1 or id eq 2",
            Q(id__exact=Value(1)) | Q(id__exact=Value(2)),
        ),
        (
            "id eq 1 and content eq 'executing'",
            Q(id__exact=Value(1)) & Q(content__exact=Value("executing")),
        ),
        (
            "id eq 1 and (content eq 'executing' or content eq 'failed')",
            Q(id__exact=Value(1))
            & (
                Q(content__exact=Value("executing")) | Q(content__exact=Value("failed"))
            ),
        ),
        ("id eq 1 add 1", Q(id__exact=Value(1) + Value(1))),
        ("id eq 2 sub 1", Q(id__exact=Value(2) - Value(1))),
        ("id eq 2 mul 2", Q(id__exact=Value(2) * Value(2))),
        ("id eq 2 div 2", Q(id__exact=Value(2) / Value(2))),
        ("id eq 5 mod 4", Q(id__exact=Value(5) % Value(4))),
        ("id eq 2 add -1", Q(id__exact=Value(2) + Value(-1))),
        (
            "id eq id sub 1",
            Q(id__exact=F("id") - Value(1)),
        ),
        (
            "title eq 'donut' add 'tello'",
            Q(title__exact=Value("donut") + Value("tello")),
        ),
        ("title eq content add content", Q(title__exact=F("content") + F("content"))),
        (
            "published_at eq 2019-01-01T00:00:00 add duration'P1DT1H1M1S'",
            Q(
                published_at__exact=Value(dt.datetime(2019, 1, 1, 0, 0, 0))
                + Value(dt.timedelta(days=1, hours=1, minutes=1, seconds=1))
            ),
        ),
        ("contains(title, 'copy')", Q(title__contains=Value("copy"))),
        ("startswith(title, 'copy')", Q(title__startswith=Value("copy"))),
        ("endswith(title, 'bla')", Q(title__endswith=Value("bla"))),
        (
            "id eq length(title)",
            Q(id__exact=functions.Length(F("title"))),
        ),
        ("length(title) eq 10", Q(title__length__exact=Value(10))),
        ("10 eq length(title)", Q(title__length__exact=Value(10))),
        (
            "length(title) eq length('flippot')",
            Q(title__length__exact=functions.Length(Value("flippot"))),
        ),
        (
            "title eq concat('a', 'b')",
            Q(title__exact=functions.Concat(Value("a"), Value("b"))),
        ),
        (
            "title eq concat('test', id)",
            Q(title__exact=functions.Concat(Value("test"), F("id"))),
        ),
        (
            "title eq concat(concat('a', 'b'), 'c')",
            Q(
                title__exact=functions.Concat(
                    functions.Concat(Value("a"), Value("b")), Value("c")
                )
            ),
        ),
        (
            "concat(title, 'a') eq 'testa'",
            Q(concat_concatpair_title_a__exact=Value("testa")),
        ),
        (
            "indexof(title, 'Copy') eq 6",
            Q(combinedexpression_strindex_title_copy_1__exact=Value(6)),
        ),
        (
            "substring(title, 0) eq 'Copy'",
            Q(substr_title_combinedexpression_0_1__exact=Value("Copy")),
        ),
        (
            "substring(title, 0, 4) eq 'Copy'",
            Q(substr_title_combinedexpression_0_1_4__exact=Value("Copy")),
        ),
        ("matchesPattern(title, 'C.py')", Q(title__regex=Value("C.py"))),
        ("tolower(title) eq 'copy'", Q(title__lower__exact=Value("copy"))),
        ("toupper(title) eq 'COPY'", Q(title__upper__exact=Value("COPY"))),
        ("trim(title) eq 'copy'", Q(title__trim__exact=Value("copy"))),
        (
            "date(published_at) eq 2019-01-01",
            Q(published_at__date__exact=Value(dt.date(2019, 1, 1))),
        ),
        ("day(published_at) eq 1", Q(published_at__day__exact=Value(1))),
        ("hour(published_at) eq 1", Q(published_at__hour__exact=Value(1))),
        ("minute(published_at) eq 1", Q(published_at__minute__exact=Value(1))),
        ("month(published_at) eq 1", Q(published_at__month__exact=Value(1))),
        ("published_at eq now()", Q(published_at__exact=functions.Now())),
        ("second(published_at) eq 1", Q(published_at__second__exact=Value(1))),
        (
            "time(published_at) eq 14:00:00",
            Q(published_at__time__exact=Value(dt.time(14, 0, 0))),
        ),
        ("year(published_at) eq 2019", Q(published_at__year__exact=Value(2019))),
        ("ceiling(id) eq 1", Q(id__ceil__exact=Value(1))),
        ("floor(id) eq 1", Q(id__floor__exact=Value(1))),
        ("round(id) eq 1", Q(id__round__exact=Value(1))),
        (
            "date(published_at) eq 2019-01-01 add duration'P1D'",
            Q(
                published_at__date__exact=Value(dt.date(2019, 1, 1))
                + Value(dt.timedelta(days=1))
            ),
        ),
        (
            "date(published_at) eq 2019-01-01 add duration'-P1D'",
            Q(
                published_at__date__exact=Value(dt.date(2019, 1, 1))
                + Value(-1 * dt.timedelta(days=1))
            ),
        ),
        ("authors/name eq 'Ruben'", Q(authors__name__exact=Value("Ruben"))),
        (
            "authors/comments/content eq 'Cool!'",
            Q(authors__comments__content__exact=Value("Cool!")),
        ),
        (
            "contains(comments/content, 'Cool')",
            Q(comments__content__contains=Value("Cool")),
        ),
        (
            "contains(concat(workflow_version/title, 'TEST'), 'BENCHMARK TEST') "
            "and startswith(created_by/title, 'Ruben') "
            "and 3 eq created_by/id",
            Q(
                concat_concatpair_workflow_version__title_test__contains=Value(
                    "BENCHMARK TEST"
                )
            )
            & Q(created_by__title__startswith=Value("Ruben"))
            & Q(created_by__id__exact=Value(3)),
        ),
        (
            "fields/any(f: f/title eq 'test')",
            Q(SubQueryToken("fields", Q(title__exact=Value("test")), Exists)),
        ),
        (
            "fields/any(f: f/title eq 'test' and f/value eq 'foo')",
            Q(
                SubQueryToken(
                    "fields",
                    Q(title__exact=Value("test")) & Q(value__exact=Value("foo")),
                    Exists,
                )
            ),
        ),
        (
            "fields/all(f: f/title eq 'test')",
            Q(
                SubQueryToken(
                    "fields",
                    ~Q(title__exact=Value("test")),
                    Exists,
                    dict(negated=True),
                )
            ),
        ),
        (
            "model/fields/any(f: f/title eq 'test')",
            Q(SubQueryToken("model__fields", Q(title__exact=Value("test")), Exists)),
        ),
    ],
)
def test_odata_filter_to_django_q(odata_query: str, expected_q: str, lexer, parser):
    ast = parser.parse(lexer.tokenize(odata_query))
    transformer = AstToDjangoQVisitor()
    res_q = transformer.visit(ast)

    assert res_q == expected_q


@pytest.mark.parametrize(
    "odata_query, expected_q, field_mapping",
    [
        (
            "data_type/modules eq 'pricing_power'",
            Q(
                data_type_version__versioned_model__modules__code__exact=Value(
                    "pricing_power"
                )
            ),
            {"data_type__modules": "data_type_version__versioned_model__modules__code"},
        ),
        (
            "data_type/modules in ('pricing_power',)",
            Q(
                data_type_version__versioned_model__modules__code__in=[
                    Value("pricing_power")
                ]
            ),
            {"data_type__modules": "data_type_version__versioned_model__modules__code"},
        ),
        (
            "data_type/id eq a7af27e6-f5a0-11e9-9649-0a252986adba",
            Q(
                data_type_version__id__exact=uuid.UUID(
                    "a7af27e6-f5a0-11e9-9649-0a252986adba"
                )
            ),
            {"data_type__id": "data_type_version__id"},
        ),
        (
            "modules eq 'pricing_power'",
            Q(versioned_model__modules__code__exact=Value("pricing_power")),
            {"modules": "versioned_model__modules__code"},
        ),
        (
            "modules eq 'pricing_power'",
            Q(modules__code__exact=Value("pricing_power")),
            {"modules": "modules__code"},
        ),
        (
            "modules in ('pricing_power',)",
            Q(modules__code__in=[Value("pricing_power")]),
            {"modules": "modules__code"},
        ),
        (
            "contains(tolower(title), 'factors')",
            Q(versioned_model__title__lower__contains=Value("factors")),
            {"title": "versioned_model__title"},
        ),
    ],
)
def test_odata_filter_to_django_q_with_field_mapping(
    odata_query: str, expected_q: str, field_mapping: dict, lexer, parser
):
    ast = parser.parse(lexer.tokenize(odata_query))
    transformer = AstToDjangoQVisitor(field_mapping)
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
        transformer = AstToDjangoQVisitor(None)
        transformer.visit(ast)
