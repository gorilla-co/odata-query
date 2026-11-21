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


Ordering and paging
^^^^^^^^^^^^^^^^^^^

The OData ``$orderby``, ``$top`` and ``$skip`` query options are keyword
arguments of both shorthands. They take the value of the option, without the
option name:

.. code-block:: python

    query = apply_odata_query(
        select(MyModel),
        "name eq 'test'",
        orderby="created_at desc, name",  # From the ``$orderby`` query parameter.
        top=10,  # From the ``$top`` query parameter, already converted to an ``int``.
        skip=20,  # From the ``$skip`` query parameter, already converted to an ``int``.
    )

``orderby`` takes precedence over any ordering that is already on the query,
which then only breaks ties. Paging is applied after filtering and ordering.
Without an ordering, the database does not guarantee a stable order between
pages, so make sure the query has one.

``NULL`` sorts first when ascending and last when descending, as OData
requires. See :doc:`deviations-and-extensions` for how that is done per
database.

You can order by properties of related entities that have one value (e.g.
``author/name``), which are outer joined so rows without one are kept.
Ordering by a collection (e.g. ``blogposts/title``) or by an entity instead of
a value raises an :py:class:`odata_query.exceptions.InvalidOrderByException`.

.. note::

   A filter over a collection (e.g. ``blogposts/title eq 'x'``) can return a
   root row once per match. Start from ``select(MyModel).distinct()`` to page
   over unique rows. Note that some databases, such as PostgreSQL, require the
   ``orderby`` of a ``DISTINCT`` query to only use selected columns, so it
   cannot order by a related entity then.


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


Optional: Ordering
^^^^^^^^^^^^^^^^^^

A ``$orderby`` value is parsed with :py:func:`odata_query.grammar.parse_orderby`.
The same visitor turns it into a list of ``ORDER BY`` items. Reuse the visitor
that built the filter, so that joins for both end up in
``visitor.join_relationships``:

.. code-block:: python

    from odata_query.grammar import parse_orderby

    ordering = visitor.visit(parse_orderby("name desc"))
    query = query.order_by(*ordering)

Relationships that are only used for ordering should be joined with
``query.outerjoin(j)`` instead of ``query.join(j)``, so that rows without a
related entity are kept.


Running the query
^^^^^^^^^^^^^^^^^

Finally, we're ready to run the query:

.. code-block:: python

    query = query.where(query_filter)
    results = s.execute(query).scalars().all()
