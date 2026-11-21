from typing import Optional

from django.db.models.query import QuerySet

from odata_query.grammar import ODataLexer, ODataParser
from odata_query.utils import validate_top_and_skip

from .django_q import AstToDjangoQVisitor


def apply_odata_query(
    queryset: QuerySet,
    odata_query: str,
    *,
    top: Optional[int] = None,
    skip: Optional[int] = None,
) -> QuerySet:
    """
    Shorthand for applying an OData query to a Django QuerySet.

    Args:
        queryset: Django QuerySet to apply the OData query to.
        odata_query: OData ``$filter`` expression.
        top: Maximum number of results to return (OData ``$top``).
        skip: Number of results to skip (OData ``$skip``).
    Returns:
        QuerySet: The modified QuerySet. When ``top`` or ``skip`` is given the
        QuerySet is sliced, so it can no longer be filtered or made
        ``distinct()``. Filters across collection relationships can return a
        row once per match; pass in ``queryset.distinct()`` to page over unique
        rows.
    Raises:
        InvalidQueryOptionException: If ``top`` or ``skip`` is not a
            non-negative integer.
    """
    validate_top_and_skip(top, skip)

    lexer = ODataLexer()
    parser = ODataParser()
    model = queryset.model

    ast = parser.parse(lexer.tokenize(odata_query))
    transformer = AstToDjangoQVisitor(model)
    where_clause = transformer.visit(ast)

    if transformer.queryset_annotations:
        queryset = queryset.annotate(**transformer.queryset_annotations)

    queryset = queryset.filter(where_clause)

    if top is not None:
        return queryset[(skip or 0) : (skip or 0) + top]
    if skip is not None:
        return queryset[skip:]
    return queryset
