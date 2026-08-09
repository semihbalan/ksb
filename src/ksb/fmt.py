"""Pretty-printer: AST → readable KSB source."""

from __future__ import annotations

from ksb.ast_nodes import (
    Assign,
    Attr,
    BinOp,
    Break,
    Call,
    Continue,
    Expr,
    ExprStmt,
    FnDef,
    ForEach,
    If,
    Import,
    Index,
    Lambda,
    ListLit,
    Literal,
    MapLit,
    Match,
    Module,
    Name,
    Pat,
    PatBind,
    PatList,
    PatLiteral,
    PatMap,
    PatWildcard,
    Pipe,
    Return,
    Stmt,
    UnaryOp,
    While,
)
from ksb.parser import parse


class Formatter:
    def __init__(self, indent: str = "  ") -> None:
        self.ind = indent
        self.level = 0
        self.lines: list[str] = []

    def format_module(self, mod: Module) -> str:
        self.lines = []
        self.level = 0
        for i, stmt in enumerate(mod.body):
            if i and isinstance(stmt, FnDef):
                self.lines.append("")
            self._stmt(stmt)
        return "\n".join(self.lines).rstrip() + "\n"

    def _w(self, s: str) -> None:
        self.lines.append(self.ind * self.level + s)

    def _stmt(self, s: Stmt) -> None:
        if isinstance(s, Import):
            self._w(f"~ {s.module}")
        elif isinstance(s, FnDef):
            params = ", ".join(
                f"{n}:{t}" if t else n for n, t in s.params
            )
            ret = f"->{s.ret_type}" if s.ret_type else ""
            self._w(f"@ {s.name}({params}){ret} {{")
            self.level += 1
            for st in s.body:
                self._stmt(st)
            self.level -= 1
            self._w("}")
        elif isinstance(s, Assign):
            self._w(f"= {s.name} {self._expr(s.value)}")
        elif isinstance(s, Return):
            if s.value is None:
                self._w("^")
            else:
                self._w(f"^ {self._expr(s.value)}")
        elif isinstance(s, If):
            self._w(f"? {self._expr(s.cond)} {{")
            self.level += 1
            for st in s.then_body:
                self._stmt(st)
            self.level -= 1
            if s.else_body is not None:
                self._w("} {")
                self.level += 1
                for st in s.else_body:
                    self._stmt(st)
                self.level -= 1
                self._w("}")
            else:
                self._w("}")
        elif isinstance(s, While):
            self._w(f"* {self._expr(s.cond)} {{")
            self.level += 1
            for st in s.body:
                self._stmt(st)
            self.level -= 1
            self._w("}")
        elif isinstance(s, ForEach):
            self._w(f"* {s.var}:{self._expr(s.iter)} {{")
            self.level += 1
            for st in s.body:
                self._stmt(st)
            self.level -= 1
            self._w("}")
        elif isinstance(s, Break):
            self._w("!.")
        elif isinstance(s, Continue):
            self._w("..")
        elif isinstance(s, Match):
            self._w(f"# {self._expr(s.scrut)} {{")
            self.level += 1
            for arm in s.arms:
                assert arm.pat is not None
                # single return expr arm → compact
                if (
                    len(arm.body) == 1
                    and isinstance(arm.body[0], Return)
                    and arm.body[0].value is not None
                ):
                    self._w(f"{self._pat(arm.pat)} => {self._expr(arm.body[0].value)}")
                elif len(arm.body) == 1 and isinstance(arm.body[0], ExprStmt):
                    self._w(f"{self._pat(arm.pat)} => {self._expr(arm.body[0].expr)}")
                else:
                    self._w(f"{self._pat(arm.pat)} => {{")
                    self.level += 1
                    for st in arm.body:
                        self._stmt(st)
                    self.level -= 1
                    self._w("}")
            self.level -= 1
            self._w("}")
        elif isinstance(s, ExprStmt):
            self._w(self._expr(s.expr))
        else:
            self._w(f"// unknown stmt {type(s).__name__}")

    def _expr(self, e: Expr | None) -> str:
        if e is None:
            return "N"
        if isinstance(e, Name):
            return e.id
        if isinstance(e, Literal):
            if e.kind == "bool":
                return "T" if e.value else "F"
            if e.kind == "null":
                return "N"
            if e.kind == "str":
                return json_str(str(e.value))
            return repr(e.value)
        if isinstance(e, ListLit):
            return "[" + ", ".join(self._expr(x) for x in e.elts) + "]"
        if isinstance(e, MapLit):
            return "{" + ", ".join(f"{k}: {self._expr(v)}" for k, v in e.entries) + "}"
        if isinstance(e, BinOp):
            return f"({self._expr(e.left)} {e.op} {self._expr(e.right)})"
        if isinstance(e, UnaryOp):
            return f"({e.op}{self._expr(e.expr)})"
        if isinstance(e, Call):
            return f"{self._expr(e.func)}({', '.join(self._expr(a) for a in e.args)})"
        if isinstance(e, Index):
            return f"{self._expr(e.target)}[{self._expr(e.index)}]"
        if isinstance(e, Attr):
            return f"{self._expr(e.target)}.{e.attr}"
        if isinstance(e, Pipe):
            return f"({self._expr(e.left)} | {self._expr(e.right)})"
        if isinstance(e, Lambda):
            if isinstance(e.body, list):
                # multi — rare in fmt
                return f"|{e.param}| {{ ... }}"
            return f"|{e.param}| {self._expr(e.body)}"
        if isinstance(e, Match):
            # inline compact
            arms = "; ".join(
                f"{self._pat(a.pat)} => ..." for a in e.arms if a.pat
            )
            return f"# {self._expr(e.scrut)} {{ {arms} }}"
        return f"/*?{type(e).__name__}*/"

    def _pat(self, p: Pat) -> str:
        if isinstance(p, PatWildcard):
            return "_"
        if isinstance(p, PatBind):
            return p.name
        if isinstance(p, PatLiteral):
            if p.kind == "bool":
                return "T" if p.value else "F"
            if p.kind == "null":
                return "N"
            if p.kind == "str":
                return json_str(str(p.value))
            return repr(p.value)
        if isinstance(p, PatList):
            parts = [self._pat(x) for x in p.elts]
            if p.rest:
                parts.append(f"*{p.rest}")
            return "[" + ", ".join(parts) + "]"
        if isinstance(p, PatMap):
            return "{" + ", ".join(f"{k}: {self._pat(v)}" for k, v in p.entries) + "}"
        return "_"


def json_str(s: str) -> str:
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n") + '"'


def format_source(source: str, *, path: str | None = None) -> str:
    return Formatter().format_module(parse(source, path=path))
