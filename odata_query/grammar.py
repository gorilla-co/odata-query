# type: ignore
"""
Implementation of a subset of the
`OData formal grammar <https://docs.oasis-open.org/odata/odata/v4.01/csprd06/abnf/odata-abnf-construction-rules.txt>`_ .
Implemented with `SLY <https://sly.readthedocs.io/en/latest/>`_.
"""

from typing import List

from sly import Lexer, Parser

from . import ast, exceptions

_RWS = r"\s+"
_INTEGER = r"[+-]?\d+"
_DATE = r"[1-9]\d{3}-(?:0\d|1[0-2])-(?:[0-2]\d|3[01])"
_TIME = r"(?:[01]\d|2[0-3]):[0-5]\d(:?:[0-5]\d(?:\.\d{1,12})?)"

# Defines known functions and min/max nr of args:
ODATA_FUNCTIONS = {
    # String functions
    "concat": 2,
    "contains": 2,
    "endswith": 2,
    "indexof": 2,
    "length": 1,
    "startswith": 2,
    "substring": (2, 3),
    "matchesPattern": 2,
    "tolower": 1,
    "toupper": 1,
    "trim": 1,
    # Datetime functions
    "year": 1,
    "month": 1,
    "day": 1,
    "hour": 1,
    "minute": 1,
    "second": 1,
    "fractionalseconds": 1,
    "totalseconds": 1,
    "date": 1,
    "time": 1,
    "totaloffsetminutes": 1,
    "mindatetime": 0,
    "maxdatetime": 0,
    "now": 0,
    # Math functions
    "round": 1,
    "floor": 1,
    "ceiling": 1,
    # Geo functions
    "geo.distance": 1,
    "geo.length": 1,
    "geo.intersects": 2,
    # Set functions
    "hassubset": 2,
    "hassubsequence": 2,
}


class ODataLexer(Lexer):
    tokens = {
        ODATA_IDENTIFIER,
        NULL,
        STRING,
        GUID,
        DATETIME,
        DATE,
        TIME,
        DURATION,
        DECIMAL,
        INTEGER,
        BOOLEAN,
        ADD,
        SUB,
        MUL,
        DIV,
        MOD,
        UMINUS,
        AND,
        OR,
        NOT,
        EQ,
        NE,
        LT,
        LE,
        GT,
        GE,
        IN,
        ANY,
        ALL,
        WS,
    }
    literals = {"(", ")", ",", "/", ":"}

    def error(self, token):
        """
        Error handler during tokenization

        Args:
            token: The token that failed to tokenize.
        Raises:
            TokenizingException
        """
        raise exceptions.TokenizingException(text)

    # NOTE: Ordering of tokens is important! Longer tokens preferably first

    ####################################################################################
    # Primitive literals
    ####################################################################################

    @_(r"(?i)duration'[+-]?P(?:\d+D)?(?:T(?:\d+H)?(?:\d+M)?(?:\d+(?:\.\d+)?S)?)?'")
    def DURATION(self, t):
        ":meta private:"
        val = t.value.upper()

        # Strip the prefix and single quotes:
        val = val[len("DURATION") + 1 : -1]

        t.value = ast.Duration(val)
        return t

    @_(r"'(?:[^']|'')*'")
    def STRING(self, t):
        ":meta private:"
        # Strings are single-quoted. To represent a single quote within a string,
        # double it!

        # Strip only the first and last single quote:
        val = t.value[1:-1]
        # Replace double single-quotes with a single quote:
        val = val.replace("''", "'")

        t.value = ast.String(val)
        return t

    @_(r"(?i)[\da-f]{8}-[\da-f]{4}-[\da-f]{4}-[\da-f]{4}-[\da-f]{12}")
    def GUID(self, t):
        ":meta private:"
        t.value = ast.GUID(t.value)
        return t

    @_(_DATE + r"T" + _TIME + r"?(Z|[+-](?:[01]\d|2[0-3]):[0-5]\d)?")
    def DATETIME(self, t):
        ":meta private:"
        t.value = ast.DateTime(t.value)
        return t

    @_(_DATE)
    def DATE(self, t):
        ":meta private:"
        t.value = ast.Date(t.value)
        return t

    @_(_TIME)
    def TIME(self, t):
        ":meta private:"
        t.value = ast.Time(t.value)
        return t

    @_(_INTEGER + r"((?:(?:\.\d+)(?:e[-+]?\d+))|(?:\.\d+)|(?:e[-+]?\d+))")
    def DECIMAL(self, t):
        ":meta private:"
        t.value = ast.Float(t.value)
        return t

    @_(_INTEGER)
    def INTEGER(self, t):
        ":meta private:"
        t.value = ast.Integer(t.value)
        return t

    @_(r"true|false")
    def BOOLEAN(self, t):
        ":meta private:"
        t.value = ast.Boolean(t.value)
        return t

    @_(r"null")
    def NULL(self, t):
        ":meta private:"
        t.value = ast.Null()
        return t

    ####################################################################################
    # Arithmetic
    ####################################################################################
    @_(fr"(?i){_RWS}add{_RWS}")
    def ADD(self, t):
        ":meta private:"
        t.value = ast.Add()
        return t

    @_(fr"(?i){_RWS}sub{_RWS}")
    def SUB(self, t):
        ":meta private:"
        t.value = ast.Sub()
        return t

    @_(fr"(?i){_RWS}mul{_RWS}")
    def MUL(self, t):
        ":meta private:"
        t.value = ast.Mult()
        return t

    @_(fr"(?i){_RWS}div{_RWS}")
    def DIV(self, t):
        ":meta private:"
        t.value = ast.Div()
        return t

    @_(fr"(?i){_RWS}mod{_RWS}")
    def MOD(self, t):
        ":meta private:"
        t.value = ast.Mod()
        return t

    @_(r"-")
    def UMINUS(self, t):
        ":meta private:"
        t.value = ast.USub()
        return t

    ####################################################################################
    # Boolean logic
    ####################################################################################
    @_(fr"(?i){_RWS}and{_RWS}")
    def AND(self, t):
        ":meta private:"
        t.value = ast.And()
        return t

    @_(fr"(?i){_RWS}or{_RWS}")
    def OR(self, t):
        ":meta private:"
        t.value = ast.Or()
        return t

    @_(fr"(?i)not{_RWS}")
    def NOT(self, t):
        ":meta private:"
        t.value = ast.Not()
        return t

    ####################################################################################
    # Comparators
    ####################################################################################
    @_(fr"(?i){_RWS}eq{_RWS}")
    def EQ(self, t):
        ":meta private:"
        t.value = ast.Eq()
        return t

    @_(fr"(?i){_RWS}ne{_RWS}")
    def NE(self, t):
        ":meta private:"
        t.value = ast.NotEq()
        return t

    @_(fr"(?i){_RWS}lt{_RWS}")
    def LT(self, t):
        ":meta private:"
        t.value = ast.Lt()
        return t

    @_(fr"(?i){_RWS}le{_RWS}")
    def LE(self, t):
        ":meta private:"
        t.value = ast.LtE()
        return t

    @_(fr"(?i){_RWS}gt{_RWS}")
    def GT(self, t):
        ":meta private:"
        t.value = ast.Gt()
        return t

    @_(fr"(?i){_RWS}ge{_RWS}")
    def GE(self, t):
        ":meta private:"
        t.value = ast.GtE()
        return t

    @_(fr"(?i){_RWS}in{_RWS}")
    def IN(self, t):
        ":meta private:"
        t.value = ast.In()
        return t

    ####################################################################################
    # Collection operators
    ####################################################################################
    @_(r"(?i)any")
    def ANY(self, t):
        ":meta private:"
        t.value = ast.Any()
        return t

    @_(r"(?i)all")
    def ALL(self, t):
        ":meta private:"
        t.value = ast.All()
        return t

    ####################################################################################
    # Misc
    ####################################################################################
    @_(r"(?i)[_a-z]\w{0,127}")
    def ODATA_IDENTIFIER(self, t):
        ":meta private:"
        t.value = ast.Identifier(t.value)
        return t

    WS = _RWS


class ODataParser(Parser):
    debugfile = None
    tokens = ODataLexer.tokens

    # Predecence from low to high.
    # See: https://docs.oasis-open.org/odata/odata/v4.0/errata03/os/complete/part2-url-conventions/odata-v4.0-errata03-os-part2-url-conventions-complete.html#_Toc453752358
    # OData 5.1.1.14 Operator Precedence
    precedence = (
        ("left", OR),
        ("left", AND),
        ("left", EQ, NE),
        ("left", GT, GE, LT, LE),
        ("left", ADD, SUB),
        ("left", MUL, DIV, MOD),
        ("right", NOT, UMINUS),
        ("left", IN),
    )

    def error(self, token):
        """
        Error handler during parsing.

        Args:
            token: The token at which point parsing failed.
        Raises:
            ParsingFailedException
        """
        eof = token is None
        raise exceptions.ParsingException(token, eof)

    @_('"(" BWS common_expr BWS ")"')
    def common_expr(self, p):
        ":meta private:"
        return p.common_expr

    @_("primitive_literal", "first_member_expr", "list_expr")
    def common_expr(self, p):
        ":meta private:"
        return p[0]

    ####################################################################################
    # Primitives
    ####################################################################################
    @_(
        "NULL",
        "INTEGER",
        "DECIMAL",
        "STRING",
        "BOOLEAN",
        "GUID",
        "DATE",
        "TIME",
        "DATETIME",
        "DURATION",
    )
    def primitive_literal(self, p):
        ":meta private:"
        return p[0]

    @_('common_expr BWS "," BWS common_expr')
    def list_items(self, p):
        ":meta private:"
        return [p[0], p[4]]

    @_('list_items BWS "," BWS common_expr')
    def list_items(self, p):
        ":meta private:"
        p.list_items.append(p.common_expr)
        return p.list_items

    @_('"(" BWS common_expr BWS "," BWS ")"')
    def list_expr(self, p):
        ":meta private:"
        # NOTE: This is NOT according to the OData standard ABNF.
        # The standard says a single item list is (x), but that collides with the parenExpr
        # rule, e.g.: concat(('a'), ('b')) could mean concat of lists or concat of str expressions.
        # Therefore we follow Python syntax: a single item list has a comma at the end.
        return ast.List([p.common_expr])

    @_('"(" BWS list_items BWS ")"')
    def list_expr(self, p):
        ":meta private:"
        return ast.List(p.list_items)

    ####################################################################################
    # Names, properties, variables
    ####################################################################################

    # NOTE: !WARNING! OData ABNF has a lot of rules with very similar names
    # in this section. Like 'propertyPath' and 'propertyPathExpr', and their
    # definitions look almost exactly the same! Stay vigilant!

    @_("member_expr")
    def first_member_expr(self, p):
        ":meta private:"
        return p.member_expr

    @_("property_path_expr")
    def member_expr(self, p):
        ":meta private:"
        return p[0]

    @_("entity_navigation_property")
    def property_path_expr(self, p):
        ":meta private:"
        return p.entity_navigation_property

    @_("entity_navigation_property single_navigation_expr")
    def property_path_expr(self, p):
        ":meta private:"
        if isinstance(p[1], ast.Attribute):
            # We want to nest attributes in the opposite direction of parsing, e.g.:
            # we prefer Attribute(Attribute(Id(A), 'created_by'), 'name')
            # over      Attribute(Id(A), Attribute(Id(created_by), 'name'))
            naive_attr = ast.Attribute(p[0], p[1])
            return self._reverse_attributes(naive_attr)
        elif isinstance(p[1], ast.CollectionLambda):
            # Very similar for CollectionLambdas:
            # We prefer the CollectionLambda to define its complete owner
            # instead of being a deeply nested attribute:
            owner: ast.Identifier = p[1].owner
            new_owner = ast.Attribute(p[0], owner.name)
            return ast.CollectionLambda(new_owner, p[1].operator, p[1].lambda_)
        else:
            return ast.Attribute(p[0], p[1].name)

    @_("ODATA_IDENTIFIER")
    def entity_navigation_property(self, p):
        ":meta private:"
        return p[0]

    @_("'/' member_expr")
    def single_navigation_expr(self, p):
        ":meta private:"
        return p.member_expr

    @_("'/' any_expr", "'/' all_expr")
    def collection_path_expr(self, p):
        ":meta private:"
        return p[1]

    @_("entity_navigation_property collection_path_expr")
    def property_path_expr(self, p):
        ":meta private:"
        return ast.CollectionLambda(p[0], *p[1])

    ####################################################################################
    # Collections
    ####################################################################################
    @_('ODATA_IDENTIFIER BWS ":" BWS common_expr')
    def lambda_(self, p):
        ":meta private:"
        return ast.Lambda(p[0], p.common_expr)

    @_('ANY "(" BWS lambda_ BWS ")"')
    def any_expr(self, p):
        ":meta private:"
        return (p[0], p.lambda_)

    @_('ANY "(" BWS ")"')
    def any_expr(self, p):
        ":meta private:"
        return (p[0], None)

    @_('ALL "(" BWS lambda_ BWS ")"')
    def all_expr(self, p):
        ":meta private:"
        return (p[0], p.lambda_)

    ####################################################################################
    # Arithmetic
    ####################################################################################
    @_("UMINUS BWS common_expr")
    def common_expr(self, p):
        ":meta private:"
        return ast.UnaryOp(p[0], p[2])

    @_(
        "common_expr ADD common_expr",
        "common_expr SUB common_expr",
        "common_expr MUL common_expr",
        "common_expr DIV common_expr",
        "common_expr MOD common_expr",
    )
    def common_expr(self, p):
        ":meta private:"
        return ast.BinOp(p[1], p[0], p[2])

    ####################################################################################
    # Comparisons
    ####################################################################################
    @_(
        "common_expr EQ common_expr",
        "common_expr NE common_expr",
        "common_expr LT common_expr",
        "common_expr LE common_expr",
        "common_expr GT common_expr",
        "common_expr GE common_expr",
        "common_expr IN list_expr",
    )
    def common_expr(self, p):
        ":meta private:"
        return ast.Compare(p[1], p[0], p[2])

    ####################################################################################
    # Boolean logic
    ####################################################################################
    @_("common_expr AND common_expr", "common_expr OR common_expr")
    def common_expr(self, p):
        ":meta private:"
        return ast.BoolOp(p[1], p[0], p[2])

    @_("NOT common_expr")
    def common_expr(self, p):
        ":meta private:"
        return ast.UnaryOp(p[0], p.common_expr)

    ####################################################################################
    # Function calls
    ####################################################################################
    def _function_call(self, func: ast.Identifier, args: List[ast._Node]):
        ":meta private:"
        func_name = func.name
        try:
            n_args_exp = ODATA_FUNCTIONS[func_name]
        except KeyError:
            raise exceptions.UnknownFunctionException(func_name)

        n_args_given = len(args)
        if isinstance(n_args_exp, int) and n_args_given != n_args_exp:
            raise exceptions.ArgumentCountException(
                func_name, n_args_exp, n_args_exp, n_args_given
            )

        if isinstance(n_args_exp, tuple) and (
            n_args_given < n_args_exp[0] or n_args_given > n_args_exp[1]
        ):
            raise exceptions.ArgumentCountException(
                func_name, n_args_exp[0], n_args_exp[1], n_args_given
            )

        return ast.Call(func, args)

    @_('ODATA_IDENTIFIER "(" ")"')
    def common_expr(self, p):
        ":meta private:"
        args = []
        return self._function_call(p[0], args)

    @_('ODATA_IDENTIFIER "(" BWS common_expr BWS ")"')
    def common_expr(self, p):
        ":meta private:"
        args = [p.common_expr]
        return self._function_call(p[0], args)

    @_("ODATA_IDENTIFIER list_expr")
    def common_expr(self, p):
        ":meta private:"
        args = p[1].val
        return self._function_call(p[0], args)

    ####################################################################################
    # Misc
    ####################################################################################
    @_("")
    def empty(self, p):
        ":meta private:"
        pass

    @_("WS")
    def BWS(self, p):
        """
        'Bad Whitespace'

        :meta private:
        """
        pass

    @_("empty")
    def BWS(self, p):
        """
        'Bad Whitespace'

        :meta private:
        """
        pass

    ####################################################################################
    # Utils
    ####################################################################################
    def _reverse_attributes(self, attr: ast.Attribute) -> ast.Attribute:
        """
        Transforms an attribute like:
        ``Attribute(Id(A), Attribute(..., 'name'))``
        into
        ``Attribute(Attribute(Id(A), ...), 'name')``

        Args:
            attr: The :class:`Attribute` to reverse.
        Returns:
            The transformed attribute.
        """
        exploded = self._explode_attr(attr)
        leaf_attr = exploded.pop()
        owner = ast.Identifier(exploded.pop(0))
        for inter in exploded:
            owner = ast.Attribute(owner, inter)

        return ast.Attribute(owner, leaf_attr)

    def _explode_attr(self, attr: ast.Attribute) -> List[str]:
        """
        Splits a (possibly nested) attribute into a list of all elements, e.g.:
        ``Attribute(Id(A), Attribute(Id(B), 'name'))``
        into
        ``[A, B, name]``

        Args:
            attr: The :class:`Attribute` to split.
        Returns:
            A list of all identifiers in the ``attr``
        """
        if isinstance(attr.owner, ast.Identifier):
            exploded = [attr.owner.name]
        elif isinstance(attr.owner, ast.Attribute):
            exploded = self._explode_attr(attr.owner)
        else:
            raise NotImplementedError()

        if isinstance(attr.attr, str):
            exploded.append(attr.attr)
        elif isinstance(attr.attr, ast.Attribute):
            exploded.extend(self._explode_attr(attr.attr))
        else:
            raise NotImplementedError

        return exploded
