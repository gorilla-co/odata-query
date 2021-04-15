import datetime as dt
from typing import Type

import pytest
from sqlalchemy import select

from odata_query.sqlalchemy import AstToSqlAlchemyClauseVisitor

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


@pytest.mark.parametrize(
    "model, query, exp_results",
    [
        (Author, "name eq 'Baboon'", 1),
        (Author, "startswith(name, 'Gori')", 1),
        (BlogPost, "contains(content, 'How')", 2),
        (BlogPost, "published_at gt 2019-06-01", 1),
    ],
)
def test_query_with_odata(
    model: Type[Base],
    query: str,
    exp_results: int,
    lexer,
    parser,
    sample_data_sess,
):
    ast = parser.parse(lexer.tokenize(query))
    transformer = AstToSqlAlchemyClauseVisitor()
    where_clause = transformer.visit(ast)

    q = select(model).filter(where_clause)
    results = sample_data_sess.execute(q).scalars().all()
    assert len(results) == exp_results
