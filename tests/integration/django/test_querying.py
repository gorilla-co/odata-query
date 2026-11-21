import datetime as dt
from typing import Type

import pytest
from django.db import models, transaction

from odata_query.django import apply_odata_query
from odata_query.django.django_q import AstToDjangoQVisitor
from odata_query.exceptions import (
    InvalidOrderByException,
    InvalidQueryOptionException,
    ParsingException,
)
from odata_query.grammar import parse_orderby

from .models import Author, BlogPost, Comment, Ticket


@pytest.fixture
def sample_data_sess(django_db):
    # https://docs.djangoproject.com/en/3.1/topics/db/transactions/#managing-autocommit
    transaction.set_autocommit(False)
    a1 = Author(name="Gorilla")
    a1.save()
    a2 = Author(name="Baboon")
    a2.save()
    a3 = Author(name="Saki")
    a3.save()

    bp1 = BlogPost(
        title="Querying Data",
        published_at=dt.datetime(2020, 1, 1),
        content="How 2 query data...",
    )
    bp1.save()
    bp2 = BlogPost(
        title="Automating Monkey Jobs",
        published_at=dt.datetime(2019, 1, 1),
        content="How 2 automate monkey jobs...",
    )
    bp2.save()
    bp1.authors.set([a1])
    bp2.authors.set([a2, a3])

    c1 = Comment(content="Dope!", author=a2, blogpost=bp1)
    c1.save()
    c2 = Comment(content="Cool!", author=a1, blogpost=bp2)
    c2.save()
    yield
    transaction.rollback()


@pytest.mark.parametrize(
    "model, query, exp_results",
    [
        (Author, "name eq 'Baboon'", 1),
        (Author, "startswith(name, 'Gori')", 1),
        (BlogPost, "contains(content, 'How')", 2),
        (BlogPost, "published_at gt 2019-06-01", 1),
        (Author, "contains(blogposts/title, 'Monkey')", 2),
        (Author, "startswith(blogposts/comments/content, 'Cool')", 2),
        (Author, "comments/any()", 2),
        (BlogPost, "authors/any(a: contains(a/name, 'o'))", 2),
        (BlogPost, "authors/all(a: contains(a/name, 'o'))", 1),
        (Author, "blogposts/comments/any(c: contains(c/content, 'Cool'))", 2),
        (Author, "id eq a7af27e6-f5a0-11e9-9649-0a252986adba", 0),
        (
            Author,
            "id in (a7af27e6-f5a0-11e9-9649-0a252986adba, 800c56e4-354d-11eb-be38-3af9d323e83c)",
            0,
        ),
        (BlogPost, "comments/author eq 0", 0),
        (BlogPost, "substring(content, 0) eq 'test'", 0),
        (BlogPost, "year(published_at) eq 2019", 1),
        # GITHUB-19
        (BlogPost, "contains(title, 'Query') eq true", 1),
        (BlogPost, "contains(title, 'Query') eq false", 1),
    ],
)
def test_query_with_odata(
    model: Type[models.Model],
    query: str,
    exp_results: int,
    sample_data_sess,
):
    q = apply_odata_query(model.objects, query)
    results = q.all()
    assert len(results) == exp_results


@pytest.mark.parametrize(
    "odata_query, expected_sql",
    [
        (
            "author eq null",
            (
                'SELECT DISTINCT "django_comment"."id", "django_comment"."content", "django_comment"."author_id", "django_comment"."blogpost_id" '
                'FROM "django_comment" '
                'WHERE "django_comment"."author_id" IS NULL'
            ),
        ),
        (
            "author ne null",
            (
                'SELECT DISTINCT "django_comment"."id", "django_comment"."content", "django_comment"."author_id", "django_comment"."blogpost_id" '
                'FROM "django_comment" '
                'WHERE "django_comment"."author_id" IS NOT NULL'
            ),
        ),
    ],
)
def test_odata_filter_to_sql_query(odata_query: str, expected_sql: str):
    q = apply_odata_query(Comment.objects, odata_query)
    queryset = q.distinct()
    sql = str(queryset.query)
    assert sql == expected_sql


def _author_names(odata_query: str, **options) -> list:
    """
    Authors ordered by name (Baboon, Gorilla, Saki), as a list of names.
    """
    q = apply_odata_query(Author.objects.order_by("name"), odata_query, **options)
    return [a.name for a in q]


@pytest.mark.parametrize(
    "odata_query, options, exp_names",
    [
        ("true eq true", {}, ["Baboon", "Gorilla", "Saki"]),
        ("true eq true", {"top": 2}, ["Baboon", "Gorilla"]),
        ("true eq true", {"skip": 1}, ["Gorilla", "Saki"]),
        # Distinguishes a plain offset from `skip * top`, and from swapped args:
        ("true eq true", {"top": 2, "skip": 1}, ["Gorilla", "Saki"]),
        ("true eq true", {"top": 1, "skip": 2}, ["Saki"]),
        # Boundaries:
        ("true eq true", {"top": 0}, []),
        ("true eq true", {"top": 0, "skip": 1}, []),
        ("true eq true", {"skip": 0}, ["Baboon", "Gorilla", "Saki"]),
        ("true eq true", {"top": 10}, ["Baboon", "Gorilla", "Saki"]),
        ("true eq true", {"skip": 3}, []),
        ("true eq true", {"top": 5, "skip": 10}, []),
        # Paging applies to the filtered results, including annotated ones:
        ("name ne 'Baboon'", {"top": 1, "skip": 1}, ["Saki"]),
        ("name eq 'Nobody'", {"top": 1, "skip": 1}, []),
        ("tolower(name) ne 'baboon'", {"top": 1, "skip": 1}, ["Saki"]),
        ("contains(blogposts/title, 'Monkey')", {"top": 1, "skip": 1}, ["Saki"]),
        # Ordering overrides the ordering of the base query, and happens before paging:
        ("true eq true", {"orderby": "name"}, ["Baboon", "Gorilla", "Saki"]),
        ("true eq true", {"orderby": "name asc"}, ["Baboon", "Gorilla", "Saki"]),
        ("true eq true", {"orderby": "name desc"}, ["Saki", "Gorilla", "Baboon"]),
        (
            "true eq true",
            {"orderby": "length(name), name"},
            ["Saki", "Baboon", "Gorilla"],
        ),
        (
            "true eq true",
            {"orderby": "length(name) desc"},
            ["Gorilla", "Baboon", "Saki"],
        ),
        (
            "true eq true",
            {"orderby": "tolower(name) DESC"},
            ["Saki", "Gorilla", "Baboon"],
        ),
        ("true eq true", {"orderby": "name desc", "top": 2}, ["Saki", "Gorilla"]),
        ("true eq true", {"orderby": "name desc", "skip": 1}, ["Gorilla", "Baboon"]),
        (
            "true eq true",
            {"orderby": "name desc", "top": 1, "skip": 1},
            ["Gorilla"],
        ),
        ("name ne 'Baboon'", {"orderby": "name desc"}, ["Saki", "Gorilla"]),
        (
            "name ne 'Baboon'",
            {"orderby": "name desc", "top": 1, "skip": 1},
            ["Gorilla"],
        ),
        ("name eq 'Nobody'", {"orderby": "name desc", "top": 1}, []),
        # Ordering and filtering over the same relationship, or ordering by an
        # expression that needs an annotation:
        (
            "contains(blogposts/title, 'Monkey')",
            {"orderby": "name desc"},
            ["Saki", "Baboon"],
        ),
        (
            "tolower(name) ne 'baboon'",
            {"orderby": "tolower(name) desc", "top": 1},
            ["Saki"],
        ),
    ],
)
def test_top_and_skip(sample_data_sess, odata_query, options, exp_names):
    assert _author_names(odata_query, **options) == exp_names


@pytest.mark.parametrize(
    "options, expected_exception",
    [
        ({"top": -1}, InvalidQueryOptionException),
        ({"skip": -1}, InvalidQueryOptionException),
        ({"top": "5"}, InvalidQueryOptionException),
        ({"orderby": ""}, ParsingException),
        ({"orderby": "name desc desc"}, ParsingException),
        ({"orderby": "name,"}, ParsingException),
    ],
)
def test_invalid_options_are_rejected(options, expected_exception):
    with pytest.raises(expected_exception):
        apply_odata_query(Author.objects, "true eq true", **options)


def test_top_and_skip_page_over_unique_rows_with_distinct(sample_data_sess):
    gorilla = Author.objects.get(name="Gorilla")
    blogpost = BlogPost.objects.create(
        title="Querying More", published_at=dt.datetime(2021, 1, 1), content="..."
    )
    blogpost.authors.set([gorilla])
    odata_query = "contains(blogposts/title, 'Querying')"

    unique = apply_odata_query(Author.objects.distinct(), odata_query, top=1)
    duplicated = apply_odata_query(Author.objects.all(), odata_query, top=2)

    assert [a.name for a in unique] == ["Gorilla"]
    assert [a.name for a in duplicated] == ["Gorilla", "Gorilla"]


@pytest.fixture
def tickets(sample_data_sess):
    """
    Tickets by number: 1 'Dope!' (Baboon), 2 'Cool!' (Gorilla),
    3 no title and no assignee, 4 'Cool!' (Saki).
    """
    by_name = {a.name: a for a in Author.objects.all()}
    Ticket.objects.create(number=1, title="Dope!", assignee=by_name["Baboon"])
    Ticket.objects.create(number=2, title="Cool!", assignee=by_name["Gorilla"])
    Ticket.objects.create(number=3, title=None, assignee=None)
    Ticket.objects.create(number=4, title="Cool!", assignee=by_name["Saki"])


def _ticket_numbers(odata_query="true eq true", base=None, **options):
    base = Ticket.objects.all() if base is None else base
    return [t.number for t in apply_odata_query(base, odata_query, **options)]


@pytest.mark.parametrize(
    "orderby, exp_numbers",
    [
        # NULL sorts first when ascending, last when descending. The two
        # 'Cool!' tickets tie, which the default ordering of Ticket decides:
        ("title", [3, 4, 2, 1]),
        ("title asc", [3, 4, 2, 1]),
        ("title desc", [1, 4, 2, 3]),
        # Ties are broken by the next item:
        ("title, number desc", [3, 4, 2, 1]),
        ("title desc, number desc", [1, 4, 2, 3]),
        ("number desc", [4, 3, 2, 1]),
        # Expressions can contain NULL too:
        ("length(title), number", [3, 1, 2, 4]),
        ("tolower(title) desc, number desc", [1, 4, 2, 3]),
        ("title eq 'Cool!' desc, number", [2, 4, 1, 3]),
        ("title eq 'Cool!', number desc", [3, 1, 4, 2]),
        ("number mod 2 desc, number", [1, 3, 2, 4]),
        # Boolean expressions, NULL sorts before false and false before true:
        ("title eq 'Cool!' and number gt 2 desc, number", [4, 1, 2, 3]),
        ("title eq 'Cool!' and number gt 2, number", [3, 1, 2, 4]),
        ("title eq 'Cool!' or number eq 3 desc, number", [2, 3, 4, 1]),
        ("title eq 'Cool!' or number eq 3, number desc", [1, 4, 3, 2]),
        # A related entity that is missing sorts as NULL, and keeps the row:
        ("assignee/name", [3, 1, 2, 4]),
        ("assignee/name desc", [4, 2, 1, 3]),
        ("tolower(assignee/name) desc", [4, 2, 1, 3]),
        ("title, assignee/name desc", [3, 4, 2, 1]),
        ("assignee/name, assignee/name desc, number", [3, 1, 2, 4]),
    ],
)
def test_orderby(tickets, orderby, exp_numbers):
    assert _ticket_numbers(orderby=orderby) == exp_numbers


def test_orderby_comes_before_ordering_that_is_already_on_the_queryset(tickets):
    numbers = _ticket_numbers(base=Ticket.objects.order_by("number"), orderby="title")

    # The two 'Cool!' tickets tie on title, so the base ordering decides:
    assert numbers == [3, 2, 4, 1]


def test_orderby_comes_before_the_default_ordering_of_the_model(tickets):
    # Ticket is ordered by `-number` by default.
    assert _ticket_numbers(orderby="title") == [3, 4, 2, 1]


def test_orderby_replaces_nothing_when_the_queryset_is_explicitly_unordered(tickets):
    numbers = _ticket_numbers(base=Ticket.objects.order_by(), orderby="title desc, id")

    assert numbers == [1, 2, 4, 3]


@pytest.mark.parametrize("orderby", ["author_id", "author_id desc"])
def test_orderby_on_a_foreign_key_column_is_ordering_by_a_value(
    orderby, sample_data_sess
):
    queryset = apply_odata_query(Comment.objects, "true eq true", orderby=orderby)

    assert len(list(queryset)) == 2
    direction = "ASC" if orderby == "author_id" else "DESC"
    assert f'"author_id" {direction}' in str(queryset.query)


def test_orderby_with_filter_top_and_skip(tickets):
    numbers = _ticket_numbers(
        "number gt 1", orderby="title desc, number", top=2, skip=1
    )

    assert numbers == [4, 3]


def test_orderby_with_filter_on_the_same_relationship(tickets):
    numbers = _ticket_numbers("assignee/name ne 'Baboon'", orderby="assignee/name")

    # The filter drops the ticket without assignee:
    assert numbers == [2, 4]


@pytest.mark.parametrize(
    "model, orderby",
    [
        # A collection would repeat the root rows:
        (Author, "blogposts/title"),
        (Author, "blogposts/title desc"),
        (Author, "name, comments/content"),
        (Author, "tickets/title"),
        (Author, "length(blogposts/title)"),
        (Author, "blogposts/title eq 'a'"),
        (Comment, "author/blogposts/title"),
        (BlogPost, "authors/name"),
        # Entities are not values:
        (Author, "blogposts"),
        (Comment, "author"),
        (Comment, "author desc"),
        (Comment, "blogpost, id"),
        (Ticket, "assignee"),
    ],
)
def test_orderby_on_collections_and_entities_is_rejected(model, orderby):
    with pytest.raises(InvalidOrderByException):
        apply_odata_query(model.objects, "true eq true", orderby=orderby)


def test_orderby_on_collection_names_the_collection():
    with pytest.raises(InvalidOrderByException) as exc_info:
        apply_odata_query(Author.objects, "true eq true", orderby="blogposts/title")

    assert exc_info.value.field_name == "blogposts"


@pytest.mark.parametrize(
    "orderby, exp_nulls_first, exp_nulls_last",
    [
        # Explicit NULL ordering where NULL is possible:
        ("title", True, None),
        ("title desc", None, True),
        ("assignee/name", True, None),
        ("assignee/name desc", None, True),
        ("title eq 'a'", True, None),
        ("length(title) desc", None, True),
        ("number add 1", True, None),
        # ... but not for a column that is not nullable, as it can cost the use
        # of an index:
        ("number", None, None),
        ("number desc", None, None),
    ],
)
def test_orderby_asks_for_null_ordering_only_where_null_is_possible(
    orderby, exp_nulls_first, exp_nulls_last
):
    (order_by,) = AstToDjangoQVisitor(Ticket).visit(parse_orderby(orderby))

    assert order_by.nulls_first is exp_nulls_first
    assert order_by.nulls_last is exp_nulls_last
