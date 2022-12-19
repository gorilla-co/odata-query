from typing import List

from sqlalchemy.orm.query import Query
from sqlalchemy.sql.expression import ClauseElement, Select

from odata_query.grammar import ODataLexer, ODataParser  # type: ignore

from .core import AstToSqlAlchemyCoreVisitor
from .orm import AstToSqlAlchemyOrmVisitor


def _get_joined_attrs(query: Select) -> List[str]:
    return [str(join[0]) for join in query._setup_joins]


def apply_odata_query(query: ClauseElement, odata_query: str) -> ClauseElement:
    """
    Shorthand for applying an OData query to a SQLAlchemy query.

    Args:
        query: SQLAlchemy query to apply the OData query to.
        odata_query: OData query string.
    Returns:
        ClauseElement: The modified query
    """
    lexer = ODataLexer()
    parser = ODataParser()

    clause_elem: ClauseElement
    if isinstance(query, Query):
        # For now, we keep supporting the 1.x style of queries unofficially.
        # GITHUB-34
        clause_elem = query.__clause_element__()
    else:
        clause_elem = query

    model = clause_elem.columns_clause_froms[0].entity_namespace

    ast = parser.parse(lexer.tokenize(odata_query))
    transformer = AstToSqlAlchemyOrmVisitor(model)
    where_clause = transformer.visit(ast)

    for j in transformer.join_relationships:
        if str(j) not in _get_joined_attrs(query):
            query = query.join(j)

    return query.filter(where_clause)


def apply_odata_core(query: ClauseElement, odata_query: str) -> ClauseElement:
    """
    Shorthand for applying an OData query to a SQLAlchemy core.

    Args:
        query: SQLAlchemy query to apply the OData query to.
        odata_query: OData query string.
    Returns:
        ClauseElement: The modified query
    """
    lexer = ODataLexer()
    parser = ODataParser()
    table = query.columns_clause_froms[0]

    ast = parser.parse(lexer.tokenize(odata_query))
    transformer = AstToSqlAlchemyCoreVisitor(table)
    where_clause = transformer.visit(ast)
    return query.filter(where_clause)
