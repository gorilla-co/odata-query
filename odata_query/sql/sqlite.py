import logging
import re
from typing import Optional

from odata_query import ast, exceptions, typing, visitor

log = logging.getLogger(__name__)

UNSAFE_CHARS = re.compile(r"[^a-zA-Z0-9_]")


def clean_sqlite_identifier(identifier: str) -> str:
    """
    Cleans an Sqlite identifier so it passes the following validation rules:

    - Table names and table column names in Sqlite must be lowercase
    - Sqlite table, view, database, and column names allow only underscore special characters
    - Names should be quoted or backticked when starting with a number or underscore

    Source: https://docs.aws.amazon.com/sqlite/latest/ug/tables-databases-columns-names.html
    """
    id_new = identifier.lower()
    id_new = UNSAFE_CHARS.sub("_", id_new)

    first_char = id_new[0]
    if first_char == "_" or first_char.isdigit():
        log.warning(
            "Sqlite identifier '%s' starts with an unsafe character, "
            "which might reduce compatibility with certain BI tools.",
            identifier,
        )

    return id_new


class AstToSqliteSqlVisitor(visitor.NodeVisitor):
    """
    :class:`NodeVisitor` that transforms an :term:`AST` into an Sqlite SQL
    ``WHERE`` clause.

    Args:
        table_alias: Optional alias for the root table.
    """

    def __init__(self, table_alias: Optional[str] = None):
        super().__init__()
        self.table_alias = table_alias

    def visit_Identifier(self, node: ast.Identifier) -> str:
        """:meta private:"""
        # Double quotes for column names acc SQL Standard
        sql_id = f'"{clean_sqlite_identifier(node.name)}"'

        if self.table_alias:
            sql_id = f'"{self.table_alias}".' + sql_id

        return sql_id

    def visit_Null(self, node: ast.Null) -> str:
        """:meta private:"""
        return "NULL"

    def visit_Integer(self, node: ast.Integer) -> str:
        """:meta private:"""
        return node.val

    def visit_Float(self, node: ast.Float) -> str:
        """:meta private:"""
        return node.val

    def visit_Boolean(self, node: ast.Boolean) -> int:
        """:meta private:"""
        if node.val == "false":
            return 0
        return 1

    def visit_String(self, node: ast.String) -> str:
        """:meta private:"""
        # Replace single quotes with double single-quotes acc SQL standard:
        val = node.val.replace("'", "''")
        # Wrap in single quotes for string constants acc SQL Standard
        return f"'{val}'"

    def visit_Date(self, node: ast.Date) -> str:
        """:meta private:"""
        # Single quotes for date constants acc SQL Standard
        return f"date('{node.val}')"

    def visit_DateTime(self, node: ast.DateTime) -> str:
        """:meta private:"""
        # Single quotes for datetime constants acc SQL Standard
        return f"datetime('{node.val}')"

    def visit_GUID(self, node: ast.GUID) -> str:
        """:meta private:"""
        return f"'{node.val}'"

    def visit_List(self, node: ast.List) -> str:
        """:meta private:"""
        options = ", ".join(self.visit(n) for n in node.val)
        return f"({options})"

    def visit_Add(self, node: ast.Add) -> str:
        """:meta private:"""
        return "+"

    def visit_Sub(self, node: ast.Sub) -> str:
        """:meta private:"""
        return "-"

    def visit_Mult(self, node: ast.Mult) -> str:
        """:meta private:"""
        return "*"

    def visit_Div(self, node: ast.Div) -> str:
        """:meta private:"""
        return "/"

    def visit_Mod(self, node: ast.Mod) -> str:
        """:meta private:"""
        return "%"

    def visit_BinOp(self, node: ast.BinOp) -> str:
        """:meta private:"""
        left = self.visit(node.left)
        right = self.visit(node.right)
        op = self.visit(node.op)

        return f"{left} {op} {right}"

    def visit_Eq(self, node: ast.Eq) -> str:
        """:meta private:"""
        return "="

    def visit_NotEq(self, node: ast.NotEq) -> str:
        """:meta private:"""
        return "!="

    def visit_Lt(self, node: ast.Lt) -> str:
        """:meta private:"""
        return "<"

    def visit_LtE(self, node: ast.LtE) -> str:
        """:meta private:"""
        return "<="

    def visit_Gt(self, node: ast.Gt) -> str:
        """:meta private:"""
        return ">"

    def visit_GtE(self, node: ast.GtE) -> str:
        """:meta private:"""
        return ">="

    def visit_In(self, node: ast.In) -> str:
        """:meta private:"""
        return "IN"

    def visit_Compare(self, node: ast.Compare) -> str:
        """:meta private:"""
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
        """:meta private:"""
        return "AND"

    def visit_Or(self, node: ast.Or) -> str:
        """:meta private:"""
        return "OR"

    def visit_BoolOp(self, node: ast.BoolOp) -> str:
        """:meta private:"""
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
        """:meta private:"""
        return "NOT"

    def visit_UnaryOp(self, node: ast.UnaryOp) -> str:
        """:meta private:"""
        op = self.visit(node.op)
        operand = self.visit(node.operand)

        # In case of a subexpression, wrap it in parentheses
        if isinstance(node.operand, ast.BoolOp):
            operand = f"({operand})"

        return f"{op} {operand}"

    def visit_Call(self, node: ast.Call) -> str:
        """:meta private:"""
        try:
            # Grammar has already validated that the function is valid OData,
            # but that doesn't guarantee we can represent it in SQL:
            sql_gen = getattr(self, "sqlfunc_" + node.func.name.lower())
        except AttributeError:
            raise exceptions.UnsupportedFunctionException(node.func.name)

        return sql_gen(*node.args)

    def sqlfunc_concat(self, *args: ast._Node) -> str:
        """:meta private:"""
        # Presto's `concat` works on both strings and lists:
        args_sql = [self.visit(arg) for arg in args]
        return " || ".join(args_sql)

    def sqlfunc_contains(self, field: ast._Node, substr: ast._Node) -> str:
        """:meta private:"""
        left = self.visit(field)
        right = self.visit(substr)
        right = f"'%{right[1:-1]}%'"
        return f"{left} LIKE {right}"

    def sqlfunc_endswith(self, field: ast._Node, substr: ast._Node) -> str:
        """:meta private:"""
        left = self.visit(field)
        right = self.visit(substr)
        right = f"'%{right[1:-1]}'"
        return f"{left} LIKE {right}"

    def sqlfunc_indexof(self, left: ast._Node, right: ast.String) -> str:
        """:meta private:"""
        left = self.visit(left)
        right = self.visit(right)
        return f"INSTR({left}, {right}) - 1"

    def sqlfunc_length(self, arg: ast._Node) -> str:
        """:meta private:"""
        arg_sql = self.visit(arg)
        return f"length({arg_sql})"

    def sqlfunc_startswith(self, field: ast._Node, substr: ast._Node) -> str:
        """:meta private:"""
        left = self.visit(field)
        right = self.visit(substr)
        right = f"'{right[1:-1]}%'"
        return f"{left} LIKE {right}"

    def sqlfunc_substring(self, *args: ast._Node) -> str:
        """:meta private:"""
        args_sql = [self.visit(arg) for arg in args]
        inferred_type = typing.infer_type(args[0])

        # If the first input is a string or default, assume str-substr:
        if inferred_type is ast.String or inferred_type is None:
            if len(args) == 2:
                return f"substr({args_sql[0]}, {args_sql[1]} + 1)"
            if len(args) == 3:
                return f"substr({args_sql[0]}, {args_sql[1]} + 1, {args_sql[2]})"

        # If the first input is a list, assume list-substr:
        if inferred_type is ast.List:
            if len(args) == 2:
                return f"slice({args_sql[0]}, {args_sql[1]})"
            if len(args) == 3:
                return f"slice({args_sql[0]}, {args_sql[1]}, {args_sql[2]})"

        raise exceptions.ArgumentTypeException("substring")

    def sqlfunc_tolower(self, arg: ast._Node) -> str:
        """:meta private:"""
        arg_sql = self.visit(arg)
        return f"lower({arg_sql})"

    def sqlfunc_toupper(self, arg: ast._Node) -> str:
        """:meta private:"""
        arg_sql = self.visit(arg)
        return f"upper({arg_sql})"

    def sqlfunc_trim(self, arg: ast._Node) -> str:
        """:meta private:"""
        arg_sql = self.visit(arg)
        return f"trim({arg_sql})"

    def sqlfunc_year(self, arg: ast._Node) -> str:
        """:meta private:"""
        arg_sql = self.visit(arg)
        return f"strftime('%y', {arg_sql})"

    def sqlfunc_month(self, arg: ast._Node) -> str:
        """:meta private:"""
        arg_sql = self.visit(arg)
        return f"strftime('%m', {arg_sql})"

    def sqlfunc_day(self, arg: ast._Node) -> str:
        """:meta private:"""
        arg_sql = self.visit(arg)
        return f"strftime('%d', {arg_sql})"

    def sqlfunc_hour(self, arg: ast._Node) -> str:
        """:meta private:"""
        arg_sql = self.visit(arg)
        return f"strftime('%H', {arg_sql})"

    def sqlfunc_minute(self, arg: ast._Node) -> str:
        """:meta private:"""
        arg_sql = self.visit(arg)
        return f"strftime('%M', {arg_sql})"

    def sqlfunc_date(self, arg: ast._Node) -> str:
        """:meta private:"""
        arg_sql = self.visit(arg)
        return f"date({arg_sql})"

    def sqlfunc_now(self) -> str:
        """:meta private:"""
        return "datetime('now')"

    def sqlfunc_round(self, arg: ast._Node) -> str:
        """:meta private:"""
        arg_sql = self.visit(arg)
        return f"round({arg_sql})"

    def sqlfunc_floor(self, arg: ast._Node) -> str:
        """:meta private:"""
        arg_sql = self.visit(arg)
        return f"floor({arg_sql})"

    def sqlfunc_ceiling(self, arg: ast._Node) -> str:
        """:meta private:"""
        arg_sql = self.visit(arg)
        return f"ceiling({arg_sql})"
