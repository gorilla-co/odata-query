from typing import List

from sqlalchemy.sql.expression import ClauseElement, Select

from odata_query.grammar import ODataLexer, ODataParser  # type: ignore

from .sqlalchemy_clause import AstToSqlAlchemyClauseVisitor


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
    model = query.column_descriptions[0]["entity"]

    ast = parser.parse(lexer.tokenize(odata_query))
    transformer = AstToSqlAlchemyClauseVisitor(model)
    where_clause = transformer.visit(ast)

    for j in transformer.join_relationships:
        if str(j) not in _get_joined_attrs(query):
            query = query.join(j)

    return query.filter(where_clause)
