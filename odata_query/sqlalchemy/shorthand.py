from typing import List, Optional

from sqlalchemy.orm.query import Query
from sqlalchemy.sql.expression import ClauseElement, Select

from odata_query.grammar import ODataLexer, ODataParser
from odata_query.utils import validate_top_and_skip

from .core import AstToSqlAlchemyCoreVisitor
from .orm import AstToSqlAlchemyOrmVisitor


def _get_joined_attrs(query: Select) -> List[str]:
    # use _legacy_setup_joins for legacy Query objects
    setup_joins = (
        getattr(query, "_legacy_setup_joins", query._setup_joins) or query._setup_joins
    )
    return [str(join[0]) for join in setup_joins]


def _apply_paging(
    query: ClauseElement, top: Optional[int], skip: Optional[int]
) -> ClauseElement:
    if skip is not None:
        query = query.offset(skip)
    if top is not None:
        query = query.limit(top)
    return query


def apply_odata_query(
    query: ClauseElement,
    odata_query: str,
    *,
    top: Optional[int] = None,
    skip: Optional[int] = None,
) -> ClauseElement:
    """
    Shorthand for applying an OData query to a SQLAlchemy query.

    Args:
        query: SQLAlchemy query to apply the OData query to.
        odata_query: OData ``$filter`` expression.
        top: Maximum number of results to return (OData ``$top``).
        skip: Number of results to skip (OData ``$skip``).
    Returns:
        ClauseElement: The modified query. Filters across collection
        relationships can return a row once per match; start from
        ``query.distinct()`` to page over unique rows.
    Raises:
        InvalidQueryOptionException: If ``top`` or ``skip`` is not a
            non-negative integer.
    """
    validate_top_and_skip(top, skip)

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

    existing_joins = _get_joined_attrs(query)
    for required_join in transformer.join_relationships:
        if (
            str(required_join) not in existing_joins
            and str(required_join.key) not in existing_joins
        ):
            query = query.join(required_join)

    return _apply_paging(query.filter(where_clause), top, skip)


def apply_odata_core(
    query: ClauseElement,
    odata_query: str,
    *,
    top: Optional[int] = None,
    skip: Optional[int] = None,
) -> ClauseElement:
    """
    Shorthand for applying an OData query to a SQLAlchemy core.

    Args:
        query: SQLAlchemy query to apply the OData query to.
        odata_query: OData ``$filter`` expression.
        top: Maximum number of results to return (OData ``$top``).
        skip: Number of results to skip (OData ``$skip``).
    Returns:
        ClauseElement: The modified query. Filters across collection
        relationships can return a row once per match; start from
        ``query.distinct()`` to page over unique rows.
    Raises:
        InvalidQueryOptionException: If ``top`` or ``skip`` is not a
            non-negative integer.
    """
    validate_top_and_skip(top, skip)

    lexer = ODataLexer()
    parser = ODataParser()
    table = query.columns_clause_froms[0]

    ast = parser.parse(lexer.tokenize(odata_query))
    transformer = AstToSqlAlchemyCoreVisitor(table)
    where_clause = transformer.visit(ast)
    return _apply_paging(query.filter(where_clause), top, skip)
