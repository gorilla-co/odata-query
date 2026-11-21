Using OData with raw SQL
========================

Using a raw SQL interface is slightly more involved and less powerful, but
offers a lot of flexibility in return.


Parsing the OData Query
^^^^^^^^^^^^^^^^^^^^^^^

.. include:: snippets/parsing.rst


Optional: Modifying the AST
^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. include:: snippets/modifying.rst


Building a Query Filter
^^^^^^^^^^^^^^^^^^^^^^^

To get from an :term:`AST` to a SQL clause, you'll need to use
:py:class:`odata_query.sql.base.AstToSqlVisitor` (standard SQL) or one of its
dialect-specific subclasses, such as
:py:class:`odata_query.sql.sqlite.AstToSqliteSqlVisitor` (SQLite).

.. code-block:: python

    from odata_query.sql import AstToSqlVisitor

    visitor = AstToSqlVisitor()
    where_clause = visitor.visit(ast)


Optional: Ordering and paging
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

A ``$orderby`` value is parsed with :py:func:`odata_query.grammar.parse_orderby`,
and the same visitor turns it into the items of an ``ORDER BY`` clause.
``$top`` and ``$skip`` are turned into the paging clause of the dialect, which
validates that both are non-negative integers:

.. code-block:: python

    from odata_query.grammar import parse_orderby

    order_by = visitor.visit(parse_orderby("name desc, age"))
    paging = visitor.paging_clause(top=10, skip=20)

``NULL`` sorts first when ascending and last when descending, as OData
requires. The standard visitor does so with ``NULLS FIRST``/``NULLS LAST``,
which databases such as MySQL and SQL Server do not support. They already
sort ``NULL`` that way by default, so for those, subclass the visitor and
override ``visit_OrderByItem`` to leave the suffix out, and ``paging_clause``
for their paging syntax. Ordering by properties of related entities is not
supported.


Running the query
^^^^^^^^^^^^^^^^^

Finally, we're ready to run the query:

.. code-block:: python

    query = f"SELECT * FROM my_table WHERE {where_clause} ORDER BY {order_by} {paging}"
    results = conn.execute(query).fetchall()

.. warning::

    The generated clause embeds values from the OData query as SQL literals,
    because the raw SQL backends cannot use bound parameters. Escaping is
    implemented for the characters that are special in standard SQL strings
    only. If your database treats other characters specially inside string
    literals (for example backslashes in MySQL), values may still break out of
    the literal. Prefer the :doc:`SQLAlchemy <sqlalchemy>` or
    :doc:`Django <django>` backends for untrusted input, as they use bound
    parameters. Otherwise, run the query with a read-only database user that
    can only reach the tables the filter is meant to query.


Supported dialects
^^^^^^^^^^^^^^^^^^

.. autoclass:: odata_query.sql.base.AstToSqlVisitor
.. autoclass:: odata_query.sql.sqlite.AstToSqliteSqlVisitor
.. autoclass:: odata_query.sql.athena.AstToAthenaSqlVisitor
