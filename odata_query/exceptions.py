import logging
import re

log = logging.getLogger(__name__)

COLUMN_NOT_FOUND = re.compile(r"Column '(\w+)' cannot be resolved")
DEFAULT_SYNTAX_ERR = re.compile(r"SYNTAX_ERROR:")


class ODataException(Exception):
    pass


class SyntaxError(ODataException):
    """Generic syntax error we can throw in our parser"""

    def __init__(self, token, eof: bool = False):
        self.token = token
        self.eof = eof


class ODataSyntaxException(ODataException):
    pass


class UnsupportedFunctionException(ODataException):
    pass


class FunctionCallException(ODataException):
    pass


class ArgumentTypeException(ODataException):
    def __init__(self, func: str = None, *args):
        if func:
            message = f"Unsupported or invalid type for function or operator '{func}'"
        else:
            message = "Invalid argument type for function or operator."
        super().__init__(message, *args)


class InvalidComparisonException(ODataException):
    pass


class InvalidUnaryOperandException(ODataException):
    pass


class InvalidBoolOperandException(ODataException):
    pass


class NoIdentifierInComparisonException(ODataException):
    pass


class ValueException(ODataException):
    def __init__(self, value, *args):
        message = f"Invalid value: {value}"
        super().__init__(message, *args)
