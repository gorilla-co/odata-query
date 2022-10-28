Working with the AST
====================

Now that our :ref:`OData query has been parsed <ref-parsing-odata>` to an :term:`AST`,
how do we work with it?  `The Visitor Pattern`_ is a popular way to walk tree
structures such as :term:`AST`'s and modify or transform them to another
representation. ``odata-query`` contains the :ref:`ref-node-visitor` and
:ref:`ref-node-transformer` base classes that implement this pattern, as well
as some concrete implementations.


.. _ref-node-visitor:

NodeVisitor
-----------

A :py:class:`odata_query.visitor.NodeVisitor` is a class that walks an :term:`AST`
(depth-first by default) and calls a ``visit_{node_type}`` method on each
:py:class:`odata_query.ast._Node` it encounters. These methods can return whatever
they want, making this a very flexible pattern! If no ``visit_`` method is
implemented for the type of the node the visitor will continue with the node's
children if it has any, so you only need to implement what you explicitly need.
A simple :py:class:`odata_query.visitor.NodeVisitor` that counts comparison
expressions for example, might look like this:

.. code-block:: python

    class ComparisonCounter(NodeVisitor):
        def visit_Comparison(self, node: ast.Comparison) -> int:
            count_lhs = self.visit(node.left) or 0
            count_rhs = self.visit(node.right) or 0
            return 1 + count_lhs + count_rhs


    count = ComparisonCounter().visit(my_ast)


This isn't the most useful implementation... For some more realistic examples,
take a look at the :py:class:`odata_query.django.django_q.AstToDjangoQVisitor` or
the :py:class:`odata_query.sqlalchemy.orm.AstToSqlAlchemyOrmVisitor`
implementations. They transform an :term:`AST` to Django and SQLAlchemy ORM queries
respectively.


.. _ref-node-transformer:

NodeTransformer
---------------

A :py:class:`odata_query.visitor.NodeTransformer` is very similar to a
:ref:`ref-node-visitor`, with one difference: The ``visit_`` methods should return
an :py:class:`odata_query.ast._Node`, which will replace the node that is being
visited. This allows ``NodeTransformer``'s to modify the :term:`AST` while it's
being traversed. For example, the following
:py:class:`odata_query.visitor.NodeTransformer` would invert all 'less-than'
comparisons to 'greater-than' and vice-versa:


.. code-block:: python

    class ComparisonInverter(NodeTransformer):
        def visit_Comparison(self, node: ast.Comparison) -> ast.Comparison:
            if node.comparator == ast.Lt():
                new_comparator = ast.Gt()
            elif node.comparator == ast.Gt():
                new_comparator = ast.Lt()
            else:
                new_comparator = node.comparator

            return ast.Comparison(new_comparator, node.left, node.right)


    inverted = ComparisonInverter().visit(my_ast)


An interesting concrete implementation in ``odata-query`` is the
:py:class:`odata_query.rewrite.AliasRewriter`. This transformer looks for
aliases in identifiers and attributes, and replaces them with their full names.



Included Visitors
-----------------


.. autoclass:: odata_query.django.django_q.AstToDjangoQVisitor
.. autoclass:: odata_query.sqlalchemy.orm.AstToSqlAlchemyOrmVisitor
.. autoclass:: odata_query.sqlalchemy.core.AstToSqlAlchemyCoreVisitor
.. autoclass:: odata_query.rewrite.AliasRewriter
.. autoclass:: odata_query.roundtrip.AstToODataVisitor


.. _The Visitor Pattern: https://en.wikipedia.org/wiki/Visitor_pattern
