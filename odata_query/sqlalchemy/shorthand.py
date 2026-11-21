from typing import List, Optional

from sqlalchemy.orm.query import Query
from sqlalchemy.sql.expression import ClauseElement, Select

from odata_query.grammar import ODataLexer, ODataParser, parse_orderby
from odata_query.utils import validate_top_and_skip

from .core import AstToSqlAlchemyCoreVisitor
from .orm import AstToSqlAlchemyOrmVisitor


def _get_joined_attrs(query: Select) -> List[str]:
    # use _legacy_setup_joins for legacy Query objects
    setup_joins = (
        getattr(query, "_legacy_setup_joins", query._setup_joins) or query._setup_joins
    )
    return [str(join[0]) for join in setup_joins]


def _apply_ordering(
    query: ClauseElement, ordering: List[ClauseElement]
) -> ClauseElement:
    # The OData ordering takes precedence, ordering that was already on the
    # query still breaks ties.
    return query.order_by(None).order_by(*ordering, *query._order_by_clauses)


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
    orderby: Optional[str] = None,
    top: Optional[int] = None,
    skip: Optional[int] = None,
) -> ClauseElement:
    """
    Shorthand for applying an OData query to a SQLAlchemy query.

    Args:
        query: SQLAlchemy query to apply the OData query to.
        odata_query: OData ``$filter`` expression.
        orderby: OData ``$orderby`` expression, e.g. ``"name, age desc"``. It
            takes precedence over any ordering already on ``query``, which
            then only breaks ties. ``NULL`` sorts first when ascending and
            last when descending.
        top: Maximum number of results to return (OData ``$top``). Replaces
            any limit already on ``query``.
        skip: Number of results to skip (OData ``$skip``). Replaces any
            offset already on ``query``.
    Returns:
        ClauseElement: The modified query. Filters across collection
        relationships can return a row once per match; start from
        ``query.distinct()`` to page over unique rows.
    Raises:
        InvalidQueryOptionException: If ``top`` or ``skip`` is not a
            non-negative integer.
        InvalidOrderByException: If ``orderby`` sorts on a collection or on
            something that is not a value.
    """
    validate_top_and_skip(top, skip)
    orderby_ast = parse_orderby(orderby) if orderby is not None else None

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
    n_filter_joins = len(transformer.join_relationships)
    ordering = transformer.visit(orderby_ast) if orderby_ast else []

    existing_joins = _get_joined_attrs(query)
    for i, required_join in enumerate(transformer.join_relationships):
        if (
            str(required_join) not in existing_joins
            and str(required_join.key) not in existing_joins
        ):
            # Ordering must not drop rows that have no related entity.
            join = query.join if i < n_filter_joins else query.outerjoin
            query = join(required_join)
            existing_joins.append(str(required_join))

    query = query.filter(where_clause)
    if ordering:
        query = _apply_ordering(query, ordering)
    return _apply_paging(query, top, skip)


def apply_odata_core(
    query: ClauseElement,
    odata_query: str,
    *,
    orderby: Optional[str] = None,
    top: Optional[int] = None,
    skip: Optional[int] = None,
) -> ClauseElement:
    """
    Shorthand for applying an OData query to a SQLAlchemy core.

    Args:
        query: SQLAlchemy query to apply the OData query to.
        odata_query: OData ``$filter`` expression.
        orderby: OData ``$orderby`` expression, e.g. ``"name, age desc"``. It
            takes precedence over any ordering already on ``query``, which
            then only breaks ties. ``NULL`` sorts first when ascending and
            last when descending.
        top: Maximum number of results to return (OData ``$top``). Replaces
            any limit already on ``query``.
        skip: Number of results to skip (OData ``$skip``). Replaces any
            offset already on ``query``.
    Returns:
        ClauseElement: The modified query. Filters across collection
        relationships can return a row once per match; start from
        ``query.distinct()`` to page over unique rows.
    Raises:
        InvalidQueryOptionException: If ``top`` or ``skip`` is not a
            non-negative integer.
        InvalidOrderByException: If ``orderby`` sorts on a collection or on
            something that is not a value.
    """
    validate_top_and_skip(top, skip)
    orderby_ast = parse_orderby(orderby) if orderby is not None else None

    lexer = ODataLexer()
    parser = ODataParser()
    table = query.columns_clause_froms[0]

    ast = parser.parse(lexer.tokenize(odata_query))
    transformer = AstToSqlAlchemyCoreVisitor(table)
    where_clause = transformer.visit(ast)
    ordering = transformer.visit(orderby_ast) if orderby_ast else []

    query = query.filter(where_clause)
    if ordering:
        query = _apply_ordering(query, ordering)
    return _apply_paging(query, top, skip)
