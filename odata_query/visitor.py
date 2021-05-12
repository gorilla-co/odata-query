from dataclasses import fields
from typing import Any, Iterator, Tuple

from . import ast


def iter_dataclass_fields(node: ast._Node) -> Iterator[Tuple[str, Any]]:
    """
    Loops over all fields of the given node, yielding the field's name and
    the current value.

    Yields:
        Tuples of ``(fieldname, value)`` for each field in ``node._fields``.
    """
    for field in fields(node):
        yield field.name, getattr(node, field.name)


class NodeVisitor:
    """
    Base class for visitors that walk the :term:`AST` and calls a visitor
    method for every node found. This method may return a value
    which is forwarded by the :func:`visit` method.

    This class is meant to be subclassed, with the subclass adding visitor
    methods.
    By default the visitor methods for the nodes are named ``'visit_'`` +
    class name of the node (e.g. ``visit_Identifier(self, identifier)``).
    If no visitor method exists for a node, the :func:`generic_visit` visitor is
    used instead.
    """

    def visit(self, node: ast._Node):
        """
        Looks for an explicit node visiting method on ``self``,
        otherwise calls :func:`generic_visit`.

        Returns:
            Whatever the called method returned. The user is free to choose what
            the :class:`NodeVisitor` should return.
        """
        method = "visit_" + node.__class__.__name__
        visitor = getattr(self, method, self.generic_visit)
        return visitor(node)

    def generic_visit(self, node: ast._Node):
        """
        Visits all fields on ``node`` recursively.
        Called if no explicit visitor method exists for a node.
        """
        for field, value in iter_dataclass_fields(node):
            if isinstance(value, list):
                for item in value:
                    if isinstance(item, ast._Node):
                        self.visit(item)
            elif isinstance(value, ast._Node):
                self.visit(value)


class NodeTransformer(NodeVisitor):
    """
    A subclass of :class:`NodeVisitor` that allows replacing of nodes in the
    :term:`AST` as it passes over it. The visitor methods should return instances
    of :class:`_Node` that replace the passed node.
    """

    def generic_visit(self, node: ast._Node) -> ast._Node:
        new_kwargs = {}

        for field, value in iter_dataclass_fields(node):
            if isinstance(value, list):
                new_val = []
                for item in value:
                    if isinstance(item, ast._Node):
                        new_val.append(self.visit(item))
                    else:
                        new_val.append(item)
            elif isinstance(value, ast._Node):
                new_val = self.visit(value)
            else:
                new_val = value

            new_kwargs[field] = new_val

        return type(node)(**new_kwargs)  # type: ignore
