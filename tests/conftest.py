from pathlib import Path

import pytest

from odata_query.grammar import ODataLexer, ODataParser


@pytest.fixture(scope="session")
def lexer():
    return ODataLexer()


@pytest.fixture
def parser():
    return ODataParser()


@pytest.fixture(scope="session")
def data_dir():
    data_dir_path = Path(__file__).parent / "data"
    data_dir_path.mkdir(exist_ok=True)

    return data_dir_path
