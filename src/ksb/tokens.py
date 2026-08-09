"""Token kinds and token object."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto


class Tok(Enum):
    EOF = auto()
    NEWLINE = auto()  # statement boundary; binops do not cross newlines
    IDENT = auto()
    INT = auto()
    FLOAT = auto()
    STRING = auto()

    # single / multi char
    AT = auto()          # @
    CARET = auto()       # ^
    TILDE = auto()       # ~
    QMARK = auto()       # ?
    HASH = auto()        # #  match
    EQ = auto()          # =
    SEMI = auto()        # ;
    COMMA = auto()       # ,
    COLON = auto()       # :
    DOT = auto()         # .
    ARROW = auto()       # ->
    FATARROW = auto()    # =>  match arm
    PIPE = auto()        # |
    OR = auto()          # ||
    AND = auto()         # &&
    BANG = auto()        # !
    NE = auto()          # !=
    EQEQ = auto()        # ==
    LT = auto()          # <
    GT = auto()          # >
    LE = auto()          # <=
    GE = auto()          # >=
    PLUS = auto()        # +
    MINUS = auto()       # -
    STAR = auto()        # *
    SLASH = auto()       # /
    PERCENT = auto()     # %
    LPAREN = auto()      # (
    RPAREN = auto()      # )
    LBRACE = auto()      # {
    RBRACE = auto()      # }
    LBRACK = auto()      # [
    RBRACK = auto()      # ]


@dataclass(frozen=True, slots=True)
class Token:
    kind: Tok
    value: str | int | float | None
    line: int
    col: int

    def __repr__(self) -> str:
        if self.value is None or self.value == "":
            return f"Token({self.kind.name}@{self.line}:{self.col})"
        return f"Token({self.kind.name}={self.value!r}@{self.line}:{self.col})"
