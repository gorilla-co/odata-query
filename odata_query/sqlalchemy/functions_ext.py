from sqlalchemy.sql.functions import GenericFunction
from sqlalchemy.types import Integer, String


class strpos(GenericFunction):
    type = Integer
    package = "odata"


class substr(GenericFunction):
    type = String
    package = "odata"


class lower(GenericFunction):
    type = String
    package = "odata"


class upper(GenericFunction):
    type = String
    package = "odata"


class ltrim(GenericFunction):
    type = String
    package = "odata"


class rtrim(GenericFunction):
    type = String
    package = "odata"


class ceil(GenericFunction):
    type = Integer
    package = "odata"


class floor(GenericFunction):
    type = Integer
    package = "odata"


class round(GenericFunction):
    type = Integer
    package = "odata"
