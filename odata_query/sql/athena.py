import re

from odata_query import ast, exceptions, typing

from .base import AstToSqlVisitor

UNSAFE_CHARS = re.compile(r"[^a-zA-Z0-9_]")


def clean_athena_identifier(identifier: str) -> str:
    """
    Cleans an Athena identifier so it passes the following validation rules:

    - Table names and table column names in Athena must be lowercase
    - Athena table, view, database, and column names allow only underscore special characters
    - Names should be quoted or backticked when starting with a number or underscore

    Source: https://docs.aws.amazon.com/athena/latest/ug/tables-databases-columns-names.html
    """
    id_new = identifier.lower()
    id_new = UNSAFE_CHARS.sub("_", id_new)
    return id_new


class AstToAthenaSqlVisitor(AstToSqlVisitor):
    """
    :class:`NodeVisitor` that transforms an :term:`AST` into an Athena SQL
    ``WHERE`` clause.

    Args:
        table_alias: Optional alias for the root table.
    """

    def visit_Identifier(self, node: ast.Identifier) -> str:
        ":meta private:"
        # Double quotes for column names acc SQL Standard
        sql_id = f'"{clean_athena_identifier(node.name)}"'

        if self.table_alias:
            sql_id = f'"{self.table_alias}".' + sql_id

        return sql_id

    def visit_DateTime(self, node: ast.DateTime) -> str:
        ":meta private:"
        return f"FROM_ISO8601_TIMESTAMP('{node.val}')"

    def sqlfunc_length(self, arg: ast._Node) -> str:
        ":meta private:"
        arg_sql = self.visit(arg)
        inferred_type = typing.infer_type(arg)

        # If the input is a string or default, assume str-length:
        if inferred_type is ast.String or inferred_type is None:
            return f"LENGTH({arg_sql})"

        # If the input is a list, assume list-length:
        if inferred_type is ast.List:
            return f"CARDINALITY({arg_sql})"

        raise exceptions.ArgumentTypeException("length")

    def sqlfunc_substring(self, *args: ast._Node) -> str:
        ":meta private:"
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
            if len(args) == 2:
                return f"SLICE({args_sql[0]}, {args_sql[1]})"
            if len(args) == 3:
                return f"SLICE({args_sql[0]}, {args_sql[1]}, {args_sql[2]})"

        raise exceptions.ArgumentTypeException("substring")

    def sqlfunc_round(self, arg: ast._Node) -> str:
        ":meta private:"
        arg_sql = self.visit(arg)
        return f"ROUND({arg_sql})"

    def sqlfunc_floor(self, arg: ast._Node) -> str:
        ":meta private:"
        arg_sql = self.visit(arg)
        return f"FLOOR({arg_sql})"

    def sqlfunc_ceiling(self, arg: ast._Node) -> str:
        ":meta private:"
        arg_sql = self.visit(arg)
        return f"CEILING({arg_sql})"

    def sqlfunc_hassubset(self, *args: ast._Node) -> str:
        ":meta private:"
        args_sql = [self.visit(arg) for arg in args]
        return f"CARDINALITY(ARRAY_INTERSECT({args_sql[0]}, {args_sql[1]})) = CARDINALITY({args_sql[1]})"
