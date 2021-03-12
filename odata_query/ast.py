import re
from dataclasses import dataclass
from typing import List as ListType, Optional, Tuple

DURATION_PATTERN = re.compile(r"([+-])?P(\d+D)?(?:T(\d+H)?(\d+M)?(\d+(?:\.\d+)?S)?)?")


@dataclass
class _Node:
    pass


@dataclass
class Identifier(_Node):
    name: str


@dataclass
class Attribute(_Node):
    owner: _Node
    attr: str


###############################################################################
# Literals
###############################################################################
@dataclass
class _Literal(_Node):
    pass


@dataclass
class Null(_Literal):
    pass


@dataclass
class Integer(_Literal):
    val: str


@dataclass
class Float(_Literal):
    val: str


@dataclass
class Boolean(_Literal):
    val: str


@dataclass
class String(_Literal):
    val: str


@dataclass
class Date(_Literal):
    val: str


@dataclass
class Time(_Literal):
    val: str


@dataclass
class DateTime(_Literal):
    val: str


@dataclass
class Duration(_Literal):
    val: str

    def unpack(
        self,
    ) -> Tuple[
        Optional[str], Optional[str], Optional[str], Optional[str], Optional[str]
    ]:
        """Returns (sign, days, hours, minutes, seconds)"""

        match = DURATION_PATTERN.fullmatch(self.val)
        if not match:
            raise ValueError(f"Could not unpack Duration with value {self.val}")

        sign, days, hours, minutes, seconds = match.groups()

        _days = days[:-1] if days else None
        _hours = hours[:-1] if hours else None
        _minutes = minutes[:-1] if minutes else None
        _seconds = seconds[:-1] if seconds else None

        return sign, _days, _hours, _minutes, _seconds


@dataclass
class GUID(_Literal):
    val: str


@dataclass
class List(_Literal):
    val: ListType[_Literal]


###############################################################################
# Arithmetic
###############################################################################
@dataclass
class _BinOpToken(_Node):
    pass


@dataclass
class Add(_BinOpToken):
    pass


@dataclass
class Sub(_BinOpToken):
    pass


@dataclass
class Mult(_BinOpToken):
    pass


@dataclass
class Div(_BinOpToken):
    pass


@dataclass
class Mod(_BinOpToken):
    pass


@dataclass
class BinOp(_Node):
    op: _BinOpToken
    left: _Node
    right: _Node


###############################################################################
# Comparison
###############################################################################
@dataclass
class _Comparator(_Node):
    pass


@dataclass
class Eq(_Comparator):
    pass


@dataclass
class NotEq(_Comparator):
    pass


@dataclass
class Lt(_Comparator):
    pass


@dataclass
class LtE(_Comparator):
    pass


@dataclass
class Gt(_Comparator):
    pass


@dataclass
class GtE(_Comparator):
    pass


@dataclass
class In(_Comparator):
    pass


@dataclass
class Compare(_Node):
    comparator: _Comparator
    left: _Node
    right: _Node


###############################################################################
# Boolean ops
###############################################################################
@dataclass
class _BoolOpToken(_Node):
    pass


@dataclass
class And(_BoolOpToken):
    pass


@dataclass
class Or(_BoolOpToken):
    pass


@dataclass
class BoolOp(_Node):
    op: _BoolOpToken
    left: _Node
    right: _Node


###############################################################################
# Unary ops
###############################################################################
@dataclass
class _UnaryOpToken(_Node):
    pass


@dataclass
class Not(_UnaryOpToken):
    pass


@dataclass
class USub(_UnaryOpToken):
    pass


@dataclass
class UnaryOp(_Node):
    op: _UnaryOpToken
    operand: _Node


###############################################################################
# Function calls
###############################################################################
@dataclass
class Call(_Node):
    func: Identifier
    args: ListType[_Node]


###############################################################################
# Collections
###############################################################################
@dataclass
class _CollectionOperator(_Node):
    pass


@dataclass
class Any(_CollectionOperator):
    pass


@dataclass
class All(_CollectionOperator):
    pass


@dataclass
class Lambda(_Node):
    identifier: Identifier
    expression: _Node


@dataclass
class CollectionLambda(_Node):
    owner: _Node
    operator: _CollectionOperator
    lambda_: Optional[Lambda]
