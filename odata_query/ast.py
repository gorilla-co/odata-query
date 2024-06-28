import datetime as dt
import re
from dataclasses import dataclass, field
from typing import List as ListType, Optional, Tuple
from uuid import UUID

from dateutil.parser import isoparse

DURATION_PATTERN = re.compile(
    r"([+-])?P(\d+Y)?(\d+M)?(\d+D)?(?:T(\d+H)?(\d+M)?(\d+(?:\.\d+)?S)?)?"
)


@dataclass(frozen=True)
class _Node:
    pass


@dataclass(frozen=True)
class Identifier(_Node):
    name: str
    namespace: Tuple[str, ...] = field(default_factory=tuple)

    def full_name(self):
        return ".".join(self.namespace + (self.name,))


@dataclass(frozen=True)
class Attribute(_Node):
    owner: _Node
    attr: str


###############################################################################
# Literals
###############################################################################
@dataclass(frozen=True)
class _Literal(_Node):
    pass

    @property
    def py_val(self):
        raise NotImplementedError()


@dataclass(frozen=True)
class Null(_Literal):
    @property
    def py_val(self) -> None:
        return None


@dataclass(frozen=True)
class Integer(_Literal):
    val: str

    @property
    def py_val(self) -> int:
        return int(self.val)


@dataclass(frozen=True)
class Float(_Literal):
    val: str

    @property
    def py_val(self) -> float:
        return float(self.val)


@dataclass(frozen=True)
class Boolean(_Literal):
    val: str

    @property
    def py_val(self) -> bool:
        return self.val.lower() == "true"


@dataclass(frozen=True)
class String(_Literal):
    val: str

    @property
    def py_val(self) -> str:
        return self.val


@dataclass(frozen=True)
class Geography(_Literal):
    val: str

    def wkt(self):
        return self.val


@dataclass(frozen=True)
class Date(_Literal):
    val: str

    @property
    def py_val(self) -> dt.date:
        return dt.date.fromisoformat(self.val)


@dataclass(frozen=True)
class Time(_Literal):
    val: str

    @property
    def py_val(self) -> dt.time:
        return dt.time.fromisoformat(self.val)


@dataclass(frozen=True)
class DateTime(_Literal):
    val: str

    @property
    def py_val(self) -> dt.datetime:
        return isoparse(self.val)


@dataclass(frozen=True)
class Duration(_Literal):
    val: str

    @property
    def py_val(self) -> dt.timedelta:
        sign, years, months, days, hours, minutes, seconds = self.unpack()

        # Initialize days to 0 if None
        num_days = float(days or 0)

        # Approximate conversion, adjust as necessary for more precision
        num_days += float(years or 0) * 365.25  # Average including leap years
        num_days += float(months or 0) * 30.44  # Average month length

        delta = dt.timedelta(
            days=num_days,
            hours=float(hours or 0),
            minutes=float(minutes or 0),
            seconds=float(seconds or 0),
        )
        if sign and sign == "-":
            delta = -1 * delta
        return delta

    def unpack(
        self,
    ) -> Tuple[
        Optional[str],
        Optional[str],
        Optional[str],
        Optional[str],
        Optional[str],
        Optional[str],
        Optional[str],
    ]:
        """
        Returns:
            ``(sign, years, months, days, hours, minutes, seconds)``
        """

        match = DURATION_PATTERN.fullmatch(self.val)
        if not match:
            raise ValueError(f"Could not unpack Duration with value {self.val}")

        sign, years, months, days, hours, minutes, seconds = match.groups()

        _years = years[:-1] if years else None
        _months = months[:-1] if months else None
        _days = days[:-1] if days else None
        _hours = hours[:-1] if hours else None
        _minutes = minutes[:-1] if minutes else None
        _seconds = seconds[:-1] if seconds else None

        return sign, _years, _months, _days, _hours, _minutes, _seconds


@dataclass(frozen=True)
class GUID(_Literal):
    val: str

    @property
    def py_val(self) -> UUID:
        return UUID(self.val)


@dataclass(frozen=True)
class List(_Literal):
    val: ListType[_Literal]

    @property
    def py_val(self) -> list:
        return [v.py_val for v in self.val]


###############################################################################
# Arithmetic
###############################################################################
@dataclass(frozen=True)
class _BinOpToken(_Node):
    pass


@dataclass(frozen=True)
class Add(_BinOpToken):
    pass


@dataclass(frozen=True)
class Sub(_BinOpToken):
    pass


@dataclass(frozen=True)
class Mult(_BinOpToken):
    pass


@dataclass(frozen=True)
class Div(_BinOpToken):
    pass


@dataclass(frozen=True)
class Mod(_BinOpToken):
    pass


@dataclass(frozen=True)
class BinOp(_Node):
    op: _BinOpToken
    left: _Node
    right: _Node


###############################################################################
# Comparison
###############################################################################
@dataclass(frozen=True)
class _Comparator(_Node):
    pass


@dataclass(frozen=True)
class Eq(_Comparator):
    pass


@dataclass(frozen=True)
class NotEq(_Comparator):
    pass


@dataclass(frozen=True)
class Lt(_Comparator):
    pass


@dataclass(frozen=True)
class LtE(_Comparator):
    pass


@dataclass(frozen=True)
class Gt(_Comparator):
    pass


@dataclass(frozen=True)
class GtE(_Comparator):
    pass


@dataclass(frozen=True)
class In(_Comparator):
    pass


@dataclass(frozen=True)
class Compare(_Node):
    comparator: _Comparator
    left: _Node
    right: _Node


###############################################################################
# Boolean ops
###############################################################################
@dataclass(frozen=True)
class _BoolOpToken(_Node):
    pass


@dataclass(frozen=True)
class And(_BoolOpToken):
    pass


@dataclass(frozen=True)
class Or(_BoolOpToken):
    pass


@dataclass(frozen=True)
class BoolOp(_Node):
    op: _BoolOpToken
    left: _Node
    right: _Node


###############################################################################
# Unary ops
###############################################################################
@dataclass(frozen=True)
class _UnaryOpToken(_Node):
    pass


@dataclass(frozen=True)
class Not(_UnaryOpToken):
    pass


@dataclass(frozen=True)
class USub(_UnaryOpToken):
    pass


@dataclass(frozen=True)
class UnaryOp(_Node):
    op: _UnaryOpToken
    operand: _Node


###############################################################################
# Function calls
###############################################################################
@dataclass(frozen=True)
class NamedParam(_Node):
    name: Identifier
    param: _Node


@dataclass(frozen=True)
class Call(_Node):
    func: Identifier
    args: ListType[_Node]


###############################################################################
# Collections
###############################################################################
@dataclass(frozen=True)
class _CollectionOperator(_Node):
    pass


@dataclass(frozen=True)
class Any(_CollectionOperator):
    pass


@dataclass(frozen=True)
class All(_CollectionOperator):
    pass


@dataclass(frozen=True)
class Lambda(_Node):
    identifier: Identifier
    expression: _Node


@dataclass(frozen=True)
class CollectionLambda(_Node):
    owner: _Node
    operator: _CollectionOperator
    lambda_: Optional[Lambda]
