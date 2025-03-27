import re
from typing import List, Literal

from odata_query.grammar import ODataLexer, ODataParser  # type: ignore
from sqlalchemy.orm.query import Query
from sqlalchemy.sql.expression import ClauseElement, Select

from .core import AstToSqlAlchemyCoreVisitor
from .orm import AstToSqlAlchemyOrmVisitor


QueryOptions = dict[
    Literal["filter", "count", "orderby", "top", "skip", "search", "format"],
    str,
]

query_option_names = set(
    [
        "filter",
        "count",
        "orderby",
        "top",
        "skip",
        "search",
        "format",
    ]
)


def _get_query_options(odata_query: str) -> QueryOptions:
    """Get system query options as per odata specification"""

    query_options = {}

    for component in odata_query.split("$"):
        component_name = None
        match = re.match("(\w+)=", component)
        if match:
            component_name = match.group(1)
            if component_name not in query_option_names:
                raise ValueError(f"Unknown option name {component_name}")
            query_options[component_name] = component[len(match.group()) :]
        else:
            query_options["filter"] = component

    return query_options


def _apply_query_options(
    query_options: QueryOptions, where_clause: ClauseElement
) -> ClauseElement:
    """Applies OData query options to a SQLAlchemy query."""

    # Apply orderby system query option.
    orderby = query_options.get("orderby", None)
    if orderby:
        where_clause = where_clause.order_by(orderby)

    # Apply top and skip system query options.
    top = query_options.get("top", None)
    skip = query_options.get("skip", None)
    if top and skip:
        top = int(top)
        skip = int(skip)
        where_clause = where_clause.limit(top).offset(skip * top)
    elif top:
        where_clause = where_clause.limit(int(top))

    return where_clause


def _get_joined_attrs(query: Select) -> List[str]:
    # use _legacy_setup_joins for legacy Query objects
    setup_joins = (
        getattr(query, "_legacy_setup_joins", query._setup_joins) or query._setup_joins
    )
    return [str(join[0]) for join in setup_joins]


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

    query_options = _get_query_options(odata_query)
    ast = parser.parse(lexer.tokenize(query_options["filter"]))
    transformer = AstToSqlAlchemyOrmVisitor(model)
    where_clause = transformer.visit(ast)

    existing_joins = _get_joined_attrs(query)
    for required_join in transformer.join_relationships:
        if (
            str(required_join) not in existing_joins
            and str(required_join.key) not in existing_joins
        ):
            query = query.join(required_join)

    query = query.filter(where_clause)
    query = _apply_query_options(query_options, query)
    return query


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

    query_options = _get_query_options(odata_query)
    ast = parser.parse(lexer.tokenize(query_options["filter"]))
    transformer = AstToSqlAlchemyCoreVisitor(table)
    where_clause = transformer.visit(ast)

    query = query.filter(where_clause)
    query = _apply_query_options(query_options, query)
    return query
