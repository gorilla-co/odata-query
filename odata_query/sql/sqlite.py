from odata_query import ast, exceptions, typing

from .base import AstToSqlVisitor


class AstToSqliteSqlVisitor(AstToSqlVisitor):
    """
    :class:`NodeVisitor` that transforms an :term:`AST` into a SQLite SQL
    ``WHERE`` clause.

    Args:
        table_alias: Optional alias for the root table.
    """

    def visit_Boolean(self, node: ast.Boolean) -> str:
        """:meta private:"""
        if node.py_val:
            return "1"
        return "0"

    def visit_Date(self, node: ast.Date) -> str:
        """:meta private:"""
        return f"DATE('{node.val}')"

    def visit_DateTime(self, node: ast.DateTime) -> str:
        """:meta private:"""
        return f"DATETIME('{node.val}')"

    def sqlfunc_indexof(self, *args: ast._Node) -> str:
        """:meta private:"""
        args_sql = [self.visit(arg) for arg in args]
        inferred_type = [typing.infer_type(arg) for arg in args]

        # If any of the inputs is a string, assume str-indexof:
        if any(typ is ast.String for typ in inferred_type) or all(
            typ is None for typ in inferred_type
        ):
            return f"INSTR({args_sql[0]}, {args_sql[1]}) - 1"

        # If any of the inputs is a list, assume list-indexof
        # which isn't easily doable at the moment:
        if any(typ is ast.List for typ in inferred_type):
            raise exceptions.UnsupportedFunctionException("indexof<List>")

        raise exceptions.ArgumentTypeException("indexof")

    def sqlfunc_length(self, arg: ast._Node) -> str:
        """:meta private:"""
        arg_sql = self.visit(arg)
        return f"LENGTH({arg_sql})"

    def sqlfunc_substring(self, *args: ast._Node) -> str:
        """:meta private:"""
        args_sql = [self.visit(arg) for arg in args]
        inferred_type = typing.infer_type(args[0])

        # If the first input is a string or default, assume str-substr:
        if inferred_type is ast.String or inferred_type is None:
            if len(args) == 2:
                return f"SUBSTR({args_sql[0]}, {args_sql[1]} + 1)"
            if len(args) == 3:
                return f"SUBSTR({args_sql[0]}, {args_sql[1]} + 1, {args_sql[2]})"

        # If the first input is a list, assume list-substr:
        if inferred_type is ast.List:
            raise exceptions.UnsupportedFunctionException("substring<List>")

        raise exceptions.ArgumentTypeException("substring")

    def sqlfunc_year(self, arg: ast._Node) -> str:
        """:meta private:"""
        arg_sql = self.visit(arg)
        return f"CAST(STRFTIME('%Y', {arg_sql}) AS INTEGER)"

    def sqlfunc_month(self, arg: ast._Node) -> str:
        """:meta private:"""
        arg_sql = self.visit(arg)
        return f"CAST(STRFTIME('%m', {arg_sql}) AS INTEGER)"

    def sqlfunc_day(self, arg: ast._Node) -> str:
        """:meta private:"""
        arg_sql = self.visit(arg)
        return f"CAST(STRFTIME('%d', {arg_sql}) AS INTEGER)"

    def sqlfunc_hour(self, arg: ast._Node) -> str:
        """:meta private:"""
        arg_sql = self.visit(arg)
        return f"CAST(STRFTIME('%H', {arg_sql}) AS INTEGER)"

    def sqlfunc_minute(self, arg: ast._Node) -> str:
        """:meta private:"""
        arg_sql = self.visit(arg)
        return f"CAST(STRFTIME('%M', {arg_sql}) AS INTEGER)"

    def sqlfunc_date(self, arg: ast._Node) -> str:
        """:meta private:"""
        arg_sql = self.visit(arg)
        return f"DATE({arg_sql})"

    def sqlfunc_now(self) -> str:
        """:meta private:"""
        return "DATETIME('now')"

    def sqlfunc_round(self, arg: ast._Node) -> str:
        """:meta private:"""
        arg_sql = self.visit(arg)
        return f"TRUNC({arg_sql} + 0.5)"

    def sqlfunc_floor(self, arg: ast._Node) -> str:
        """:meta private:"""
        arg_sql = self.visit(arg)
        return f"FLOOR({arg_sql})"

    def sqlfunc_ceiling(self, arg: ast._Node) -> str:
        """:meta private:"""
        arg_sql = self.visit(arg)
        return f"CEILING({arg_sql})"
