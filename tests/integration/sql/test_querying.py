import pytest

from odata_query import sql


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
