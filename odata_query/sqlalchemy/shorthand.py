from typing import List

from sqlalchemy.sql.expression import ClauseElement, Select

from odata_query.grammar import ODataLexer, ODataParser  # type: ignore

from .sqlalchemy_clause import AstToSqlAlchemyClauseVisitor


def _get_joined_attrs(query: Select) -> List[str]:
    return [str(join[0]) for join in query._setup_joins]


def create_odata_ast(odata_query: str) -> ClauseElement:
    """
    Create an AST for a query

    Args:
        odata_query: OData query string.
    Returns:
        AST
    """
    lexer = ODataLexer()
    parser = ODataParser()
    ast = parser.parse(lexer.tokenize(odata_query))
    return ast


def apply_ast_query(query: ClauseElement, ast) -> ClauseElement:
    """
    Apply a parsed OData query AST to a SQLAlchemy query.

    Args:
        query: SQLAlchemy query to apply the OData query to.
    Returns:
        ClauseElement: The modified query
    """
    model = [col["entity"] for col in query.column_descriptions]

    transformer = AstToSqlAlchemyClauseVisitor(model)
    where_clause = transformer.visit(ast)

    for j in transformer.join_relationships:
        if str(j) not in _get_joined_attrs(query):
            query = query.join(j)

    return query.filter(where_clause)


def apply_odata_query(query: ClauseElement, odata_query: str) -> ClauseElement:
    """
    Shorthand for applying an OData query to a SQLAlchemy query.

    Args:
        query: SQLAlchemy query to apply the OData query to.
        odata_query: OData query string.
    Returns:
        ClauseElement: The modified query
    """
    ast = create_odata_ast(odata_query)
    query = apply_ast_query(query, ast)

    return query
