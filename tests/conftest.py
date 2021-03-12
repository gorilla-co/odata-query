import pytest

from odata_query.grammar import ODataLexer, ODataParser


@pytest.fixture(scope="session")
def lexer():
    return ODataLexer()


@pytest.fixture
def parser():
    return ODataParser()
