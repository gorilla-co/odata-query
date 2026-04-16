"""Tests for the DynamoDB backend (odata_query.dynamo).

Each test verifies that the generated boto3 ConditionBase:
  1. Is the correct type
  2. Uses the expected DynamoDB operator
  3. Carries the right operand values

OData syntax notes:
  - Use ``le`` / ``ge`` for ≤ / ≥  (OData standard, not ``lte`` / ``gte``)
  - ``not`` on a bare comparison needs parentheses: ``not (field eq val)``
  - String lists for IN / BETWEEN: ``('a', 'b')`` — single-item needs trailing
    comma: ``('a',)`` to distinguish from a paren-grouped expression.
"""

import pytest
from boto3.dynamodb.conditions import ConditionBase

from odata_query import exceptions
from odata_query.dynamo import apply_odata_query


def op(condition: ConditionBase) -> str:
    return condition.get_expression()["operator"]


def vals(condition: ConditionBase) -> tuple:
    return condition.get_expression()["values"]


class TestDynamoDBBackend:
    def test_basic_eq(self):
        cond = apply_odata_query("name eq 'Alice'")
        assert isinstance(cond, ConditionBase)
        assert op(cond) == "="

    def test_basic_ne(self):
        cond = apply_odata_query("name ne 'Alice'")
        assert op(cond) == "<>"

    def test_basic_lt(self):
        cond = apply_odata_query("age lt 18")
        assert op(cond) == "<"

    def test_basic_le(self):
        cond = apply_odata_query("age le 18")
        assert op(cond) == "<="

    def test_basic_gt(self):
        cond = apply_odata_query("age gt 18")
        assert op(cond) == ">"

    def test_basic_ge(self):
        cond = apply_odata_query("age ge 18")
        assert op(cond) == ">="

    def test_and_condition(self):
        cond = apply_odata_query("status eq 'active' and age gt 18")
        assert op(cond) == "AND"

    def test_or_condition(self):
        cond = apply_odata_query("status eq 'active' or status eq 'pending'")
        assert op(cond) == "OR"

    def test_not_condition(self):
        cond = apply_odata_query("not (status eq 'inactive')")
        assert op(cond) == "NOT"

    def test_eq_null(self):
        # 'field eq null' -> absent OR null-typed (covers both DynamoDB null states)
        cond = apply_odata_query("status eq null")
        assert op(cond) == "OR"
        assert op(vals(cond)[0]) == "attribute_not_exists"
        assert op(vals(cond)[1]) == "attribute_type"

    def test_ne_null(self):
        # 'field ne null' -> exists AND not null-typed
        cond = apply_odata_query("status ne null")
        assert op(cond) == "AND"
        assert op(vals(cond)[0]) == "attribute_exists"
        assert op(vals(cond)[1]) == "NOT"

    def test_exists_function(self):
        cond = apply_odata_query("field exists")
        assert op(cond) == "attribute_exists"

    def test_not_exists_function(self):
        cond = apply_odata_query("field not_exists")
        assert op(cond) == "attribute_not_exists"

    def test_contains_function(self):
        cond = apply_odata_query("contains(name, 'Jo')")
        assert op(cond) == "contains"

    def test_startswith_function(self):
        cond = apply_odata_query("startswith(name, 'Jo')")
        assert op(cond) == "begins_with"

    def test_in_operator(self):
        cond = apply_odata_query("status in ('active', 'pending')")
        assert op(cond) == "IN"

    def test_between_operator(self):
        cond = apply_odata_query("age between (18, 65)")
        assert op(cond) == "BETWEEN"

    def test_integer_value(self):
        cond = apply_odata_query("count eq 42")
        assert op(cond) == "="
        assert vals(cond)[1] == 42

    def test_float_value(self):
        cond = apply_odata_query("score ge 3.5")
        assert op(cond) == ">="
        assert vals(cond)[1] == 3.5

    def test_boolean_true(self):
        cond = apply_odata_query("active eq true")
        assert op(cond) == "="
        assert vals(cond)[1] is True

    def test_boolean_false(self):
        cond = apply_odata_query("active eq false")
        assert op(cond) == "="
        assert vals(cond)[1] is False

    def test_nested_and_or(self):
        cond = apply_odata_query(
            "(status eq 'active' or status eq 'pending') and age gt 18"
        )
        assert op(cond) == "AND"

    def test_field_with_dot_path(self):
        cond = apply_odata_query("address.city eq 'Denver'")
        assert op(cond) == "="
        assert vals(cond)[0].name == "address.city"

    def test_unsupported_function_raises(self):
        with pytest.raises(exceptions.UnsupportedFunctionException):
            apply_odata_query("endswith(name, 'son')")
