Using OData with Django
=======================

Basic Usage
-----------

The easiest way to add OData filtering to a Django QuerySet is with the shorthand:

.. code-block:: python

    from odata_query.django import apply_odata_query

    orm_query = MyModel.objects  # This can be a Manager or a QuerySet.
    odata_query = "name eq 'test'"  # This will usually come from a query string parameter.

    query = apply_odata_query(orm_query, odata_query)
    results = query.all()


Ordering and paging
^^^^^^^^^^^^^^^^^^^

The OData ``$orderby``, ``$top`` and ``$skip`` query options are keyword
arguments of the shorthand. They take the value of the option, without the
option name:

.. code-block:: python

    queryset = apply_odata_query(
        MyModel.objects,
        "name eq 'test'",
        orderby="created_at desc, name",  # From the ``$orderby`` query parameter.
        top=10,  # From the ``$top`` query parameter, already converted to an ``int``.
        skip=20,  # From the ``$skip`` query parameter, already converted to an ``int``.
    )

``orderby`` takes precedence over any ordering that was set with
``order_by()`` on the queryset, which then only breaks ties.

``NULL`` sorts first when ascending and last when descending, as OData
requires.

You can order by properties of related entities that have one value (e.g.
``author/name``). Ordering by a collection (e.g. ``blogposts/title``) or by
an entity instead of a value raises an
:py:class:`odata_query.exceptions.InvalidOrderByException`.

.. note::

   With ``top`` or ``skip`` the result is a sliced queryset, which can no
   longer be filtered or made ``distinct()``. A filter over a collection (e.g.
   ``blogposts/title eq 'x'``) can return a row once per match, so pass in
   ``MyModel.objects.distinct()`` to page over unique rows.


Advanced Usage
--------------

If you need some more flexibility or advanced features, the implementation of the
shorthand is a nice starting point: :py:mod:`odata_query.django.shorthand`

Let's break it down real quick:


Parsing the OData Query
^^^^^^^^^^^^^^^^^^^^^^^

.. include:: snippets/parsing.rst


Optional: Modifying the AST
^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. include:: snippets/modifying.rst


Building a Query Filter
^^^^^^^^^^^^^^^^^^^^^^^

To get from an :term:`AST` to something Django can use, you'll need to use the
:py:class:`odata_query.django.django_q.AstToDjangoQVisitor`. It needs to know
about the 'root model' of your query in order to build relationships if necessary.
In most cases, this will be ``queryset.model``.


.. code-block:: python

    from odata_query.django.django_q import AstToDjangoQVisitor

    visitor = AstToDjangoQVisitor(MyModel)
    query_filter = visitor.visit(ast)


Optional: QuerySet Annotations
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

For some queries using advanced expressions, the ``AstToDjangoQVisitor`` will
generate `queryset annotations`_. For the query to work, these will need to be
applied:

.. code-block:: python

    if visitor.queryset_annotations:
        queryset = queryset.annotate(**visitor.queryset_annotations)


Optional: Ordering
^^^^^^^^^^^^^^^^^^

A ``$orderby`` value is parsed with :py:func:`odata_query.grammar.parse_orderby`.
The same visitor turns it into a list of Django ordering expressions:

.. code-block:: python

    from odata_query.grammar import parse_orderby

    ordering = visitor.visit(parse_orderby("name desc"))
    queryset = queryset.order_by(*ordering)

Visit it before applying the ``queryset_annotations`` above, as ordering by
an expression can add annotations too.


Running the query
^^^^^^^^^^^^^^^^^

Finally, we're ready to run the query:

.. code-block:: python

    results = queryset.filter(query_filter).all()


.. _queryset annotations: https://docs.djangoproject.com/en/3.2/ref/models/querysets/#annotate
