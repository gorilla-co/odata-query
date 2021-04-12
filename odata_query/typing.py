import logging
import operator
from typing import Optional, Tuple, Type, Union

from . import ast, exceptions as ex

log = logging.getLogger(__name__)


def typecheck(
    node: ast._Node, expected_type: Union[Type, Tuple[Type, ...]], field_name: str
):
    actual_type = infer_type(node)
    compare = operator.contains if isinstance(expected_type, tuple) else operator.eq
    if actual_type and not compare(expected_type, actual_type):
        allowed = (
            [t.__name__ for t in expected_type]
            if isinstance(expected_type, tuple)
            else expected_type.__name__
        )
        raise ex.ArgumentTypeException(
            f"Expected argument '{field_name}' to be of type {allowed}, got {actual_type.__name__}"
        )


def infer_type(node: ast._Node) -> Optional[Type[ast._Node]]:
    if isinstance(node, (ast._Literal)):
        return type(node)

    if isinstance(node, (ast.Compare, ast.BoolOp)):
        return ast.Boolean

    if isinstance(node, ast.Call):
        return infer_return_type(node)

    log.warning("Failed to infer type for %s", node)
    return None


def infer_return_type(node: ast.Call) -> Optional[Type[ast._Node]]:
    func = node.func.name

    if func in (
        "contains",
        "endswith",
        "startswith",
        "hassubset",
        "hassubsequence",
        "geo.intersects",
    ):
        return ast.Boolean

    if func in (
        "indexof",
        "length",
        "year",
        "month",
        "day",
        "hour",
        "minute",
        "second",
        "totaloffsetminutes",
    ):
        return ast.Integer

    if func in (
        "fractionalseconds",
        "totalseconds",
        "ceiling",
        "floor",
        "round",
        "geo.distance",
        "geo.length",
    ):
        return ast.Float

    if func in ("tolower", "toupper", "trim"):
        return ast.String

    if func == "date":
        return ast.Date

    if func in ("maxdatetime", "mindatetime", "now"):
        return ast.DateTime

    if func == "concat":
        return infer_type(node.args[0]) or infer_type(node.args[1])

    if func == "substring":
        return infer_type(node.args[0])

    return None
