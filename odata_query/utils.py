from typing import Any

from . import ast, exceptions
from .rewrite import IdentifierStripper


def expression_relative_to_identifier(
    identifier: ast.Identifier, expression: ast._Node
) -> ast._Node:
    """
    Shorthand for the :class:`IdentifierStripper`.

    Args:
        identifier: Identifier to strip from ``expression``.
        expression: Expression to strip the ``identifier`` from.

    Returns:
        The ``expression`` relative to the ``identifier``.
    """
    stripper = IdentifierStripper(identifier)
    result = stripper.visit(expression)
    return result


def validate_top_and_skip(top: Any, skip: Any) -> None:
    """
    Validate the ``top`` and ``skip`` query options, which must be either
    ``None`` or a non-negative integer.

    Raises:
        InvalidQueryOptionException: If one of them is anything else.
    """
    for option_name, value in (("top", top), ("skip", skip)):
        if value is None:
            continue
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise exceptions.InvalidQueryOptionException(option_name, value)
