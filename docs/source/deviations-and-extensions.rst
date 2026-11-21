Deviations and Extensions to the OData Spec
===========================================

There are some minor cases where this library deviates from the official `spec`_, 
e.g. when the spec is ambiguous, or to add extra non-breaking functionality.


Lists with a single item need a trailing comma
----------------------------------------------

This library needs a trailing comma to represent a list with a single item, 
whereas the spec does not describe this trailing comma (e.g.
``(item,)`` instead of ``(item)``). 

The reason is that the spec doesn't seem to differentiate between a list of a
single item and any other parenthesized expression. This can lead to parsing 
conflicts. Consider the following expression:

.. code-block::
	
	concat(('a'), ('b'))


The grammar in the official spec could parse this as either:

* Concatenate 2 lists, the first one containing the single string 'a', the second 
  one containing the single string 'b'. The result would be ``('a', 'b')``.
* Concatenate 2 expressions in parentheses. The first one is the string literal
  'a', the second one the string literal 'b'. The result would be ``'ab'``


To make this difference explicit, this library requires a trailing comma to 
signify a list. The same behavior is present in Python:

>>> ("a")
'a'
>>> ("a",)
('a',)

.. >>> from odata_query.grammar import ODataLexer, ODataParser
.. >>> lexer = ODataLexer()
.. >>> parser = ODataParser()
>>> parser.parse(lexer.tokenize("('a')"))
String(val='a')
>>> parser.parse(lexer.tokenize("('a',)"))
List(val=[String(val='a')])


Durations expressed in years and months
---------------------------------------

The official `spec`_ defines a duration with a number of days, hours, minutes,
and seconds. E.g. ``duration'P1DT2H'`` is a duration of 1 **D**\ ay and 2 **H**\ ours.

This library adds the ability to express durations containing **Y**\ ears and 
**M**\ onths. E.g. ``duration'P1Y2M3DT4H'`` would express a duration of 1 **Y**\ ear,
2 **M**\ onths, 3 **D**\ ays, and 4 **H**\ ours.

It's important to note that the final internal value is still expressed in days,
based on average durations.
Thus, a month simply represents 30.44 days, while a year represents 365.25 days.


Ordering and paging are keyword arguments
-----------------------------------------

The OData ``$orderby``, ``$top`` and ``$skip`` system query options are not
parsed from a query string. The shorthands take them as the keyword arguments
``orderby``, ``top`` and ``skip``, so applications can use the query string
parsing of their web framework. ``top`` and ``skip`` must be non-negative
integers, and ``skip`` is applied before ``top`` as the spec requires.

Other system query options, such as ``$count``, ``$select`` and ``$expand``,
are not supported yet.


Ordering is limited to values
-----------------------------

The spec allows ``$orderby`` to sort on any expression, including the count of
a collection (``$orderby=Products/$count``). This library supports expressions
that the ``$filter`` supports, with one restriction: they cannot refer to a
collection, or to an entity instead of one of its properties. Those raise an
``InvalidOrderByException``. A collection would repeat the rows of the root
entity, and an entity has no order of its own.

In SQL, ordering by properties of a related entity is only supported by the
SQLAlchemy ORM and Django backends.

The ``asc`` and ``desc`` keywords are case-insensitive, and whitespace around
the commas of the list is accepted, which is more lenient than the ABNF.


Where NULL sorts
----------------

The spec says ``NULL`` sorts before any value when ascending, and after any
value when descending. Databases disagree on their defaults, so the backends
make it explicit where the database needs it:

* SQLAlchemy emits ``NULLS FIRST``/``NULLS LAST`` for every dialect except
  SQLite, MySQL, MariaDB and SQL Server, which sort ``NULL`` that way already
  and get no suffix. The suffix is also left out for columns that cannot be
  ``NULL``, so databases can use an index.
* Django uses ``nulls_first``/``nulls_last``, which Django emulates for
  databases that do not support them. It skips fields of the root model that
  cannot be ``NULL``.
* The standard SQL visitor emits ``NULLS FIRST``/``NULLS LAST``, as does the
  Athena visitor. The SQLite visitor emits nothing. Other databases may need a
  subclass, see :doc:`sql`.

Ordering by a boolean expression, such as ``price gt 5``, sorts ``false``
before ``true`` as the spec says, but needs a database that accepts a predicate
in ``ORDER BY``. PostgreSQL, SQLite and MySQL do, SQL Server and Oracle do not.


.. _spec: https://www.odata.org/documentation/
