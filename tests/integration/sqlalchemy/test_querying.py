import datetime as dt
from typing import Callable, Type

import pytest
from sqlalchemy import select

from odata_query.sqlalchemy import apply_odata_core, apply_odata_query

from .models import Author, Base, BlogPost, Comment


@pytest.fixture
def sample_data_sess(db_session):
    s = db_session()
    a1 = Author(name="Gorilla")
    a2 = Author(name="Baboon")
    a3 = Author(name="Saki")
    bp1 = BlogPost(
        title="Querying Data",
        published_at=dt.datetime(2020, 1, 1),
        content="How 2 query data...",
        authors=[a1],
    )
    bp2 = BlogPost(
        title="Automating Monkey Jobs",
        published_at=dt.datetime(2019, 1, 1),
        content="How 2 automate monkey jobs...",
        authors=[a2, a3],
    )
    c1 = Comment(content="Dope!", author=a2, blogpost=bp1)
    c2 = Comment(content="Cool!", author=a1, blogpost=bp2)
    s.add_all([a1, a2, a3, bp1, bp2, c1, c2])
    s.flush()
    yield s
    s.rollback()


def apply_odata_query_bc_sqla1(*args, **kwargs):
    """
    Check for backwards compatibility with the "old style" of ORM querying.
    See: GITHUB-34
    """
    return apply_odata_query(*args, **kwargs)


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
    ],
)
@pytest.mark.parametrize(
    "apply_func",
    [
        pytest.param(apply_odata_query, id="ORM"),
        pytest.param(apply_odata_query_bc_sqla1, id="ORM 1.x"),
        pytest.param(apply_odata_core, id="Core"),
    ],
)
def test_query_with_odata(
    model: Type[Base],
    query: str,
    exp_results: int,
    apply_func: Callable,
    sample_data_sess,
):
    # ORM mode 1.x:
    if apply_func is apply_odata_query_bc_sqla1:
        base_q = sample_data_sess.query(model)
        q = apply_func(base_q, query)
        results = q.all()
        assert len(results) == exp_results
        return

    # ORM mode:
    elif apply_func is apply_odata_query:
        base_q = select(model)

    # Core mode:
    elif apply_func is apply_odata_core:
        base_q = select(model.__table__)

    else:
        raise ValueError(apply_func)

    try:
        q = apply_func(base_q, query)
    except NotImplementedError:
        pytest.xfail("Not implemented yet.")

    results = sample_data_sess.execute(q).scalars().all()
    assert len(results) == exp_results


@pytest.mark.parametrize(
    "apply_func",
    [
        pytest.param(apply_odata_query, id="ORM"),
        pytest.param(apply_odata_query_bc_sqla1, id="ORM 1.x"),
    ],
)
def test_query_with_existing_join(apply_func, sample_data_sess):
    """
    GITHUB-37
    """
    odata_query = "author/name eq 'Gorilla'"
    exp_results = 1

    # ORM mode 1.x:
    if apply_func is apply_odata_query_bc_sqla1:
        base_q = sample_data_sess.query(Comment).join(
            Author, Comment.author_id == Author.id
        )
        q = apply_func(base_q, odata_query)
        results = q.all()
        assert len(results) == exp_results
        return

    # ORM mode:
    elif apply_func is apply_odata_query:
        base_q = select(Comment).join(Comment.author)

    else:
        raise ValueError(apply_func)

    q = apply_func(base_q, odata_query)

    results = sample_data_sess.execute(q).scalars().all()
    assert len(results) == exp_results
