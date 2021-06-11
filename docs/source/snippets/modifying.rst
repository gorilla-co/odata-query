There are cases where you'll want to modify the query before executing it. That's
what :ref:`ref-node-transformer`'s are for!

One example might be that certain fields are exposed to end users under a different
name than the one in the database. In this case, the
:py:class:`odata_query.rewrite.AliasRewriter` will come in handy. Just pass it a
mapping of aliases to their full name and let it do its job:

.. code-block:: python

    from odata_query.rewrite import AliasRewriter

    rewriter = AliasRewriter({
        "name": "author/name",
    })
    new_ast = rewriter.visit(ast)

