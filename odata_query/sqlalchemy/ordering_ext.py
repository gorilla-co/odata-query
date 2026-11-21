from sqlalchemy.ext.compiler import compiles
from sqlalchemy.sql import operators
from sqlalchemy.sql.elements import UnaryExpression
from sqlalchemy.sql.visitors import InternalTraversal


class SpecOrdering(UnaryExpression):
    """
    An ``ORDER BY`` item that sorts ``NULL`` first when ascending and last when
    descending, as OData requires.

    Args:
        element: The expression to sort on.
        ascending: Whether to sort ascending or descending.
        may_be_null: Whether ``element`` can evaluate to ``NULL``. If not, it
            can be sorted without an explicit ``NULL`` ordering, which can keep
            a database from using an index.
    """

    inherit_cache = True
    _traverse_internals = UnaryExpression._traverse_internals + [
        ("may_be_null", InternalTraversal.dp_boolean)
    ]

    def __init__(self, element, ascending: bool, may_be_null: bool = True):
        super().__init__(
            element,
            modifier=operators.asc_op if ascending else operators.desc_op,
            wraps_column_expression=False,
        )
        self.may_be_null = may_be_null


def _compile(element: SpecOrdering, compiler, nulls: bool, **kw) -> str:
    sql = compiler.process(element.element, **kw)
    nulls = nulls and element.may_be_null
    if element.modifier is operators.asc_op:
        return sql + " ASC" + (" NULLS FIRST" if nulls else "")
    return sql + " DESC" + (" NULLS LAST" if nulls else "")


@compiles(SpecOrdering)
def _compile_with_explicit_nulls(element, compiler, **kw):
    return _compile(element, compiler, nulls=True, **kw)


# These databases consider NULL smaller than any value, which already is the
# order OData asks for. They do not all support NULLS FIRST/LAST.
@compiles(SpecOrdering, "sqlite", "mysql", "mariadb", "mssql")
def _compile_with_default_nulls(element, compiler, **kw):
    return _compile(element, compiler, nulls=False, **kw)
