"""AST node types for KSB."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Node:
    line: int = 0
    col: int = 0


# --- expressions ---


@dataclass
class Expr(Node):
    pass


@dataclass
class Name(Expr):
    id: str = ""


@dataclass
class Literal(Expr):
    value: Any = None
    kind: str = "any"  # int|float|str|bool|null


@dataclass
class ListLit(Expr):
    elts: list[Expr] = field(default_factory=list)


@dataclass
class MapLit(Expr):
    entries: list[tuple[str, Expr]] = field(default_factory=list)


@dataclass
class BinOp(Expr):
    op: str = ""
    left: Expr | None = None
    right: Expr | None = None


@dataclass
class UnaryOp(Expr):
    op: str = ""
    expr: Expr | None = None


@dataclass
class Call(Expr):
    func: Expr | None = None
    args: list[Expr] = field(default_factory=list)


@dataclass
class Index(Expr):
    target: Expr | None = None
    index: Expr | None = None


@dataclass
class Attr(Expr):
    target: Expr | None = None
    attr: str = ""


@dataclass
class Pipe(Expr):
    left: Expr | None = None
    right: Expr | None = None  # usually Name or Call


@dataclass
class Lambda(Expr):
    param: str = ""
    body: list[Stmt] | Expr | None = None  # block stmts or single expr


# --- patterns (for # match) ---


@dataclass
class Pat(Node):
    pass


@dataclass
class PatWildcard(Pat):
    """`_` — matches anything, binds nothing."""


@dataclass
class PatLiteral(Pat):
    value: Any = None
    kind: str = "any"


@dataclass
class PatBind(Pat):
    """Name binds the matched value."""
    name: str = ""


@dataclass
class PatList(Pat):
    """`[a, b, *rest]` — rest is optional trailing star-bind."""
    elts: list[Pat] = field(default_factory=list)
    rest: str | None = None  # *name


@dataclass
class PatMap(Pat):
    """`{k: pat, ...}` — all listed keys must match."""
    entries: list[tuple[str, Pat]] = field(default_factory=list)


# --- statements ---


@dataclass
class Stmt(Node):
    pass


@dataclass
class Assign(Stmt):
    name: str = ""
    value: Expr | None = None


@dataclass
class Return(Stmt):
    value: Expr | None = None


@dataclass
class If(Stmt):
    cond: Expr | None = None
    then_body: list[Stmt] = field(default_factory=list)
    else_body: list[Stmt] | None = None


@dataclass
class While(Stmt):
    cond: Expr | None = None
    body: list[Stmt] = field(default_factory=list)


@dataclass
class ForEach(Stmt):
    var: str = ""
    iter: Expr | None = None
    body: list[Stmt] = field(default_factory=list)


@dataclass
class Break(Stmt):
    pass


@dataclass
class Continue(Stmt):
    pass


@dataclass
class ExprStmt(Stmt):
    expr: Expr | None = None


@dataclass
class FnDef(Stmt):
    name: str = ""
    params: list[tuple[str, str | None]] = field(default_factory=list)  # (name, type?)
    ret_type: str | None = None
    body: list[Stmt] = field(default_factory=list)


@dataclass
class Import(Stmt):
    module: str = ""


@dataclass
class MatchArm(Node):
    pat: Pat | None = None
    body: list[Stmt] = field(default_factory=list)


@dataclass
class Match(Stmt, Expr):
    """`# scrut { pat => body; ... }` — usable as stmt or expr."""
    scrut: Expr | None = None
    arms: list[MatchArm] = field(default_factory=list)


@dataclass
class Module(Node):
    body: list[Stmt] = field(default_factory=list)
    path: str | None = None
