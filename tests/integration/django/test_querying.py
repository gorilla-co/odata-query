import datetime as dt
from typing import Type

import pytest
from django.db import models, transaction

from odata_query.django import AstToDjangoQVisitor

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
    ],
)
def test_query_with_odata(
    model: Type[models.Model],
    query: str,
    exp_results: int,
    lexer,
    parser,
    sample_data_sess,
):
    ast = parser.parse(lexer.tokenize(query))
    transformer = AstToDjangoQVisitor()
    where_clause = transformer.visit(ast)

    results = model.objects.filter(where_clause).all()
    assert len(results) == exp_results
