import pytest

from odata_query.roundtrip import AstToODataVisitor


@pytest.mark.parametrize(
    "odata_query",
    [
        "id eq a7af27e6-f5a0-11e9-9649-0a252986adba",
        "my_app.id eq 1",
        "id in (a7af27e6-f5a0-11e9-9649-0a252986adba, 800c56e4-354d-11eb-be38-3af9d323e83c)",
        "id eq 4",
        "id ne 4",
        "4 eq id",
        "4 ne id",
        "published_at gt 2018-01-01",
        "published_at ge 2018-01-01",
        "published_at lt 2018-01-01",
        "published_at le 2018-01-01",
        "2018-01-01 gt published_at",
        "2018-01-01 ge published_at",
        "published_at gt 2018-01-01T01:02",
        "published_at gt 2018-01-01T01:02:03",
        "published_at gt 2018-01-01T01:02:03.123",
        "published_at gt 2018-01-01T01:02:03.123456",
        "published_at gt 2018-01-01T01:02Z",
        "published_at gt 2018-01-01T01:02:03Z",
        "published_at gt 2018-01-01T01:02:03.123Z",
        "published_at gt 2018-01-01T01:02+02:00",
        "published_at gt 2018-01-01T01:02-02:00",
        "id in (1, 2, 3)",
        "id eq null",
        "id ne null",
        "not (id eq 1)",
        "id eq 1 or id eq 2",
        "id eq 1 and content eq 'executing'",
        "id eq 1 and (content eq 'executing' or content eq 'failed')",
        "id eq 1 add 1",
        "id eq 2 sub 1",
        "id eq 2 mul 2",
        "id eq 2 div 2",
        "id eq 5 mod 4",
        "id eq 2 add -1",
        "id eq id sub 1",
        "title eq 'donut' add 'tello'",
        "title eq content add content",
        "published_at eq 2019-01-01T00:00:00 add duration'P1DT1H1M1S'",
        "contains(title, 'copy')",
        "startswith(title, 'copy')",
        "endswith(title, 'bla')",
        "id eq length(title)",
        "length(title) eq 10",
        "10 eq length(title)",
        "length(title) eq length('flippot')",
        "title eq concat('a', 'b')",
        "title eq concat('test', id)",
        "title eq concat(concat('a', 'b'), 'c')",
        "concat(title, 'a') eq 'testa'",
        "indexof(title, 'Copy') eq 6",
        "substring(title, 0) eq 'Copy'",
        "substring(title, 0, 4) eq 'Copy'",
        "matchesPattern(title, 'C.py')",
        "tolower(title) eq 'copy'",
        "toupper(title) eq 'COPY'",
        "trim(title) eq 'copy'",
        "date(published_at) eq 2019-01-01",
        "day(published_at) eq 1",
        "hour(published_at) eq 1",
        "minute(published_at) eq 1",
        "month(published_at) eq 1",
        "published_at eq now()",
        "second(published_at) eq 1",
        "time(published_at) eq 14:00:00",
        "year(published_at) eq 2019",
        "ceiling(id) eq 1",
        "floor(id) eq 1",
        "round(id) eq 1",
        "date(published_at) eq 2019-01-01 add duration'P1D'",
        "date(published_at) eq 2019-01-01 add duration'-P1D'",
        "authors/name eq 'Ruben'",
        "authors/comments/content eq 'Cool!'",
        "contains(comments/content, 'Cool')",
        "contains(title, 'TEST') eq true",
        # Precedence checks:
        "1 mul (2 add -3 sub 4) div 5",
    ],
)
def test_odata_filter_roundtrip(odata_query: str, lexer, parser):
    ast = parser.parse(lexer.tokenize(odata_query))
    transformer = AstToODataVisitor()
    res = transformer.visit(ast)

    assert res == odata_query
