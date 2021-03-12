from django.db.models import CharField, Lookup, Subquery, fields, functions


@fields.Field.register_lookup
class NotEqual(Lookup):
    """https://docs.djangoproject.com/en/2.2/howto/custom-lookups/"""

    lookup_name = "ne"

    def as_sql(self, compiler, connection):
        lhs, lhs_params = self.process_lhs(compiler, connection)
        rhs, rhs_params = self.process_rhs(compiler, connection)
        params = lhs_params + rhs_params
        return "%s <> %s" % (lhs, rhs), params


CharField.register_lookup(functions.Length)
CharField.register_lookup(functions.Upper)
CharField.register_lookup(functions.Lower)
CharField.register_lookup(functions.Trim)


class _AnyAll(Subquery):
    template = ""

    def __init__(self, queryset, negated=False, **kwargs):
        # As a performance optimization, remove ordering since ~ doesn't
        # care about it, just whether or not a row matches.
        queryset = queryset.order_by()
        self.negated = negated
        super().__init__(queryset, **kwargs)

    def __invert__(self):
        clone = self.copy()
        clone.negated = not self.negated
        return clone

    def __repr__(self) -> str:
        return self.template % {"subquery": self.queryset.query}

    def as_sql(self, compiler, connection, template=None, **extra_context):
        sql, params = super().as_sql(compiler, connection, template, **extra_context)
        # if self.negated:
        #     sql = "NOT {}".format(sql)
        return sql, params

    def select_format(self, compiler, sql, params):
        return sql, params


class Any(_AnyAll):
    template = "ANY(%(subquery)s)"


class All(_AnyAll):
    template = "ALL(%(subquery)s)"
