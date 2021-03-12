import logging
from typing import Optional

from . import ast

log = logging.getLogger(__name__)


def infer_type(node: ast._Node) -> Optional[type]:
    if isinstance(node, (ast._Literal)):
        return type(node)

    if isinstance(node, (ast.Compare, ast.BoolOp)):
        return ast.Boolean

    if isinstance(node, ast.Call):
        return infer_return_type(node)

    log.warning("Failed to infer type for %s", node)
    return None


def infer_return_type(node: ast.Call) -> Optional[type]:
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
