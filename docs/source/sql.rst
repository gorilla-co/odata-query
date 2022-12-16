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


Running the query
^^^^^^^^^^^^^^^^^

Finally, we're ready to run the query:

.. code-block:: python

    query = "SELECT * FROM my_table WHERE " + where_clause
    results = conn.execute(query).fetchall()


Supported dialects
^^^^^^^^^^^^^^^^^^

.. autoclass:: odata_query.sql.base.AstToSqlVisitor
.. autoclass:: odata_query.sql.sqlite.AstToSqliteSqlVisitor
.. autoclass:: odata_query.sql.athena.AstToAthenaSqlVisitor
