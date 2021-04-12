from sqlalchemy.sql.functions import GenericFunction
from sqlalchemy.types import Integer, String


class strpos(GenericFunction):
    type = Integer


class substr(GenericFunction):
    type = String


class lower(GenericFunction):
    type = String


class upper(GenericFunction):
    type = String


class ltrim(GenericFunction):
    type = String


class rtrim(GenericFunction):
    type = String


class ceil(GenericFunction):
    type = Integer


class floor(GenericFunction):
    type = Integer


class round(GenericFunction):
    type = Integer
