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


Running the query
^^^^^^^^^^^^^^^^^

Finally, we're ready to run the query:

.. code-block:: python

    results = queryset.filter(query_filter).all()


.. _queryset annotations: https://docs.djangoproject.com/en/3.2/ref/models/querysets/#annotate
