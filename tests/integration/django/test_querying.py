import datetime as dt
from typing import Type

import pytest
from django.db import models, transaction

from odata_query.django import apply_odata_query

from .models import Author, BlogPost, Comment


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
