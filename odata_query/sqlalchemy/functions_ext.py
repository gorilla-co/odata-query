from sqlalchemy.sql.functions import GenericFunction
from sqlalchemy.types import Integer, String


class strpos(GenericFunction):
    type = Integer
    package = "odata"
    inherit_cache = True


class substr(GenericFunction):
    type = String
    package = "odata"
    inherit_cache = True


class lower(GenericFunction):
    type = String
    package = "odata"
    inherit_cache = True


class upper(GenericFunction):
    type = String
    package = "odata"
    inherit_cache = True


class ltrim(GenericFunction):
    type = String
    package = "odata"
    inherit_cache = True


class rtrim(GenericFunction):
    type = String
    package = "odata"
    inherit_cache = True


class ceil(GenericFunction):
    type = Integer
    package = "odata"
    inherit_cache = True


class floor(GenericFunction):
    type = Integer
    package = "odata"
    inherit_cache = True


class round(GenericFunction):
    type = Integer
    package = "odata"
    inherit_cache = True
