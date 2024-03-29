Using OData with SQLAlchemy
===========================

Basic Usage
-----------

The easiest way to add OData filtering to a SQLAlchemy query is with the shorthand:


SQLAlchemy ORM
^^^^^^^^^^^^^^

.. code-block:: python

    from odata_query.sqlalchemy import apply_odata_query

    orm_query = select(MyModel)  # This is any form of Query or Selectable.
    odata_query = "name eq 'test'"  # This will usually come from a query string parameter.

    query = apply_odata_query(orm_query, odata_query)
    results = session.execute(query).scalars().all()


SQLAlchemy Core
^^^^^^^^^^^^^^^

.. attention::

   Basic support for SQLAlchemy Core is new since version 0.7.0.
   It currently does not support relationship traversal or ``any``/``all``
   yet. Those operations will raise a ``NotImplementedException``.


.. code-block:: python

    from odata_query.sqlalchemy import apply_odata_core

    core_query = select(MyTable)  # This is any form of Query or Selectable.
    odata_query = "name eq 'test'"  # This will usually come from a query string parameter.

    query = apply_odata_query(core_query, odata_query)
    results = session.execute(query).scalars().all()


Advanced Usage
--------------

If you need some more flexibility or advanced features, the implementation of the
shorthand is a nice starting point: :py:mod:`odata_query.sqlalchemy.shorthand`

Let's break it down real quick:


Parsing the OData Query
^^^^^^^^^^^^^^^^^^^^^^^

.. include:: snippets/parsing.rst


Optional: Modifying the AST
^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. include:: snippets/modifying.rst


Building a Query Filter
^^^^^^^^^^^^^^^^^^^^^^^

To get from an :term:`AST` to something SQLAlchemy can use, you'll need to use the
:py:class:`odata_query.sqlalchemy.orm.AstToSqlAlchemyOrmVisitor` (ORM mode) or
the :py:class:`odata_query.sqlalchemy.core.AstToSqlAlchemyCoreVisitor` (Core
mode).
It needs to know about the 'root model' or table of your query in order to see
which fields exists and how objects are related.


SQLAlchemy ORM
""""""""""""""

.. code-block:: python

    from odata_query.sqlalchemy.orm import AstToSqlAlchemyOrmVisitor

    visitor = AstToSqlAlchemyOrmVisitor(MyModel)
    query_filter = visitor.visit(ast)

SQLAlchemy Core
"""""""""""""""

.. code-block:: python

    from odata_query.sqlalchemy.core import AstToSqlAlchemyCoreVisitor

    visitor = AstToSqlAlchemyCoreVisitor(MyTable)
    query_filter = visitor.visit(ast)


Optional: Joins
^^^^^^^^^^^^^^^

.. attention::

   Relationship traversal and automatic joins are not yet supported for
   SQLAlchemy Core mode.


If your query spans relationships, the ``AstToSqlAlchemyClauseVisitor`` will
generate join statements. For the query to work, these will need to be
applied explicitly:

.. code-block:: python

    for j in visitor.join_relationships:
        query = query.join(j)


Running the query
^^^^^^^^^^^^^^^^^

Finally, we're ready to run the query:

.. code-block:: python

    query = query.where(query_filter)
    results = s.execute(query).scalars().all()
