OData-Query
===========

.. image:: https://readthedocs.org/projects/odata-query/badge/?version=latest
    :alt: Documentation Status
    :target: https://odata-query.readthedocs.io/en/latest/?badge=latest

.. image:: https://img.shields.io/badge/code%20style-black-000000.svg
    :alt: Code style: black
    :target: https://github.com/psf/black


``odata-query`` is a library that parses `OData v4`_ filter strings, and can
convert them to other forms such as `Django Queries`_, `SQLAlchemy Queries`_,
or just plain SQL.


Installation
------------

``odata-query`` is available on pypi, so can be installed with the package manager
of your choice:

.. code-block:: bash

    pip install odata-query
    # OR
    poetry add odata-query
    # OR
    pipenv install odata-query


The package defines the following optional ``extra``'s:

* ``django``: If you want to pin a compatible Django version.
* ``sqlalchemy``: If you want to pin a compatible SQLAlchemy version.


The following ``extra``'s relate to the development of this library:

- ``linting``: The linting and code style tools.
- ``testing``: Packages for running the tests.
- ``docs``: For building the project documentation.


You can install ``extra``'s by adding them between square brackets during
installation:

.. code-block:: bash

    pip install odata-query[sqlalchemy]


Quickstart
----------

The most common use case is probably parsing an OData query string, and applying
it to a query your ORM understands. For this purpose there is an all-in-one function:
``apply_odata_query``.

Example for Django:

.. code-block:: python

    from odata_query.django import apply_odata_query

    orm_query = MyModel.objects  # This can be a Manager or a QuerySet.
    odata_query = "name eq 'test'"  # This will usually come from a query string parameter.

    query = apply_odata_query(orm_query, odata_query)
    results = query.all()


Example for SQLAlchemy ORM:

.. code-block:: python

    from odata_query.sqlalchemy import apply_odata_query

    orm_query = select(MyModel)  # This is any form of Query or Selectable.
    odata_query = "name eq 'test'"  # This will usually come from a query string parameter.

    query = apply_odata_query(orm_query, odata_query)
    results = session.execute(query).scalars().all()

Example for SQLAlchemy Core:

.. code-block:: python

    from odata_query.sqlalchemy import apply_odata_core

    core_query = select(MyTable)  # This is any form of Query or Selectable.
    odata_query = "name eq 'test'"  # This will usually come from a query string parameter.

    query = apply_odata_core(core_query, odata_query)
    results = session.execute(query).scalars().all()

.. splitinclude-1

Advanced Usage
--------------

Not all use cases are as simple as that. Luckily, ``odata-query`` is modular
and extendable. See the `documentation`_ for advanced usage or extending the
library for other cases.

.. splitinclude-2

Contact
-------

Got any questions or ideas? We'd love to hear from you. Check out our
`contributing guidelines`_ for ways to offer feedback and
contribute.


License
-------

Copyright © `Gorillini NV`_.
All rights reserved.

Licensed under the MIT License.


.. _odata v4: https://www.odata.org/
.. _django queries: https://docs.djangoproject.com/en/3.2/topics/db/queries/
.. _sqlalchemy queries: https://docs.sqlalchemy.org/en/14/orm/loading_objects.html
.. _documentation: https://odata-query.readthedocs.io/en/latest
.. _Gorillini NV: https://gorilla.co/
.. _contributing guidelines: ./CONTRIBUTING.rst
