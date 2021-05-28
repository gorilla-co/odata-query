from django.db.models.query import QuerySet

from odata_query.grammar import ODataLexer, ODataParser  # type: ignore

from .django_q import AstToDjangoQVisitor


def apply_odata_query(queryset: QuerySet, odata_query: str) -> QuerySet:
    """
    Shorthand for applying an OData query to a Django QuerySet.

    Args:
        queryset: Django QuerySet to apply the OData query to.
        odata_query: OData query string.
    Returns:
        QuerySet: The modified QuerySet
    """
    lexer = ODataLexer()
    parser = ODataParser()
    model = queryset.model

    ast = parser.parse(lexer.tokenize(odata_query))
    transformer = AstToDjangoQVisitor(model)
    where_clause = transformer.visit(ast)

    if transformer.queryset_annotations:
        queryset = queryset.annotate(**transformer.queryset_annotations)

    return queryset.filter(where_clause)
