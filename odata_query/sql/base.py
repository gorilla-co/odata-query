import logging
from typing import Optional

from odata_query import ast, exceptions, typing, visitor

log = logging.getLogger(__name__)


class AstToSqlVisitor(visitor.NodeVisitor):
    """
    :class:`NodeVisitor` that transforms an :term:`AST` into a SQL ``WHERE``
    clause. Based on SQL-99 as described here: https://crate.io/docs/sql-99/en/latest/

    Args:
        table_alias: Optional alias for the root table.
    """

    def __init__(self, table_alias: Optional[str] = None):
        super().__init__()
        self.table_alias = table_alias

    def visit_Identifier(self, node: ast.Identifier) -> str:
        ":meta private:"
        # Double quotes for column names acc SQL Standard
        sql_id = f'"{node.name}"'

        if self.table_alias:
            sql_id = f'"{self.table_alias}".' + sql_id

        return sql_id

    def visit_Null(self, node: ast.Null) -> str:
        ":meta private:"
        return "NULL"

    def visit_Integer(self, node: ast.Integer) -> str:
        ":meta private:"
        return node.val

    def visit_Float(self, node: ast.Float) -> str:
        ":meta private:"
        return node.val

    def visit_Boolean(self, node: ast.Boolean) -> str:
        ":meta private:"
        return node.val.upper()

    def visit_String(self, node: ast.String) -> str:
        ":meta private:"
        # Replace single quotes with double single-quotes acc SQL standard:
        val = node.val.replace("'", "''")
        # Wrap in single quotes for string constants acc SQL Standard
        return f"'{val}'"

    def visit_Date(self, node: ast.Date) -> str:
        ":meta private:"
        # Single quotes for date constants acc SQL Standard
        return f"DATE '{node.val}'"

    def visit_DateTime(self, node: ast.DateTime) -> str:
        ":meta private:"
        sql_ts = node.val.replace("T", " ")
        # Single quotes for datetime constants acc SQL Standard
        return f"TIMESTAMP '{sql_ts}'"

    def visit_Duration(self, node: ast.Duration) -> str:
        ":meta private:"
        sign, years, months, days, hours, minutes, seconds = node.unpack()

        sign = sign or ""
        intervals = []
        if years:
            intervals.append(f"INTERVAL '{years}' YEAR")
        if months:
            intervals.append(f"INTERVAL '{months}' MONTH")
        if days:
            intervals.append(f"INTERVAL '{days}' DAY")
        if hours:
            intervals.append(f"INTERVAL '{hours}' HOUR")
        if minutes:
            intervals.append(f"INTERVAL '{minutes}' MINUTE")
        if seconds:
            intervals.append(f"INTERVAL '{seconds}' SECOND")

        if len(intervals) == 0:
            # Shouldn't occur but whatever
            return ""
        if len(intervals) == 1:
            return f"{sign}{intervals[0]}"
        if len(intervals) > 1:
            interval = " + ".join(intervals)
            return f"{sign}({interval})"

        # Make Quality checks happy:
        raise Exception("This code is never reachable...")

    def visit_GUID(self, node: ast.GUID) -> str:
        ":meta private:"
        return f"'{node.val}'"

    def visit_List(self, node: ast.List) -> str:
        ":meta private:"
        options = ", ".join(self.visit(n) for n in node.val)
        return f"({options})"

    def visit_Add(self, node: ast.Add) -> str:
        ":meta private:"
        return "+"

    def visit_Sub(self, node: ast.Sub) -> str:
        ":meta private:"
        return "-"

    def visit_Mult(self, node: ast.Mult) -> str:
        ":meta private:"
        return "*"

    def visit_Div(self, node: ast.Div) -> str:
        ":meta private:"
        return "/"

    def visit_Mod(self, node: ast.Mod) -> str:
        ":meta private:"
        return "%"

    def visit_BinOp(self, node: ast.BinOp) -> str:
        ":meta private:"
        left = self.visit(node.left)
        right = self.visit(node.right)
        op = self.visit(node.op)

        return f"{left} {op} {right}"

    def visit_Eq(self, node: ast.Eq) -> str:
        ":meta private:"
        return "="

    def visit_NotEq(self, node: ast.NotEq) -> str:
        ":meta private:"
        return "!="

    def visit_Lt(self, node: ast.Lt) -> str:
        ":meta private:"
        return "<"

    def visit_LtE(self, node: ast.LtE) -> str:
        ":meta private:"
        return "<="

    def visit_Gt(self, node: ast.Gt) -> str:
        ":meta private:"
        return ">"

    def visit_GtE(self, node: ast.GtE) -> str:
        ":meta private:"
        return ">="

    def visit_In(self, node: ast.In) -> str:
        ":meta private:"
        return "IN"

    def visit_Compare(self, node: ast.Compare) -> str:
        ":meta private:"
        left = self.visit(node.left)
        right = self.visit(node.right)
        comparator = self.visit(node.comparator)

        # In case of a subexpression, wrap it in parentheses
        if isinstance(node.left, (ast.BoolOp, ast.Compare)):
            left = f"({left})"
        if isinstance(node.right, (ast.BoolOp, ast.Compare)):
            right = f"({right})"

        #  'eq/ne null' should become 'IS (NOT) NULL' instead of '(!)= NULL'
        if isinstance(node.right, ast.Null):
            if isinstance(node.comparator, ast.Eq):
                comparator = "IS"
            elif isinstance(node.comparator, ast.NotEq):
                comparator = "IS NOT"

        return f"{left} {comparator} {right}"

    def visit_And(self, node: ast.And) -> str:
        ":meta private:"
        return "AND"

    def visit_Or(self, node: ast.Or) -> str:
        ":meta private:"
        return "OR"

    def visit_BoolOp(self, node: ast.BoolOp) -> str:
        ":meta private:"
        left = self.visit(node.left)
        op = self.visit(node.op)
        right = self.visit(node.right)

        # In case of a subexpression, wrap it in parentheses
        # UNLESS it has the same operator as the current BoolOp, e.g.:
        # x AND y AND z
        if isinstance(node.left, ast.BoolOp) and node.left.op != node.op:
            left = f"({left})"
        if isinstance(node.right, ast.BoolOp) and node.right.op != node.op:
            right = f"({right})"

        return f"{left} {op} {right}"

    def visit_Not(self, node: ast.Not) -> str:
        ":meta private:"
        return "NOT"

    def visit_UnaryOp(self, node: ast.UnaryOp) -> str:
        ":meta private:"
        op = self.visit(node.op)
        operand = self.visit(node.operand)

        # In case of a subexpression, wrap it in parentheses
        if isinstance(node.operand, ast.BoolOp):
            operand = f"({operand})"

        return f"{op} {operand}"

    def visit_Call(self, node: ast.Call) -> str:
        ":meta private:"
        try:
            # Grammar has already validated that the function is valid OData,
            # but that doesn't guarantee we can represent it in SQL:
            sql_gen = getattr(self, "sqlfunc_" + node.func.name.lower())
        except AttributeError:
            raise exceptions.UnsupportedFunctionException(node.func.name)

        return sql_gen(*node.args)

    def sqlfunc_concat(self, *args: ast._Node) -> str:
        ":meta private:"
        args_sql = [self.visit(arg) for arg in args]
        return f"{args_sql[0]} || {args_sql[1]}"

    def _to_pattern(self, arg: ast._Node, prefix: str = "", suffix: str = "") -> str:
        """
        Transform a node into a pattern usable in `LIKE` clauses.
        :meta private:
        """
        if isinstance(arg, (ast.Identifier, ast.Call)):
            res = self.visit(arg)
            if prefix:
                res = f"'{prefix}' || " + res
            if suffix:
                res = res + f" || '{suffix}'"
        else:
            res = str(arg.val).replace("%", "%%").replace("_", "__")  # type: ignore
            res = "'" + prefix + res + suffix + "'"
        return res

    def sqlfunc_contains(self, *args: ast._Node) -> str:
        ":meta private:"
        args_sql = [self.visit(arg) for arg in args]
        inferred_type = [typing.infer_type(arg) for arg in args]

        # If any of the inputs is a string or default, assume str-contains:
        if any(typ is ast.String for typ in inferred_type) or all(
            typ is None for typ in inferred_type
        ):
            pattern = self._to_pattern(args[1], prefix="%", suffix="%")
            return f"{args_sql[0]} LIKE {pattern}"

        # If any of the inputs is a list, assume list-contains:
        if any(typ is ast.List for typ in inferred_type):
            raise exceptions.UnsupportedFunctionException("contains<List>")

        raise exceptions.ArgumentTypeException("contains")

    def sqlfunc_endswith(self, *args: ast._Node) -> str:
        ":meta private:"
        args_sql = [self.visit(arg) for arg in args]
        inferred_type = [typing.infer_type(arg) for arg in args]

        # If any of the inputs is a string or default, assume str-endswith:
        if any(typ is ast.String for typ in inferred_type) or all(
            typ is None for typ in inferred_type
        ):
            pattern = self._to_pattern(args[1], prefix="%")
            return f"{args_sql[0]} LIKE {pattern}"

        # If any of the inputs is a list, assume list-endswith
        # which isn't easily doable at the moment:
        if any(typ is ast.List for typ in inferred_type):
            raise exceptions.UnsupportedFunctionException("endswith<List>")

        raise exceptions.ArgumentTypeException("endswith")

    def sqlfunc_indexof(self, *args: ast._Node) -> str:
        ":meta private:"
        args_sql = [self.visit(arg) for arg in args]
        inferred_type = [typing.infer_type(arg) for arg in args]

        # If any of the inputs is a string, assume str-indexof:
        if any(typ is ast.String for typ in inferred_type) or all(
            typ is None for typ in inferred_type
        ):
            return f"POSITION({args_sql[1]} IN {args_sql[0]}) - 1"

        # If any of the inputs is a list, assume list-indexof
        # which isn't easily doable at the moment:
        if any(typ is ast.List for typ in inferred_type):
            raise exceptions.UnsupportedFunctionException("indexof<List>")

        raise exceptions.ArgumentTypeException("indexof")

    def sqlfunc_length(self, arg: ast._Node) -> str:
        ":meta private:"
        arg_sql = self.visit(arg)
        inferred_type = typing.infer_type(arg)

        # If the input is a string or default, assume str-length:
        if inferred_type is ast.String or inferred_type is None:
            return f"CHAR_LENGTH({arg_sql})"

        # If the input is a list, assume list-length:
        if inferred_type is ast.List:
            return f"CARDINALITY({arg_sql})"

        raise exceptions.ArgumentTypeException("length")

    def sqlfunc_startswith(self, *args: ast._Node) -> str:
        ":meta private:"
        args_sql = [self.visit(arg) for arg in args]
        inferred_type = [typing.infer_type(arg) for arg in args]

        # If any of the inputs is a string or default, assume str-startswith:
        if any(typ is ast.String for typ in inferred_type) or all(
            typ is None for typ in inferred_type
        ):
            pattern = self._to_pattern(args[1], suffix="%")
            return f"{args_sql[0]} LIKE {pattern}"

        # If any of the inputs is a list, assume list-startswith
        # which isn't easily doable at the moment:
        if any(typ is ast.List for typ in inferred_type):
            raise exceptions.UnsupportedFunctionException("startswith<List>")

        raise exceptions.ArgumentTypeException("startswith")

    def sqlfunc_substring(self, *args: ast._Node) -> str:
        ":meta private:"
        args_sql = [self.visit(arg) for arg in args]
        inferred_type = typing.infer_type(args[0])

        # If the first input is a string or default, assume str-substr:
        if inferred_type is ast.String or inferred_type is None:
            if len(args) == 2:
                return f"SUBSTRING({args_sql[0]} FROM {args_sql[1]} + 1)"
            if len(args) == 3:
                return (
                    f"SUBSTRING({args_sql[0]} FROM {args_sql[1]} + 1 FOR {args_sql[2]})"
                )

        # If the first input is a list, assume list-substr:
        if inferred_type is ast.List:
            raise exceptions.UnsupportedFunctionException("substring<List>")

        raise exceptions.ArgumentTypeException("substring")

    def sqlfunc_tolower(self, arg: ast._Node) -> str:
        ":meta private:"
        arg_sql = self.visit(arg)
        return f"LOWER({arg_sql})"

    def sqlfunc_toupper(self, arg: ast._Node) -> str:
        ":meta private:"
        arg_sql = self.visit(arg)
        return f"UPPER({arg_sql})"

    def sqlfunc_trim(self, arg: ast._Node) -> str:
        ":meta private:"
        arg_sql = self.visit(arg)
        return f"TRIM({arg_sql})"

    def sqlfunc_year(self, arg: ast._Node) -> str:
        ":meta private:"
        arg_sql = self.visit(arg)
        return f"EXTRACT (YEAR FROM {arg_sql})"

    def sqlfunc_month(self, arg: ast._Node) -> str:
        ":meta private:"
        arg_sql = self.visit(arg)
        return f"EXTRACT (MONTH FROM {arg_sql})"

    def sqlfunc_day(self, arg: ast._Node) -> str:
        ":meta private:"
        arg_sql = self.visit(arg)
        return f"EXTRACT (DAY FROM {arg_sql})"

    def sqlfunc_hour(self, arg: ast._Node) -> str:
        ":meta private:"
        arg_sql = self.visit(arg)
        return f"EXTRACT (HOUR FROM {arg_sql})"

    def sqlfunc_minute(self, arg: ast._Node) -> str:
        ":meta private:"
        arg_sql = self.visit(arg)
        return f"EXTRACT (MINUTE FROM {arg_sql})"

    def sqlfunc_date(self, arg: ast._Node) -> str:
        ":meta private:"
        arg_sql = self.visit(arg)
        return f"CAST ({arg_sql} AS DATE)"

    def sqlfunc_now(self) -> str:
        ":meta private:"
        return "CURRENT_TIMESTAMP"

    def sqlfunc_round(self, arg: ast._Node) -> str:
        ":meta private:"
        arg_sql = self.visit(arg)
        return f"CAST ({arg_sql} + 0.5 AS INTEGER)"

    def sqlfunc_floor(self, arg: ast._Node) -> str:
        ":meta private:"
        arg_sql = self.visit(arg)
        return f"""CASE {arg_sql}
    WHEN > 0 CAST ({arg_sql} AS INTEGER)
    WHEN < 0 CAST (0 - (ABS({arg_sql}) + 0.5) AS INTEGER))
    ELSE {arg_sql}
END"""

    def sqlfunc_ceiling(self, arg: ast._Node) -> str:
        ":meta private:"
        arg_sql = self.visit(arg)
        return f"""CASE {arg_sql} - CAST ({arg_sql} AS INTEGER)
    WHEN > 0 {arg_sql}+1
    WHEN < 0 {arg_sql}-1
    ELSE {arg_sql}
END"""

    def sqlfunc_hassubset(self, *args: ast._Node) -> str:
        ":meta private:"
        raise exceptions.UnsupportedFunctionException("hassubset")
