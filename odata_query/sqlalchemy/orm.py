from typing import List, Type

from sqlalchemy.inspection import inspect
from sqlalchemy.orm.attributes import InstrumentedAttribute
from sqlalchemy.orm.decl_api import DeclarativeMeta
from sqlalchemy.orm.relationships import RelationshipProperty
from sqlalchemy.sql.expression import BinaryExpression, ClauseElement, ColumnClause

from odata_query import ast, exceptions as ex, utils, visitor

from . import common


class AstToSqlAlchemyOrmVisitor(common._CommonVisitors, visitor.NodeVisitor):
    """
    :class:`NodeVisitor` that transforms an :term:`AST` into a SQLAlchemy query
    filter clause using ORM features.

    Args:
        root_model: The root model of the query.
    """

    def __init__(self, root_model: Type[DeclarativeMeta]):
        self.root_model = root_model
        self.join_relationships: List[InstrumentedAttribute] = []

    def visit_Identifier(self, node: ast.Identifier) -> ColumnClause:
        ":meta private:"
        try:
            return getattr(self.root_model, node.name)
        except AttributeError:
            raise ex.InvalidFieldException(node.name)

    def visit_Attribute(self, node: ast.Attribute) -> ColumnClause:
        ":meta private:"
        rel_attr = self.visit(node.owner)
        # Owner is an InstrumentedAttribute, hopefully of a relationship.
        # But we need the model pointed to by the relationship.
        prop_inspect = inspect(rel_attr).property
        if not isinstance(prop_inspect, RelationshipProperty):
            # TODO: new exception:
            raise ValueError(f"Not a relationship: {node.owner}")
        self.join_relationships.append(rel_attr)

        # We'd like to reference the column on the related class:
        owner_cls = prop_inspect.entity.class_
        try:
            return getattr(owner_cls, node.attr)
        except AttributeError:
            raise ex.InvalidFieldException(node.attr)

    def visit_Compare(self, node: ast.Compare) -> BinaryExpression:
        ":meta private:"
        left = self.visit(node.left)
        right = self.visit(node.right)
        op = self.visit(node.comparator)

        # If a node is a `relationship` representing a single foreign key,
        # the client meant to compare the foreign key, not the related object.
        # E.g. In "blogpost/author eq 1", left should be "blogpost/author_id"
        left = self._maybe_sub_relationship_with_foreign_key(left)
        right = self._maybe_sub_relationship_with_foreign_key(right)

        return op(left, right)

    def visit_CollectionLambda(self, node: ast.CollectionLambda) -> ClauseElement:
        ":meta private:"
        owner_prop = self.visit(node.owner)
        collection_model = inspect(owner_prop).property.entity.class_

        if node.lambda_:
            # For the lambda, we want to strip the identifier off, because
            # we will execute this as a subquery in the wanted model's context.
            subq_ast = utils.expression_relative_to_identifier(
                node.lambda_.identifier, node.lambda_.expression
            )
            subq_transformer = self.__class__(collection_model)
            subquery_filter = subq_transformer.visit(subq_ast)
        else:
            subquery_filter = None

        if isinstance(node.operator, ast.Any):
            return owner_prop.any(subquery_filter)
        else:
            # For an ALL query, invert both the filter and the EXISTS:
            if node.lambda_:
                subquery_filter = ~subquery_filter
            return ~owner_prop.any(subquery_filter)

    def _maybe_sub_relationship_with_foreign_key(
        self, elem: ClauseElement
    ) -> ClauseElement:
        """
        If the given ClauseElement is a `relationship` with a single ForeignKey,
        replace it with the `ForeignKey` itself.

        :meta private:
        """
        try:
            prop_inspect = inspect(elem).property
            if isinstance(prop_inspect, RelationshipProperty):
                foreign_key = prop_inspect._calculated_foreign_keys
                if len(foreign_key) == 1:
                    return next(iter(foreign_key))
        except Exception:
            pass

        return elem
