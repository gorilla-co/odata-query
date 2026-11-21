from typing import Optional

from django.db.models.query import QuerySet

from odata_query.grammar import ODataLexer, ODataParser, parse_orderby
from odata_query.utils import validate_top_and_skip

from .django_q import AstToDjangoQVisitor


def apply_odata_query(
    queryset: QuerySet,
    odata_query: str,
    *,
    orderby: Optional[str] = None,
    top: Optional[int] = None,
    skip: Optional[int] = None,
) -> QuerySet:
    """
    Shorthand for applying an OData query to a Django QuerySet.

    Args:
        queryset: Django QuerySet to apply the OData query to.
        odata_query: OData ``$filter`` expression.
        orderby: OData ``$orderby`` expression, e.g. ``"name, age desc"``. It
            takes precedence over any ordering already on ``queryset``,
            including the ``ordering`` of the model's ``Meta``, which then only
            break ties. ``NULL`` sorts first when ascending and
            last when descending.
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
        InvalidOrderByException: If ``orderby`` sorts on a collection or on
            something that is not a value.
    """
    validate_top_and_skip(top, skip)
    orderby_ast = parse_orderby(orderby) if orderby is not None else None

    lexer = ODataLexer()
    parser = ODataParser()
    model = queryset.model

    ast = parser.parse(lexer.tokenize(odata_query))
    transformer = AstToDjangoQVisitor(model)
    where_clause = transformer.visit(ast)
    ordering = transformer.visit(orderby_ast) if orderby_ast else []

    if transformer.queryset_annotations:
        queryset = queryset.annotate(**transformer.queryset_annotations)

    queryset = queryset.filter(where_clause)

    if ordering:
        # The OData ordering takes precedence, ordering that was already on the
        # queryset still breaks ties.
        query = queryset.query
        existing = query.order_by
        if not existing and query.default_ordering:
            existing = query.get_meta().ordering
        queryset = queryset.order_by(*ordering, *existing)

    if top is not None:
        return queryset[(skip or 0) : (skip or 0) + top]
    if skip is not None:
        return queryset[skip:]
    return queryset
