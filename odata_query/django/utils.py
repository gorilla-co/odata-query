from typing import Tuple, Type

from django.db.models import Model


def reverse_relationship(
    relationship_expr: str, root_model: Type[Model]
) -> Tuple[str, Type[Model]]:
    """
    Reverses a relationship expression relative to root_model.

    Args:
        relationship_expr: The Django relationship string, with underscores to
            represent relationship traversal.
        root_model: The model to which relationship_expr is relative.

    Returns:
        str: The django relationship string in reverse, so from the last joined
            relationship back to the root model.
        Type[Model]: The model to which the returned expression is relative.
    """
    relation_steps = relationship_expr.split("__")

    related_model = root_model
    path_to_outerref_parts = []
    for step in relation_steps:
        related_field = related_model._meta.get_field(step)
        related_model = related_field.related_model
        path_to_outerref_parts.append(related_field.remote_field.name)

    path_to_outerref = "__".join(reversed(path_to_outerref_parts))

    return (path_to_outerref, related_model)
