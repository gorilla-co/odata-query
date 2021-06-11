To get from a string representing an OData query to a usable representation,
we need to tokenize and parse it as follows:

.. code-block:: python

    from odata_query.grammar import ODataParser, ODataLexer

    lexer = ODataLexer()
    parser = ODataParser()
    ast = parser.parse(lexer.tokenize(my_odata_query))

This process is described in more detail in :ref:`ref-parsing-odata`.
