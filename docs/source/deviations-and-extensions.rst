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


.. _spec: https://www.odata.org/documentation/
