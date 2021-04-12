import datetime as dt

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
            Q(id__exact=Value("a7af27e6-f5a0-11e9-9649-0a252986adba")),
        ),
        ("version_id eq 4", Q(version_id__exact=Value(4))),
        ("version_id ne 4", Q(version_id__ne=Value(4))),
        ("4 eq version_id", Q(version_id__exact=Value(4))),
        ("4 ne version_id", Q(version_id__ne=Value(4))),
        ("created_at gt 2018-01-01", Q(created_at__gt=Value(dt.date(2018, 1, 1)))),
        ("created_at ge 2018-01-01", Q(created_at__gte=Value(dt.date(2018, 1, 1)))),
        ("created_at lt 2018-01-01", Q(created_at__lt=Value(dt.date(2018, 1, 1)))),
        ("created_at le 2018-01-01", Q(created_at__lte=Value(dt.date(2018, 1, 1)))),
        ("2018-01-01 gt created_at", Q(created_at__lt=Value(dt.date(2018, 1, 1)))),
        ("2018-01-01 ge created_at", Q(created_at__lte=Value(dt.date(2018, 1, 1)))),
        (
            "created_at gt 2018-01-01T01:02",
            Q(created_at__gt=Value(dt.datetime(2018, 1, 1, 1, 2))),
        ),
        (
            "created_at gt 2018-01-01T01:02:03",
            Q(created_at__gt=Value(dt.datetime(2018, 1, 1, 1, 2, 3))),
        ),
        (
            "created_at gt 2018-01-01T01:02:03.123",
            Q(created_at__gt=Value(dt.datetime(2018, 1, 1, 1, 2, 3, 123_000))),
        ),
        (
            "created_at gt 2018-01-01T01:02:03.123456",
            Q(created_at__gt=Value(dt.datetime(2018, 1, 1, 1, 2, 3, 123_456))),
        ),
        (
            "created_at gt 2018-01-01T01:02Z",
            Q(created_at__gt=Value(dt.datetime(2018, 1, 1, 1, 2, tzinfo=tz(0)))),
        ),
        (
            "created_at gt 2018-01-01T01:02:03Z",
            Q(created_at__gt=Value(dt.datetime(2018, 1, 1, 1, 2, 3, tzinfo=tz(0)))),
        ),
        (
            "created_at gt 2018-01-01T01:02:03.123Z",
            Q(
                created_at__gt=Value(
                    dt.datetime(2018, 1, 1, 1, 2, 3, 123_000, tzinfo=tz(0))
                )
            ),
        ),
        (
            "created_at gt 2018-01-01T01:02+02:00",
            Q(created_at__gt=Value(dt.datetime(2018, 1, 1, 1, 2, tzinfo=tz(+2)))),
        ),
        (
            "created_at gt 2018-01-01T01:02-02:00",
            Q(created_at__gt=Value(dt.datetime(2018, 1, 1, 1, 2, tzinfo=tz(-2)))),
        ),
        (
            "version_id in (1, 2, 3)",
            Q(version_id__in=[Value(1), Value(2), Value(3)]),
        ),
        ("version_id eq null", Q(version_id__isnull=Value(True))),
        ("version_id ne null", Q(version_id__isnull=Value(False))),
        ("not (version_id eq 1)", ~Q(version_id__exact=Value(1))),
        (
            "version_id eq 1 or version_id eq 2",
            Q(version_id__exact=Value(1)) | Q(version_id__exact=Value(2)),
        ),
        (
            "version_id eq 1 and status eq 'executing'",
            Q(version_id__exact=Value(1)) & Q(status__exact=Value("executing")),
        ),
        (
            "version_id eq 1 and (status eq 'executing' or status eq 'failed')",
            Q(version_id__exact=Value(1))
            & (Q(status__exact=Value("executing")) | Q(status__exact=Value("failed"))),
        ),
        ("version_id eq 1 add 1", Q(version_id__exact=Value(1) + Value(1))),
        ("version_id eq 2 sub 1", Q(version_id__exact=Value(2) - Value(1))),
        ("version_id eq 2 mul 2", Q(version_id__exact=Value(2) * Value(2))),
        ("version_id eq 2 div 2", Q(version_id__exact=Value(2) / Value(2))),
        ("version_id eq 5 mod 4", Q(version_id__exact=Value(5) % Value(4))),
        ("version_id eq 2 add -1", Q(version_id__exact=Value(2) + Value(-1))),
        (
            "version_id eq n_versions sub 1",
            Q(version_id__exact=F("n_versions") - Value(1)),
        ),
        (
            "name eq 'donut' add 'tello'",
            Q(name__exact=Value("donut") + Value("tello")),
        ),
        ("name eq donut add tello", Q(name__exact=F("donut") + F("tello"))),
        (
            "created_at eq 2019-01-01T00:00:00 add duration'P1DT1H1M1S'",
            Q(
                created_at__exact=Value(dt.datetime(2019, 1, 1, 0, 0, 0))
                + Value(dt.timedelta(days=1, hours=1, minutes=1, seconds=1))
            ),
        ),
        ("contains(name, 'copy')", Q(name__contains=Value("copy"))),
        ("startswith(name, 'copy')", Q(name__startswith=Value("copy"))),
        ("endswith(name, 'bla')", Q(name__endswith=Value("bla"))),
        (
            "version_id eq length(name)",
            Q(version_id__exact=functions.Length(F("name"))),
        ),
        ("length(name) eq 10", Q(name__length__exact=Value(10))),
        ("10 eq length(name)", Q(name__length__exact=Value(10))),
        (
            "length(name) eq length('flippot')",
            Q(name__length__exact=functions.Length(Value("flippot"))),
        ),
        (
            "name eq concat('a', 'b')",
            Q(name__exact=functions.Concat(Value("a"), Value("b"))),
        ),
        (
            "name eq concat('test', version_id)",
            Q(name__exact=functions.Concat(Value("test"), F("version_id"))),
        ),
        (
            "name eq concat(concat('a', 'b'), 'c')",
            Q(
                name__exact=functions.Concat(
                    functions.Concat(Value("a"), Value("b")), Value("c")
                )
            ),
        ),
        (
            "concat(name, 'a') eq 'testa'",
            Q(concat_concatpair_name_a__exact=Value("testa")),
        ),
        (
            "indexof(name, 'Copy') eq 6",
            Q(combinedexpression_strindex_name_copy_1__exact=Value(6)),
        ),
        (
            "substring(name, 0) eq 'Copy'",
            Q(substr_name_combinedexpression_0_1__exact=Value("Copy")),
        ),
        (
            "substring(name, 0, 4) eq 'Copy'",
            Q(substr_name_combinedexpression_0_1_4__exact=Value("Copy")),
        ),
        ("matchesPattern(name, 'C.py')", Q(name__regex=Value("C.py"))),
        ("tolower(name) eq 'copy'", Q(name__lower__exact=Value("copy"))),
        ("toupper(name) eq 'COPY'", Q(name__upper__exact=Value("COPY"))),
        ("trim(name) eq 'copy'", Q(name__trim__exact=Value("copy"))),
        (
            "date(created_at) eq 2019-01-01",
            Q(created_at__date__exact=Value(dt.date(2019, 1, 1))),
        ),
        ("day(created_at) eq 1", Q(created_at__day__exact=Value(1))),
        ("hour(created_at) eq 1", Q(created_at__hour__exact=Value(1))),
        ("minute(created_at) eq 1", Q(created_at__minute__exact=Value(1))),
        ("month(created_at) eq 1", Q(created_at__month__exact=Value(1))),
        ("created_at eq now()", Q(created_at__exact=functions.Now())),
        ("second(created_at) eq 1", Q(created_at__second__exact=Value(1))),
        (
            "time(created_at) eq 14:00:00",
            Q(created_at__time__exact=Value(dt.time(14, 0, 0))),
        ),
        ("year(created_at) eq 2019", Q(created_at__year__exact=Value(2019))),
        ("ceiling(result) eq 1", Q(result__ceil__exact=Value(1))),
        ("floor(result) eq 1", Q(result__floor__exact=Value(1))),
        ("round(result) eq 1", Q(result__round__exact=Value(1))),
        (
            "date(created_at) eq 2019-01-01 add duration'P1D'",
            Q(
                created_at__date__exact=Value(dt.date(2019, 1, 1))
                + Value(dt.timedelta(days=1))
            ),
        ),
        (
            "date(created_at) eq 2019-01-01 add duration'-P1D'",
            Q(
                created_at__date__exact=Value(dt.date(2019, 1, 1))
                + Value(-1 * dt.timedelta(days=1))
            ),
        ),
        ("created_by/name eq 'Ruben'", Q(created_by__name__exact=Value("Ruben"))),
        (
            "created_by/company/name eq 'Gorilla'",
            Q(created_by__company__name__exact=Value("Gorilla")),
        ),
        (
            "contains(workflow_version/name, 'BENCHMARK')",
            Q(workflow_version__name__contains=Value("BENCHMARK")),
        ),
        (
            "contains(concat(workflow_version/name, 'TEST'), 'BENCHMARK TEST') "
            "and startswith(created_by/name, 'Ruben') "
            "and 3 eq created_by/id",
            Q(
                concat_concatpair_workflow_version__name_test__contains=Value(
                    "BENCHMARK TEST"
                )
            )
            & Q(created_by__name__startswith=Value("Ruben"))
            & Q(created_by__id__exact=Value(3)),
        ),
        (
            "fields/any(f: f/name eq 'test')",
            Q(SubQueryToken("fields", Q(name__exact=Value("test")), Exists)),
        ),
        (
            "fields/any(f: f/name eq 'test' and f/value eq 'foo')",
            Q(
                SubQueryToken(
                    "fields",
                    Q(name__exact=Value("test")) & Q(value__exact=Value("foo")),
                    Exists,
                )
            ),
        ),
        (
            "fields/all(f: f/name eq 'test')",
            Q(
                SubQueryToken(
                    "fields",
                    ~Q(name__exact=Value("test")),
                    Exists,
                    dict(negated=True),
                )
            ),
        ),
        (
            "model/fields/any(f: f/name eq 'test')",
            Q(SubQueryToken("model__fields", Q(name__exact=Value("test")), Exists)),
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
                data_type_version__id__exact=Value(
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
            "contains(tolower(name), 'factors')",
            Q(versioned_model__name__lower__contains=Value("factors")),
            {"name": "versioned_model__name"},
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
        ("created_at lt 2019-02-31", exceptions.ValueException),
        ("created_at lt 2019-02-31T00:00:00", exceptions.ValueException),
    ],
)
def test_exceptions(odata_query: str, expected_exception: type, parser, lexer):
    with pytest.raises(expected_exception):
        ast = parser.parse(lexer.tokenize(odata_query))
        transformer = AstToDjangoQVisitor(None)
        transformer.visit(ast)
