import datetime as dt
from uuid import UUID

import pytest

from odata_query import ast, exceptions
from odata_query.grammar import ODataLexer, ODataParser

_prev_starting_symbol = None


def parse(stmt: str, start_symbol: str = None):
    global _prev_starting_symbol
    lexer = ODataLexer()

    if start_symbol:
        ODataParser.start = start_symbol
    if start_symbol != _prev_starting_symbol:
        # Rebuild the grammar:
        ODataParser._build(list(ODataParser.__dict__.items()))
        _prev_starting_symbol = start_symbol

    parser = ODataParser()
    return parser.parse(lexer.tokenize(stmt))


@pytest.mark.parametrize(
    "value, expected_type",
    [
        ("12", ast.Integer),
        ("0", ast.Integer),
        ("-12", ast.Integer),
        ("1.0", ast.Float),
        ("-1.0", ast.Float),
        ("1e5", ast.Float),
        ("-1e5", ast.Float),
        ("1e-5", ast.Float),
        ("-1e-5", ast.Float),
        ("1.0e5", ast.Float),
        ("-1.0e5", ast.Float),
        ("-1.0e-5", ast.Float),
        ("1.123", ast.Float),
        ("-123.132", ast.Float),
        ("true", ast.Boolean),
        ("false", ast.Boolean),
        ("'p'", ast.String),
        ("'P'", ast.String),
        ("'t'", ast.String),
        ("'T'", ast.String),
        ("'pt'", ast.String),
        ("'pT'", ast.String),
        ("'PT'", ast.String),
        ("'Pt'", ast.String),
        ("'AB'", ast.String),
        ("'AB12'", ast.String),
        ("'123'", ast.String),
        ("'a_b_c'", ast.String),
        ("'a-b-c'", ast.String),
        ("'s p a c e'", ast.String),
        ("'\"inner_quote\"'", ast.String),
        ("1edbc3b3-3685-4a19-a7ed-eb562c198d96", ast.GUID),
        ("6047331A-6F47-42A4-87E0-7078A0A95062", ast.GUID),
        ("1999-12-31", ast.Date),
        ("2020-01-01", ast.Date),
        ("1999-12-31T00:00:00", ast.DateTime),
        ("1999-12-31T23:59:59", ast.DateTime),
    ],
)
def test_primitive_literal_parsing(value: str, expected_type: type):
    res = parse(value, "primitive_literal")

    assert isinstance(res, expected_type)


@pytest.mark.parametrize(
    "value, expected_unpacked",
    [
        ("duration'P12DT23H59M59.9S'", (None, None, None, "12", "23", "59", "59.9")),
        ("duration'-P12DT23H59M59.9S'", ("-", None, None, "12", "23", "59", "59.9")),
        ("duration'P12D'", (None, None, None, "12", None, None, None)),
        ("duration'-P12D'", ("-", None, None, "12", None, None, None)),
        ("duration'PT23H59M59.9S'", (None, None, None, None, "23", "59", "59.9")),
        ("duration'-PT23H59M59.9S'", ("-", None, None, None, "23", "59", "59.9")),
        ("duration'PT23H59M59.9S'", (None, None, None, None, "23", "59", "59.9")),
        ("duration'-PT23H59M59.9S'", ("-", None, None, None, "23", "59", "59.9")),
        ("duration'PT23H59M59S'", (None, None, None, None, "23", "59", "59")),
        ("duration'-PT23H59M59S'", ("-", None, None, None, "23", "59", "59")),
        ("duration'PT23H'", (None, None, None, None, "23", None, None)),
        ("duration'-PT23H'", ("-", None, None, None, "23", None, None)),
        ("duration'PT59M'", (None, None, None, None, None, "59", None)),
        ("duration'-PT59M'", ("-", None, None, None, None, "59", None)),
        ("duration'PT59S'", (None, None, None, None, None, None, "59")),
        ("duration'-PT59S'", ("-", None, None, None, None, None, "59")),
        ("duration'PT59.9S'", (None, None, None, None, None, None, "59.9")),
        ("duration'-PT59.9S'", ("-", None, None, None, None, None, "59.9")),
        ("duration'P12DT23H'", (None, None, None, "12", "23", None, None)),
        ("duration'-P12DT23H'", ("-", None, None, "12", "23", None, None)),
        ("duration'P12DT59M'", (None, None, None, "12", None, "59", None)),
        ("duration'-P12DT59M'", ("-", None, None, "12", None, "59", None)),
        ("duration'P12DT59S'", (None, None, None, "12", None, None, "59")),
        ("duration'-P12DT59S'", ("-", None, None, "12", None, None, "59")),
        ("duration'P12DT59.9S'", (None, None, None, "12", None, None, "59.9")),
        ("duration'-P12DT59.9S'", ("-", None, None, "12", None, None, "59.9")),
        ("duration'-P1Y'", ("-", "1", None, None, None, None, None)),
        ("duration'P1Y'", (None, "1", None, None, None, None, None)),
        ("duration'-P12M'", ("-", None, "12", None, None, None, None)),
        ("duration'P2Y3M'", (None, "2", "3", None, None, None, None)),
    ],
)
def test_duration_parsing(value: str, expected_unpacked: tuple):
    res = parse(value, "primitive_literal")

    assert isinstance(res, ast.Duration)
    assert res.unpack() == expected_unpacked


@pytest.mark.parametrize(
    "value, expected",
    [
        (
            "geography'SRID=0;Point(142.1 64.1)'",
            ast.Geography("SRID=0;Point(142.1 64.1)"),
        )
    ],
)
def test_geography_literal_parsing(value: str, expected: str):
    res = parse(value, "primitive_literal")

    assert isinstance(res, ast.Geography)
    assert res == expected


@pytest.mark.parametrize(
    "odata_val, exp_py_val",
    [
        ("null", None),
        ("12", 12),
        ("0", 0),
        ("-12", -12),
        ("1.0", 1.0),
        ("-1.0", -1.0),
        ("1e5", 1e5),
        ("-1e5", -1e5),
        ("1e-5", 1e-5),
        ("-1e-5", -1e-5),
        ("1.0e5", 1.0e5),
        ("-1.0e5", -1.0e5),
        ("-1.0e-5", -1.0e-5),
        ("1.123", 1.123),
        ("-123.132", -123.132),
        ("true", True),
        ("false", False),
        (
            "1edbc3b3-3685-4a19-a7ed-eb562c198d96",
            UUID("1edbc3b3-3685-4a19-a7ed-eb562c198d96"),
        ),
        (
            "6047331A-6F47-42A4-87E0-7078A0A95062",
            UUID("6047331A-6F47-42A4-87E0-7078A0A95062"),
        ),
        ("1999-12-31", dt.date(1999, 12, 31)),
        ("1999-12-31T00:00:00", dt.datetime(1999, 12, 31)),
        ("1999-12-31T23:59:59", dt.datetime(1999, 12, 31, 23, 59, 59)),
        ("14:00:00", dt.time(14)),
        ("(1, 2, 3)", [1, 2, 3]),
        ("(1.0, 2.0, 3.0)", [1.0, 2.0, 3.0]),
        ("(1, 2.0, '3')", [1, 2.0, "3"]),
        (
            "duration'P12DT23H59M59.9S'",
            dt.timedelta(days=12, hours=23, minutes=59, seconds=59.9),
        ),
        ("duration'P12D'", dt.timedelta(days=12)),
        ("duration'P1Y'", dt.timedelta(days=365.25)),  # Average including leap years
        ("duration'P1M'", dt.timedelta(days=30.44)),  # Average month length
        ("duration'P1M2D'", dt.timedelta(days=32.44)),
    ],
)
def test_python_value_of_literals(odata_val: str, exp_py_val):
    res = parse(odata_val, "common_expr")

    assert res.py_val == exp_py_val


@pytest.mark.parametrize(
    "value",
    [
        "(1, 2, 3)",
        "(1.0, 2.0, 3.0)",
        "(1, 2.0, '3')",
        "(1,2,3)",
        "( 1,2,3 )",
        "( 1, 2, 3 )",
        "( 1, )",
        "(1,)",
        "((1, 2), (3, 4))",
    ],
)
def test_list_parsing(value: str):
    res = parse(value, "list_expr")

    assert isinstance(res, ast.List)
    for item in res.val:
        assert isinstance(item, ast._Literal)


@pytest.mark.parametrize(
    "value, expected_type",
    [
        ("meter_id", ast.Identifier),
        ("nammespace.meter_id", ast.Identifier),
        ("multiple.namespace.meter_id", ast.Identifier),
        ("_id", ast.Identifier),
        ("_123", ast.Identifier),
        ("ab123", ast.Identifier),
        ("created_by/name", ast.Attribute),
        ("versioned_model/created_by/name", ast.Attribute),
        ("versioned_model/created_by/boss/name", ast.Attribute),
    ],
)
def test_member_expression_parsing(value: str, expected_type: type):
    res = parse(value, "member_expr")

    assert isinstance(res, expected_type)


@pytest.mark.parametrize(
    "expression, expected_ast",
    [
        (
            "meter_id eq '1'",
            ast.Compare(ast.Eq(), ast.Identifier("meter_id"), ast.String("1")),
        ),
        (
            "namespace.meter_id eq 1",
            ast.Compare(
                ast.Eq(), ast.Identifier("meter_id", ("namespace",)), ast.Integer("1")
            ),
        ),
        (
            "ns1.ns2.meter_id eq 1",
            ast.Compare(
                ast.Eq(),
                ast.Identifier(
                    "meter_id",
                    ("ns1", "ns2"),
                ),
                ast.Integer("1"),
            ),
        ),
        (
            "meter_id eq 'o''reilly'''",
            ast.Compare(ast.Eq(), ast.Identifier("meter_id"), ast.String("o'reilly'")),
        ),
        (
            "eac ge 123.456",
            ast.Compare(ast.GtE(), ast.Identifier("eac"), ast.Float("123.456")),
        ),
        (
            "meter_id in ('1', '2', '3')",
            ast.Compare(
                ast.In(),
                ast.Identifier("meter_id"),
                ast.List([ast.String("1"), ast.String("2"), ast.String("3")]),
            ),
        ),
        (
            "not meter_id in ('1', '2', '3')",
            ast.UnaryOp(
                ast.Not(),
                ast.Compare(
                    ast.In(),
                    ast.Identifier("meter_id"),
                    ast.List([ast.String("1"), ast.String("2"), ast.String("3")]),
                ),
            ),
        ),
        (
            "period_start ge 2019-01-01",
            ast.Compare(
                ast.GtE(), ast.Identifier("period_start"), ast.Date("2019-01-01")
            ),
        ),
        (
            "daily_metered eq true",
            ast.Compare(ast.Eq(), ast.Identifier("daily_metered"), ast.Boolean("true")),
        ),
        (
            "eac gt 123.12 and eac lt 321.32",
            ast.BoolOp(
                ast.And(),
                ast.Compare(ast.Gt(), ast.Identifier("eac"), ast.Float("123.12")),
                ast.Compare(ast.Lt(), ast.Identifier("eac"), ast.Float("321.32")),
            ),
        ),
        (
            "meter_id eq '1' or meter_id eq '2' or meter_id eq '3'",
            ast.BoolOp(
                ast.Or(),
                ast.BoolOp(
                    ast.Or(),
                    ast.Compare(ast.Eq(), ast.Identifier("meter_id"), ast.String("1")),
                    ast.Compare(ast.Eq(), ast.Identifier("meter_id"), ast.String("2")),
                ),
                ast.Compare(ast.Eq(), ast.Identifier("meter_id"), ast.String("3")),
            ),
        ),
        (
            "meter_id eq '1' OR (meter_id eq '2' AND eac ge 100)",
            ast.BoolOp(
                ast.Or(),
                ast.Compare(ast.Eq(), ast.Identifier("meter_id"), ast.String("1")),
                ast.BoolOp(
                    ast.And(),
                    ast.Compare(ast.Eq(), ast.Identifier("meter_id"), ast.String("2")),
                    ast.Compare(ast.GtE(), ast.Identifier("eac"), ast.Integer("100")),
                ),
            ),
        ),
        (
            "meter_id in ('1',)",
            ast.Compare(
                ast.In(), ast.Identifier("meter_id"), ast.List([ast.String("1")])
            ),
        ),
        (
            "created_by/name eq 'Ruben'",
            ast.Compare(
                ast.Eq(),
                ast.Attribute(ast.Identifier("created_by"), "name"),
                ast.String("Ruben"),
            ),
        ),
        (
            "versioned_model/created_by/company/name eq 'Gorilla'",
            ast.Compare(
                ast.Eq(),
                ast.Attribute(
                    ast.Attribute(
                        ast.Attribute(ast.Identifier("versioned_model"), "created_by"),
                        "company",
                    ),
                    "name",
                ),
                ast.String("Gorilla"),
            ),
        ),
        (
            "custom_fields/any()",
            ast.CollectionLambda(ast.Identifier("custom_fields"), ast.Any(), None),
        ),
        (
            "custom_fields/any(f:f/name eq 'Market')",
            ast.CollectionLambda(
                ast.Identifier("custom_fields"),
                ast.Any(),
                ast.Lambda(
                    ast.Identifier("f"),
                    ast.Compare(
                        ast.Eq(),
                        ast.Attribute(ast.Identifier("f"), "name"),
                        ast.String("Market"),
                    ),
                ),
            ),
        ),
        (
            "model/custom_fields/any(f:f/name eq 'Market')",
            ast.CollectionLambda(
                ast.Attribute(ast.Identifier("model"), "custom_fields"),
                ast.Any(),
                ast.Lambda(
                    ast.Identifier("f"),
                    ast.Compare(
                        ast.Eq(),
                        ast.Attribute(ast.Identifier("f"), "name"),
                        ast.String("Market"),
                    ),
                ),
            ),
        ),
        (
            "custom_fields/any() and custom_fields/all(cf: cf/value gt 5)",
            ast.BoolOp(
                ast.And(),
                ast.CollectionLambda(ast.Identifier("custom_fields"), ast.Any(), None),
                ast.CollectionLambda(
                    ast.Identifier("custom_fields"),
                    ast.All(),
                    ast.Lambda(
                        ast.Identifier("cf"),
                        ast.Compare(
                            ast.Gt(),
                            ast.Attribute(ast.Identifier("cf"), "value"),
                            ast.Integer("5"),
                        ),
                    ),
                ),
            ),
        ),
    ],
)
def test_bool_common_expr(expression: str, expected_ast: ast._Node):
    res = parse(expression, "common_expr")

    assert res == expected_ast


@pytest.mark.parametrize(
    "expression, expected_ast",
    [
        (
            "1 add 2 add 3",
            ast.BinOp(
                ast.Add(),
                ast.BinOp(ast.Add(), ast.Integer("1"), ast.Integer("2")),
                ast.Integer("3"),
            ),
        ),
        (
            "1 add 2 mul 3 sub 4",
            ast.BinOp(
                ast.Sub(),
                ast.BinOp(
                    ast.Add(),
                    ast.Integer("1"),
                    ast.BinOp(ast.Mult(), ast.Integer("2"), ast.Integer("3")),
                ),
                ast.Integer("4"),
            ),
        ),
        (
            "1 div - 1",
            ast.BinOp(
                ast.Div(),
                ast.Integer("1"),
                ast.UnaryOp(ast.USub(), ast.Integer("1")),
            ),
        ),
        ("now()", ast.Call(ast.Identifier("now"), [])),
        (
            "year(now())",
            ast.Call(ast.Identifier("year"), [ast.Call(ast.Identifier("now"), [])]),
        ),
        (
            "concat('abc', 'def')",
            ast.Call(ast.Identifier("concat"), [ast.String("abc"), ast.String("def")]),
        ),
        (
            "geo.distance(home,geography'SRID=0;Point(142.1 64.1)')",
            ast.Call(
                ast.Identifier("distance", namespace=("geo",)),
                [ast.Identifier("home"), ast.Geography("SRID=0;Point(142.1 64.1)")],
            ),
        ),
    ],
)
def test_common_expr(expression: str, expected_ast):
    res = parse(expression, "common_expr")

    assert res == expected_ast


@pytest.mark.parametrize(
    "func_call, expected_exception",
    [
        ("doesnotexist()", exceptions.UnknownFunctionException),
        ("now ()", exceptions.ParsingException),
        ("now('abc')", exceptions.ArgumentCountException),
        ("substring('abc')", exceptions.ArgumentCountException),
        ("substring('abc', 'def', 'ghi', 'jkl')", exceptions.ArgumentCountException),
    ],
)
def test_bad_function_calls(func_call: str, expected_exception):
    with pytest.raises(expected_exception):
        parse(func_call, "common_expr")


def test_lexer_error():
    lexer = ODataLexer()

    with pytest.raises(exceptions.TokenizingException):
        list(lexer.tokenize("<>%&#@"))
