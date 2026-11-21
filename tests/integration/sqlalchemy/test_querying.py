import datetime as dt
from typing import Callable, Type

import pytest
from sqlalchemy import select
from sqlalchemy.dialects import mssql, mysql, oracle, postgresql, sqlite

from odata_query.exceptions import (
    InvalidFieldException,
    InvalidOrderByException,
    InvalidQueryOptionException,
    ParsingException,
)
from odata_query.sqlalchemy import apply_odata_core, apply_odata_query
from odata_query.sqlalchemy.ordering_ext import SpecOrdering

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


@pytest.mark.parametrize(
    "apply_func",
    [
        pytest.param(apply_odata_query, id="ORM"),
        pytest.param(apply_odata_query_bc_sqla1, id="ORM 1.x"),
    ],
)
def test_query_using_the_same_relationship_twice_joins_it_once(
    apply_func, sample_data_sess
):
    odata_query = "author/name eq 'Gorilla' or author/name eq 'Baboon'"

    if apply_func is apply_odata_query_bc_sqla1:
        results = apply_func(sample_data_sess.query(Comment), odata_query).all()
    else:
        q = apply_func(select(Comment), odata_query)
        results = sample_data_sess.execute(q).scalars().all()

    assert len(results) == 2


def _author_query(apply_func, session, odata_query, **options):
    """
    Authors ordered by name (Baboon, Gorilla, Saki), as a list of names.
    """
    if apply_func is apply_odata_query_bc_sqla1:
        base_q = session.query(Author).order_by(Author.name)
        return [a.name for a in apply_func(base_q, odata_query, **options).all()]

    if apply_func is apply_odata_query:
        base_q = select(Author).order_by(Author.name)
        return [
            a.name
            for a in session.execute(apply_func(base_q, odata_query, **options))
            .scalars()
            .all()
        ]

    table = Author.__table__
    base_q = select(table).order_by(table.c.name)
    rows = session.execute(apply_func(base_q, odata_query, **options)).all()
    return [r.name for r in rows]


ALL_APPLY_FUNCS = pytest.mark.parametrize(
    "apply_func",
    [
        pytest.param(apply_odata_query, id="ORM"),
        pytest.param(apply_odata_query_bc_sqla1, id="ORM 1.x"),
        pytest.param(apply_odata_core, id="Core"),
    ],
)


@ALL_APPLY_FUNCS
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
        # Paging applies to the filtered results:
        ("name ne 'Baboon'", {"top": 1, "skip": 1}, ["Saki"]),
        ("name eq 'Nobody'", {"top": 1, "skip": 1}, []),
        # Ordering overrides the ordering of the base query, and happens before paging:
        ("true eq true", {"orderby": "name"}, ["Baboon", "Gorilla", "Saki"]),
        ("true eq true", {"orderby": "name asc"}, ["Baboon", "Gorilla", "Saki"]),
        ("true eq true", {"orderby": "name desc"}, ["Saki", "Gorilla", "Baboon"]),
        ("true eq true", {"orderby": "id"}, ["Gorilla", "Baboon", "Saki"]),
        ("true eq true", {"orderby": "id desc"}, ["Saki", "Baboon", "Gorilla"]),
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
        (
            "true eq true",
            {"orderby": "id mod 2 desc, name"},
            ["Gorilla", "Saki", "Baboon"],
        ),
        (
            "true eq true",
            {"orderby": "id mod 2, name desc"},
            ["Baboon", "Saki", "Gorilla"],
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
    ],
)
def test_top_and_skip(apply_func, odata_query, options, exp_names, sample_data_sess):
    assert (
        _author_query(apply_func, sample_data_sess, odata_query, **options) == exp_names
    )


@pytest.mark.parametrize(
    "apply_func, base_q",
    [
        pytest.param(apply_odata_query, select(Author), id="ORM"),
        pytest.param(apply_odata_core, select(Author.__table__), id="Core"),
    ],
)
@pytest.mark.parametrize(
    "options, expected_exception",
    [
        ({"top": -1}, InvalidQueryOptionException),
        ({"skip": -1}, InvalidQueryOptionException),
        ({"top": "5"}, InvalidQueryOptionException),
        ({"orderby": ""}, ParsingException),
        ({"orderby": "name desc desc"}, ParsingException),
        ({"orderby": "name,"}, ParsingException),
        ({"orderby": "nonexistent"}, InvalidFieldException),
        ({"orderby": "name, nonexistent desc"}, InvalidFieldException),
    ],
)
def test_invalid_options_are_rejected_before_building_the_query(
    apply_func, base_q, options, expected_exception
):
    with pytest.raises(expected_exception):
        apply_func(base_q, "true eq true", **options)


def test_top_and_skip_replace_a_limit_and_offset_already_on_the_query(
    sample_data_sess,
):
    base_q = select(Author).order_by(Author.name).limit(1).offset(2)

    q = apply_odata_query(base_q, "true eq true", top=2, skip=1)

    result = sample_data_sess.execute(q).scalars().all()
    assert [a.name for a in result] == ["Gorilla", "Saki"]


def test_top_and_skip_with_existing_join(sample_data_sess):
    base_q = (
        sample_data_sess.query(Comment)
        .join(Author, Comment.author_id == Author.id)
        .order_by(Comment.content)
    )
    q = apply_odata_query(base_q, "author/name ne 'Nobody'", top=1, skip=1)
    assert [c.content for c in q.all()] == ["Dope!"]


def test_top_and_skip_page_over_unique_rows_with_distinct(sample_data_sess):
    gorilla = sample_data_sess.query(Author).filter_by(name="Gorilla").one()
    blogpost = BlogPost(
        title="Querying More", published_at=dt.datetime(2021, 1, 1), content="..."
    )
    sample_data_sess.add(blogpost)
    blogpost.authors = [gorilla]
    sample_data_sess.flush()
    odata_query = "contains(blogposts/title, 'Querying')"

    unique = apply_odata_query(select(Author).distinct(), odata_query, top=1)
    duplicated = apply_odata_query(select(Author), odata_query, top=2)

    assert [a.name for a in sample_data_sess.execute(unique).scalars()] == ["Gorilla"]
    assert [a.name for a in sample_data_sess.execute(duplicated).scalars()] == [
        "Gorilla",
        "Gorilla",
    ]


@pytest.mark.parametrize(
    "dialect, options, exp_suffix, exp_limit_and_offset",
    [
        (
            postgresql,
            {"top": 3, "skip": 2},
            "LIMIT %(param_2)s OFFSET %(param_3)s",
            [3, 2],
        ),
        (postgresql, {"skip": 2}, "LIMIT ALL OFFSET %(param_2)s", [2]),
        (mysql, {"top": 3, "skip": 2}, "LIMIT %s, %s", [2, 3]),
        (mysql, {"skip": 2}, "LIMIT %s, 18446744073709551615", [2]),
    ],
)
def test_paging_is_valid_sql_for_dialect(
    dialect, options, exp_suffix, exp_limit_and_offset
):
    q = apply_odata_query(select(Author), "name eq 'Gorilla'", **options)
    compiled = q.compile(dialect=dialect.dialect())
    assert str(compiled).endswith(exp_suffix)
    assert list(compiled.params.values())[1:] == exp_limit_and_offset


@pytest.fixture
def comments_sess(sample_data_sess):
    """
    Adds a comment without author or content, and a second 'Cool!' comment,
    to the sample data. Comments by id: 1 'Dope!' (Baboon), 2 'Cool!' (Gorilla),
    3 None (no author), 4 'Cool!' (Saki). Comments 1, 3 and 4 are on blogpost
    'Querying Data'.
    """
    saki = sample_data_sess.query(Author).filter_by(name="Saki").one()
    blogpost = sample_data_sess.query(BlogPost).filter_by(title="Querying Data").one()
    sample_data_sess.add_all(
        [
            Comment(content=None, blogpost=blogpost),
            Comment(content="Cool!", author=saki, blogpost=blogpost),
        ]
    )
    sample_data_sess.flush()
    return sample_data_sess


def _comments(apply_func, session, odata_query, base_order_by=None, **options):
    """
    Comments as a list of ``(id, content)`` tuples.
    """
    model = Comment if apply_func is not apply_odata_core else Comment.__table__
    if apply_func is apply_odata_query_bc_sqla1:
        base_q = session.query(Comment)
        if base_order_by is not None:
            base_q = base_q.order_by(base_order_by(Comment))
        rows = apply_func(base_q, odata_query, **options).all()
    else:
        base_q = select(model)
        if base_order_by is not None:
            base_q = base_q.order_by(base_order_by(model))
        q = apply_func(base_q, odata_query, **options)
        rows = session.execute(q).scalars().all() if model is Comment else None
        if rows is None:
            rows = session.execute(q).all()
    return [(r.id, r.content) for r in rows]


@ALL_APPLY_FUNCS
@pytest.mark.parametrize(
    "orderby, exp_ids",
    [
        # NULL sorts first when ascending, last when descending:
        ("content", [3, 2, 4, 1]),
        ("content asc", [3, 2, 4, 1]),
        ("content desc", [1, 2, 4, 3]),
        # Ties are broken by the next item:
        ("content, id desc", [3, 4, 2, 1]),
        ("content desc, id desc", [1, 4, 2, 3]),
        ("content, id", [3, 2, 4, 1]),
        ("id desc", [4, 3, 2, 1]),
        # Expressions can contain NULL too:
        ("length(content), id", [3, 1, 2, 4]),
        ("tolower(content) desc, id desc", [1, 4, 2, 3]),
        ("content eq 'Cool!' desc, id", [2, 4, 1, 3]),
        ("content eq 'Cool!', id desc", [3, 1, 4, 2]),
        # A foreign key is a value, and can be NULL:
        ("author_id desc", [4, 1, 2, 3]),
    ],
)
def test_orderby_on_sample_comments(apply_func, orderby, exp_ids, comments_sess):
    result = _comments(apply_func, comments_sess, "true eq true", orderby=orderby)
    assert [id_ for id_, _ in result] == exp_ids


@ALL_APPLY_FUNCS
def test_orderby_comes_before_ordering_that_is_already_on_the_query(
    apply_func, comments_sess
):
    result = _comments(
        apply_func,
        comments_sess,
        "true eq true",
        base_order_by=lambda model: (
            model.id if hasattr(model, "id") else model.c.id
        ).desc(),
        orderby="content",
    )
    # The two 'Cool!' comments tie on content, so the base ordering decides:
    assert [id_ for id_, _ in result] == [3, 4, 2, 1]


@ALL_APPLY_FUNCS
def test_orderby_with_filter_top_and_skip(apply_func, comments_sess):
    result = _comments(
        apply_func,
        comments_sess,
        "id gt 1",
        orderby="content desc, id",
        top=2,
        skip=1,
    )
    assert [id_ for id_, _ in result] == [4, 3]


@pytest.mark.parametrize(
    "apply_func",
    [
        pytest.param(apply_odata_query, id="ORM"),
        pytest.param(apply_odata_query_bc_sqla1, id="ORM 1.x"),
    ],
)
@pytest.mark.parametrize(
    "odata_query, orderby, exp_ids",
    [
        # Comments without author are kept, and sort as NULL:
        ("true eq true", "author/name", [3, 1, 2, 4]),
        ("true eq true", "author/name desc", [4, 2, 1, 3]),
        ("true eq true", "author/name desc, id desc", [4, 2, 1, 3]),
        ("true eq true", "tolower(author/name) desc", [4, 2, 1, 3]),
        ("true eq true", "author/name, content", [3, 1, 2, 4]),
        ("true eq true", "content, author/name desc", [3, 4, 2, 1]),
        ("true eq true", "author/name desc", [4, 2, 1, 3]),
        # The relationship is only joined once when filter and ordering share it:
        ("author/name ne 'Baboon'", "author/name desc", [4, 2]),
        ("author/name ne 'Baboon'", "author/name", [2, 4]),
        (
            "author/name ne 'Baboon' or author/name eq 'Baboon'",
            "author/name",
            [1, 2, 4],
        ),
        # ... or when ordering uses it more than once:
        ("true eq true", "author/name, author/id desc", [3, 1, 2, 4]),
        # Different relationships can be combined:
        ("true eq true", "blogpost/title, author/name desc", [2, 4, 1, 3]),
    ],
)
def test_orderby_on_related_entities(
    apply_func, odata_query, orderby, exp_ids, comments_sess
):
    result = _comments(apply_func, comments_sess, odata_query, orderby=orderby)
    assert [id_ for id_, _ in result] == exp_ids


def test_orderby_on_relationship_with_existing_join(comments_sess):
    base_q = comments_sess.query(Comment).join(Author, Comment.author_id == Author.id)
    q = apply_odata_query(base_q, "true eq true", orderby="author/name desc")
    # The existing join is an inner join, so the comment without author is gone:
    assert [c.id for c in q.all()] == [4, 2, 1]


@pytest.mark.parametrize(
    "model, orderby",
    [
        # A collection would repeat the root rows:
        (Author, "blogposts/title"),
        (Author, "blogposts/title desc"),
        (Author, "name, comments/content"),
        (Author, "length(blogposts/title)"),
        (Comment, "author/blogposts/title"),
        (BlogPost, "authors/name"),
        # Entities are not values:
        (Author, "blogposts"),
        (Comment, "author"),
        (Comment, "author desc"),
        (Comment, "blogpost, id"),
    ],
)
def test_orderby_on_collections_and_entities_is_rejected(model, orderby):
    with pytest.raises(InvalidOrderByException):
        apply_odata_query(select(model), "true eq true", orderby=orderby)


def test_orderby_on_collection_names_the_collection():
    with pytest.raises(InvalidOrderByException) as exc_info:
        apply_odata_query(select(Author), "true eq true", orderby="blogposts/title")

    assert exc_info.value.field_name == "blogposts"


def test_failed_orderby_does_not_modify_the_query_that_was_passed_in():
    base_q = select(Author)
    with pytest.raises(InvalidOrderByException):
        apply_odata_query(base_q, "true eq true", orderby="blogposts/title")

    assert str(base_q) == str(select(Author))


@pytest.mark.parametrize(
    "dialect, exp_order_by",
    [
        (
            postgresql,
            "comment.content ASC NULLS FIRST, comment.id DESC, "
            "lower(comment.content) DESC NULLS LAST",
        ),
        (
            oracle,
            '"comment".content ASC NULLS FIRST, "comment".id DESC, '
            'lower("comment".content) DESC NULLS LAST',
        ),
        # NULL is smaller than any value here, which is the OData order already:
        (
            mysql,
            "comment.content ASC, comment.id DESC, lower(comment.content) DESC",
        ),
        (
            sqlite,
            "comment.content ASC, comment.id DESC, lower(comment.content) DESC",
        ),
        (
            mssql,
            "comment.content ASC, comment.id DESC, lower(comment.content) DESC",
        ),
    ],
)
@pytest.mark.parametrize(
    "apply_func, base_q",
    [
        pytest.param(apply_odata_query, select(Comment), id="ORM"),
        pytest.param(apply_odata_core, select(Comment.__table__), id="Core"),
    ],
)
def test_orderby_null_ordering_in_sql_of_dialect(
    apply_func, base_q, dialect, exp_order_by
):
    q = apply_func(
        base_q, "true eq true", orderby="content, id desc, tolower(content) desc"
    )
    sql = str(q.compile(dialect=dialect.dialect()))

    assert sql.split("ORDER BY")[1].strip() == exp_order_by


def test_orderby_does_not_ask_for_null_ordering_of_columns_that_are_not_nullable():
    q = apply_odata_query(select(Author), "true eq true", orderby="id, name desc")
    sql = str(q.compile(dialect=postgresql.dialect()))

    assert sql.split("ORDER BY")[1].strip() == "author.id ASC, author.name DESC"


def test_orderby_asks_for_null_ordering_of_columns_that_are_null_in_a_missing_relationship():
    q = apply_odata_query(
        select(Comment), "true eq true", orderby="author/name desc, id"
    )
    sql = str(q.compile(dialect=postgresql.dialect()))

    # author.name is not nullable, but there is no author for some comments:
    assert (
        sql.split("ORDER BY")[1].strip()
        == "author.name DESC NULLS LAST, comment.id ASC"
    )


def test_orderby_statements_that_differ_in_null_ordering_do_not_share_a_cache_key():
    may_be_null = SpecOrdering(Comment.__table__.c.id, True, may_be_null=True)
    cannot_be_null = SpecOrdering(Comment.__table__.c.id, True, may_be_null=False)

    assert may_be_null._generate_cache_key() != cannot_be_null._generate_cache_key()
