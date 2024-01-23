
Changelog
=========

All notable changes to this project will be documented in this file.

The format is based on `Keep a Changelog <https://keepachangelog.com/en/1.0.0/>`_\ ,
and this project adheres to `Semantic Versioning <https://semver.org/spec/v2.0.0.html>`_.


[0.10.0] - 2024-01-21
---------------------

Added
^^^^^

* Parser,Django: Added support for geo.{intersects, distance, length} functions.
* Python 3.11 coverage in test matrix.


[0.9.1] - 2023-11-15
--------------------

Fixed
^^^^^

* SQL: support function calls on right-hand side of `contains` node.


[0.9.0] - 2023-08-17
--------------------

Fixed
^^^^^

* SQLAlchemy functions defined by ``odata_query``

    - no longer clash with other functions defined in ``sqlalchemy.func`` with 
       the same name.
    - inherit cache to prevent SQLAlchemy performance warnings. 


[0.8.1] - 2023-02-17
--------------------

Fixed
^^^^^

* SQLAlchemy: Fix detection of pre-existing joins for legacy Query objects.


[0.8.0] - 2023-01-20
--------------------

Added
^^^^^

* SQL: Support for the SQLite dialect.

Changed
^^^^^^^

* SQL: Refactored SQL support

    - The ``AstToSqlVisitor`` now implements basic, standard SQL and functions
      as a base class for dialects.
    - The Athena dialect now lives in ``AstToAthenaSqlVisitor``.


[0.7.2] - 2022-12-19
--------------------

Fixed
^^^^^

* SQLAlchemy; Return a 1.x ``Query`` if a 1.x ``Query`` is passed in the shorthand.


[0.7.1] - 2022-12-16
--------------------

Fixed
^^^^^

* SQLAlchemy; Fix accidentally dropped support for 1.x style queries.


[0.7.0] - 2022-10-28
--------------------

Added
^^^^^

* A new visitor that roundtrips OData AST back to an OData query string.
* SQLAlchemy: Support for SQLAlchemy Core through a new visitor.


Changed
^^^^^^^

* Some lower-level SQLAlchemy related modules have been reorganized to
  facilitate SQLAlchemy Core support.


[0.6.0] - 2022-10-28
--------------------

Changed
^^^^^^^

* Django; Rework Django query transformer to use Django query nodes more.
  With the release of Django 4, we can now use ``Lookup``, ``Function``, and other
  Django query nodes in queries directly instead of relying on the keyworded
  syntax. For older Django versions, we can still transform those nodes to the
  keyworded syntax.
* Deps; Upgraded Sphinx and the ReadTheDocs theme.


Fixed
^^^^^

* Django; Support comparisons of boolean funcs to booleans
  (e.g. ``contains(a, 'b') eq true``)


[0.5.2] - 2022-03-14
--------------------

Changed
^^^^^^^

* Deps; Upgraded pytest.

Fixed
^^^^^

* SQLAlchemy; Fixed datetime extract functions.


[0.5.1] - 2022-02-28
--------------------

Fixed
^^^^^

* QA; Remove ``type:ignore`` from ``grammar.py`` and fix resulting type issues.


[0.5.0] - 2022-02-28
--------------------

Added
^^^^^

* Parser: Rudimentary OData namespace support.
* AST: Literal nodes now have a `py_val` getter that returns the closest Python
  approximation to the OData value.
* QA: Added full typing support.

Changed
^^^^^^^

* QA: Upgraded linting libraries.


[0.4.2] - 2021-12-19
--------------------

Added
^^^^^

* Docs: Include contribution guidelines and changelog in the main documentation.

Changed
^^^^^^^

* Docs: Use ReStructuredText instead of markdown where possible, for easier
  interaction with Sphinx.

Removed
^^^^^^^

* Docs: Removed the ``Myst`` dependency as we're no longer mixing markdown into
  our docs.
* Dev: Removed the ``moto`` and ``Faker`` dependencies as they weren't used.

[0.4.1] - 2021-07-16
--------------------

Added
^^^^^

* Added shorthands for the most common use cases: Applying an OData filter
  straight to a Django QuerySet or SQLAlchemy query.

Fixed
^^^^^

* Cleared warnings produced in SLY by wrong regex flag placement.

[0.4.0] - 2021-05-28
--------------------

Changed
^^^^^^^

* Raise a new ``InvalidFieldException`` if a field in a query doesn't exist.

Fixed
^^^^^

* Allow ``AliasRewriter`` to recurse into ``Attribute`` nodes, in order to replace
  nodes in the ``Attribute``\ 's ownership chain.

[0.3.0] - 2021-05-17
--------------------

Added
^^^^^

* Added ``NodeTransformers``\ , which are like ``NodeVisitors`` but replace visited
  nodes with the returned value.
* Initial API documentation.

Changed
^^^^^^^

* The AstTo{ORMQuery} visitors for SQLAlchemy and Django now have the same
  interface.
* AstToDjangoQVisitor now builds subqueries for ``any()/all()`` itself, instead
  of relying on ``SubQueryToken``\ s and a seperate visitor.
* Made all AST Nodes ``frozen`` (read-only), so they can be hashed.
* Replaced ``field_mapping`` on the ORM visitors with a more general
  ``AliasRewriter`` based on the new ``NodeTransformers``.
* Refactored ``IdentifierStripper`` to use the new ``NodeTransformers``.

[0.2.0] - 2021-05-05
--------------------

Added
^^^^^

* Transform OData queries to SQLAlchemy expressions with the new
  AstToSqlAlchemyClauseVisitor.

Changed
^^^^^^^

* Don't write a debugfile for the parser by default.

[0.1.0] - 2021-03-12
--------------------

Added
^^^^^

* Initial split to seperate package.
