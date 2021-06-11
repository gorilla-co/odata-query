.. _ref-parsing-odata:

Parsing OData
=============

``odata-query`` includes a parser that tries to cover as much as possible of the `OData v4 filter spec`_.
This parser is built with `SLY`_ and consists of a :ref:`ref-lexer` and a :ref:`ref-parser`.


.. _ref-lexer:

Lexer
-----

The lexer's job is to take an OData query string and break it up into a series of
meaningful tokens, where each token has a type and a value. These are like the
words of a sentence. At this stage we're not looking at the structure of the
entire sentence yet, just if the individual words make sense.

The OData lexer this library uses is defined in :py:class:`odata_query.grammar.ODataLexer`. Here's
an example of what it does:

.. doctest::

   >>> from odata_query.grammar import ODataLexer
   >>> lexer = ODataLexer()
   >>> list(lexer.tokenize("name eq 'Hello World'"))
   [Token(type='ODATA_IDENTIFIER', value=Identifier(name='name'), lineno=1, index=0), Token(type='EQ', value=Eq(), lineno=1, index=4), Token(type='STRING', value=String(val='Hello World'), lineno=1, index=8)]



.. _ref-parser:

Parser
------

The parser's job is to take the tokens as produced by the :ref:`ref-lexer`
and find the language structure in them, according to the grammar rules defined
by the OData standard. In our case, the parser tries to build an :term:`AST` that
represents the entire query. This :term:`AST` is a tree structure that consists
of the nodes found in :py:mod:`odata_query.ast`.

As an example, the following OData query::

    name eq 'Hello World'

can be represented in the following :term:`AST`:

.. graphviz::

   digraph {
       "Compare()" -> "Identifier('name')" [label = "left"];
       "Compare()" -> "Eq()" [label = "comparator"];
       "Compare()" -> "String('Hello World')" [label = "right"];
   }


The OData parser this library uses is defined in :py:class:`odata_query.grammar.ODataParser`.
Here's an example of what it does:

.. doctest::

   >>> from odata_query.grammar import ODataParser
   >>> parser = ODataParser()
   >>> parser.parse(lexer.tokenize("name eq 'Hello World'"))
   Compare(comparator=Eq(), left=Identifier(name='name'), right=String(val='Hello World'))



.. _OData v4 filter spec: https://docs.oasis-open.org/odata/odata/v4.01/cs01/abnf/odata-abnf-construction-rules.txt
.. _SLY: https://github.com/dabeaz/sly

