from unittest import mock

import pytest

from odata_query.sql import athena


@pytest.mark.parametrize(
    "input_id, expected_output, should_warn",
    [
        ("gorilla-pytest-gorilla-data", "gorilla_pytest_gorilla_data", False),
        ("__version_id", "__version_id", True),
        ("Half Hourly MPAN Table", "half_hourly_mpan_table", False),
    ],
)
@mock.patch.object(athena.log, "warning")
def test_clean_athena_identifier(
    mocked_warning, input_id: str, expected_output: str, should_warn: bool
):
    res = athena.clean_athena_identifier(input_id)

    assert res == expected_output

    if should_warn:
        mocked_warning.assert_called_once()
