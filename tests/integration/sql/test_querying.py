import sqlite3

import pytest

from odata_query import sql
from odata_query.grammar import ODataLexer, ODataParser, parse_orderby


@pytest.fixture
def sample_data_sess(db_conn, db_schema):
    cur = db_conn.cursor()

    cur.execute("BEGIN")
    cur.execute("INSERT INTO author (name) VALUES ('Gorilla'), ('Baboon'), ('Saki')")
    cur.execute(
        "INSERT INTO blogpost (title, published_at, content) VALUES "
        "('Querying Data', '2020-01-01T00:00:00', 'How 2 query data...'), "
        "('Automating Monkey Jobs', '2019-01-01T00:00:00', 'How 2 automate monkey jobs...')"
    )
    cur.execute(
        "INSERT INTO author_blogpost (author_id, blogpost_id) VALUES "
        "(1, 1), "
        "(2, 2), "
        "(3, 2)"
    )
    cur.execute(
        "INSERT INTO comment (content, author_id, blogpost_id) VALUES "
        "('Dope!', 2, 1), "
        "('Cool!', 1, 2)"
    )

    yield cur

    cur.execute("ROLLBACK")


@pytest.mark.parametrize(
    "table, query, exp_results",
    [
        ("author", "name eq 'Baboon'", 1),
        ("author", "startswith(name, 'Gori')", 1),
        ("blogpost", "contains(content, 'How')", 2),
        ("blogpost", "published_at gt 2019-06-01", 1),
        # (Author, "contains(blogposts/title, 'Monkey')", 2),
        # (Author, "startswith(blogposts/comments/content, 'Cool')", 2),
        # (Author, "comments/any()", 2),
        # (BlogPost, "authors/any(a: contains(a/name, 'o'))", 2),
        # (BlogPost, "authors/all(a: contains(a/name, 'o'))", 1),
        # (Author, "blogposts/comments/any(c: contains(c/content, 'Cool'))", 2),
        ("author", "id eq a7af27e6-f5a0-11e9-9649-0a252986adba", 0),
        (
            "author",
            "id in (a7af27e6-f5a0-11e9-9649-0a252986adba, 800c56e4-354d-11eb-be38-3af9d323e83c)",
            0,
        ),
        # (BlogPost, "comments/author eq 0", 0),
        ("blogpost", "substring(content, 0) eq 'test'", 0),
        ("blogpost", "year(published_at) eq 2019", 1),
        # GITHUB-19
        ("blogpost", "contains(title, 'Query') eq true", 1),
        ("blogpost", "contains(tolower(title), tolower('Query'))", 1),
    ],
)
def test_query_with_odata(
    table: str, query: str, exp_results: int, lexer, parser, sample_data_sess
):
    ast = parser.parse(lexer.tokenize(query))
    visitor = sql.AstToSqliteSqlVisitor()
    where_clause = visitor.visit(ast)

    results = sample_data_sess.execute(
        f'SELECT * FROM "{table}" WHERE {where_clause}'
    ).fetchall()
    assert len(results) == exp_results


@pytest.mark.parametrize("func", ["contains", "startswith", "endswith"])
def test_like_functions_do_not_allow_sql_injection(
    func: str, lexer, parser, sample_data_sess
):
    query = f"{func}(name, 'x'' UNION SELECT id, name FROM author-- ')"
    ast = parser.parse(lexer.tokenize(query))
    where_clause = sql.AstToSqliteSqlVisitor().visit(ast)

    results = sample_data_sess.execute(
        f"SELECT * FROM author WHERE {where_clause}"
    ).fetchall()
    assert results == []


@pytest.fixture
def comments_sess(sample_data_sess):
    """
    Adds a comment without author or content, and a second 'Cool!' comment.
    Comments by id: 1 'Dope!' (author 2), 2 'Cool!' (author 1),
    3 NULL (no author), 4 'Cool!' (author 3).
    """
    sample_data_sess.execute(
        "INSERT INTO comment (content, author_id, blogpost_id) VALUES "
        "(NULL, NULL, 1), "
        "('Cool!', 3, 1)"
    )
    return sample_data_sess


def _comment_ids(
    cur, odata_filter="true eq true", orderby=None, top=None, skip=None, visitor=None
) -> list:
    visitor = visitor or sql.AstToSqliteSqlVisitor()
    where_clause = visitor.visit(
        ODataParser().parse(ODataLexer().tokenize(odata_filter))
    )
    query = f'SELECT id FROM "comment" WHERE {where_clause}'
    if orderby is not None:
        query += " ORDER BY " + visitor.visit(parse_orderby(orderby))
    query += " " + visitor.paging_clause(top, skip)

    return [row[0] for row in cur.execute(query).fetchall()]


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
        ("id desc", [4, 3, 2, 1]),
        ("author_id desc", [4, 1, 2, 3]),
        # Expressions can contain NULL too:
        ("length(content), id", [3, 1, 2, 4]),
        ("tolower(content) desc, id desc", [1, 4, 2, 3]),
        ("content eq 'Cool!' desc, id", [2, 4, 1, 3]),
        ("content eq 'Cool!', id desc", [3, 1, 4, 2]),
        ("id mod 2 desc, id", [1, 3, 2, 4]),
    ],
)
def test_orderby(orderby, exp_ids, comments_sess):
    assert _comment_ids(comments_sess, orderby=orderby) == exp_ids


@pytest.mark.skipif(
    sqlite3.sqlite_version_info < (3, 30, 0),
    reason="SQLite only supports NULLS FIRST/LAST since 3.30",
)
@pytest.mark.parametrize(
    "orderby, exp_ids",
    [
        ("content", [3, 2, 4, 1]),
        ("content desc", [1, 2, 4, 3]),
        ("content, id desc", [3, 4, 2, 1]),
        ("tolower(content) desc, id", [1, 2, 4, 3]),
    ],
)
def test_orderby_with_explicit_null_ordering_of_the_standard_visitor(
    orderby, exp_ids, comments_sess
):
    ids = _comment_ids(comments_sess, orderby=orderby, visitor=sql.AstToSqlVisitor())

    assert ids == exp_ids


@pytest.mark.parametrize(
    "where, orderby, top, skip, exp_ids",
    [
        (None, "id", None, None, [1, 2, 3, 4]),
        (None, "id", 2, None, [1, 2]),
        (None, "id", None, 1, [2, 3, 4]),
        # Distinguishes a plain offset from `skip * top`, and from swapped args:
        (None, "id", 2, 1, [2, 3]),
        (None, "id", 1, 2, [3]),
        # Boundaries:
        (None, "id", 0, None, []),
        (None, "id", 0, 1, []),
        (None, "id", None, 0, [1, 2, 3, 4]),
        (None, "id", 10, None, [1, 2, 3, 4]),
        (None, "id", None, 4, []),
        (None, "id", 5, 10, []),
        # Paging happens after ordering, and after filtering:
        (None, "content desc, id", 2, 1, [2, 4]),
        (None, "content, id desc", 3, 1, [4, 2, 1]),
        ("id gt 1", "content desc, id", 2, 1, [4, 3]),
        ("id gt 1", "id desc", None, 1, [3, 2]),
        ("id gt 100", "id", 2, 1, []),
        # Without ordering, paging still returns rows:
        (None, None, 2, None, None),
    ],
)
def test_orderby_with_top_and_skip(where, orderby, top, skip, exp_ids, comments_sess):
    ids = _comment_ids(comments_sess, where or "true eq true", orderby, top, skip)

    if exp_ids is None:
        assert len(ids) == top
    else:
        assert ids == exp_ids
