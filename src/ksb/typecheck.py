"""Lightweight type checker for optional KSB annotations.

Design goals for AI agents:
- Catch obvious mistakes before run (wrong arg count, int+str, unknown names)
- Stay short on errors (token-cheap)
- `a` (any) is the escape hatch; missing annotations default to `a`
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ksb.ast_nodes import (
    Assign,
    Attr,
    BinOp,
    Call,
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
    Pipe,
    Return,
    Stmt,
    UnaryOp,
    While,
)
from ksb.errors import KsbError

# type letters
ANY = "a"
INT = "i"
FLOAT = "f"
STR = "s"
BOOL = "b"
LIST = "l"
MAP = "m"
UNIT = "u"
NUM = "n"  # internal: int|float

VALID = frozenset({ANY, INT, FLOAT, STR, BOOL, LIST, MAP, UNIT})


class TypeError_(KsbError):
    """Named TypeError_ to avoid clashing with builtins.TypeError."""

    def __init__(self, message: str, *, line: int = 0, col: int = 0, path: str | None = None) -> None:
        super().__init__("E40", message, line=line, col=col, path=path)


@dataclass
class FnSig:
    params: list[str]
    ret: str
    line: int = 0
    col: int = 0


@dataclass
class Env:
    vars: dict[str, str] = field(default_factory=dict)
    fns: dict[str, FnSig] = field(default_factory=dict)
    modules: set[str] = field(default_factory=set)

    def copy(self) -> Env:
        return Env(vars=dict(self.vars), fns=dict(self.fns), modules=set(self.modules))


# runtime module surfaces (name → attr → ret type approx)
RUNTIME: dict[str, dict[str, str]] = {
    "fs": {
        "read": STR,
        "write": UNIT,
        "exists": BOOL,
        "list": LIST,
        "mkdir": UNIT,
        "remove": UNIT,
        "copy": UNIT,
        "cwd": STR,
    },
    "json": {"parse": ANY, "dump": STR},
    "http": {
        "get": MAP,
        "post": MAP,
        "put": MAP,
        "delete": MAP,
        "get_json": ANY,
        "post_json": ANY,
    },
    "sh": {"run": MAP},
    "env": {"get": STR, "set": UNIT},
    "log": {"info": UNIT, "err": UNIT},
    "time": {"now": FLOAT, "ms": INT, "sleep": UNIT, "iso": STR},
    "path": {"join": STR, "dirname": STR, "basename": STR, "abs": STR, "ext": STR},
    "cli": {"args": LIST, "argc": INT, "arg": STR},
    "tool": {"ok": MAP, "err": MAP, "wrap": ANY},
    "str": {
        "split": LIST,
        "join": STR,
        "trim": STR,
        "replace": STR,
        "contains": BOOL,
        "lower": STR,
        "upper": STR,
        "startswith": BOOL,
        "endswith": BOOL,
    },
}


def unify(a: str, b: str) -> str:
    if a == ANY or a == "":
        return b or ANY
    if b == ANY or b == "":
        return a
    if a == b:
        return a
    if {a, b} <= {INT, FLOAT, NUM}:
        return FLOAT if FLOAT in (a, b) else INT
    return ANY


def compatible(got: str, expect: str) -> bool:
    if expect in (ANY, "") or got in (ANY, ""):
        return True
    if got == expect:
        return True
    if expect == NUM and got in (INT, FLOAT):
        return True
    if got == INT and expect == FLOAT:
        return True
    return False


class TypeChecker:
    def __init__(self, path: str | None = None) -> None:
        self.path = path
        self.errors: list[TypeError_] = []

    def check(self, mod: Module) -> list[TypeError_]:
        self.errors = []
        env = Env()
        # first pass: collect fn signatures
        for stmt in mod.body:
            if isinstance(stmt, Import):
                env.modules.add(stmt.module.split("/")[-1].replace(".ksb", ""))
                # also full module name as imported id for runtime
                env.vars[stmt.module] = MAP  # module object-ish
                base = _import_name(stmt.module)
                env.vars[base] = MAP
            elif isinstance(stmt, FnDef):
                params = [t or ANY for _, t in stmt.params]
                env.fns[stmt.name] = FnSig(params, stmt.ret_type or ANY, stmt.line, stmt.col)
        for stmt in mod.body:
            self._stmt(stmt, env)
        return self.errors

    def _err(self, msg: str, node) -> None:
        self.errors.append(
            TypeError_(msg, line=getattr(node, "line", 0) or 0, col=getattr(node, "col", 0) or 0, path=self.path)
        )

    def _stmt(self, s: Stmt, env: Env) -> None:
        if isinstance(s, Import):
            return
        if isinstance(s, FnDef):
            local = env.copy()
            for name, t in s.params:
                local.vars[name] = t or ANY
            for st in s.body:
                self._stmt(st, local)
            return
        if isinstance(s, Assign):
            t = self._expr(s.value, env)
            env.vars[s.name] = t
            return
        if isinstance(s, Return):
            if s.value is not None:
                self._expr(s.value, env)
            return
        if isinstance(s, If):
            self._expr(s.cond, env)
            self._block(s.then_body, env)
            if s.else_body is not None:
                self._block(s.else_body, env)
            return
        if isinstance(s, While):
            self._expr(s.cond, env)
            self._block(s.body, env)
            return
        if isinstance(s, ForEach):
            self._expr(s.iter, env)
            local = env.copy()
            local.vars[s.var] = ANY
            self._block(s.body, local)
            return
        if isinstance(s, Match):
            self._expr(s.scrut, env)
            for arm in s.arms:
                local = env.copy()
                self._pat_binds(arm.pat, local)
                self._block(arm.body, local)
            return
        if isinstance(s, ExprStmt):
            self._expr(s.expr, env)

    def _block(self, body: list[Stmt], env: Env) -> None:
        for st in body:
            self._stmt(st, env)

    def _pat_binds(self, pat, env: Env) -> None:
        from ksb.ast_nodes import PatBind, PatList, PatMap

        if isinstance(pat, PatBind):
            env.vars[pat.name] = ANY
        elif isinstance(pat, PatList):
            for el in pat.elts:
                self._pat_binds(el, env)
            if pat.rest:
                env.vars[pat.rest] = LIST
        elif isinstance(pat, PatMap):
            for _, p in pat.entries:
                self._pat_binds(p, env)

    def _expr(self, e: Expr | None, env: Env) -> str:
        if e is None:
            return UNIT
        if isinstance(e, Literal):
            return {
                "int": INT,
                "float": FLOAT,
                "str": STR,
                "bool": BOOL,
                "null": UNIT,
            }.get(e.kind, ANY)
        if isinstance(e, Name):
            if e.id in env.vars:
                return env.vars[e.id]
            if e.id in env.fns:
                return ANY  # function value
            # allow builtins used bare
            if e.id in ("len", "str", "int", "float", "bool", "list", "dict", "print"):
                return ANY
            self._err(f"unknown name '{e.id}'", e)
            return ANY
        if isinstance(e, ListLit):
            for x in e.elts:
                self._expr(x, env)
            return LIST
        if isinstance(e, MapLit):
            for _, v in e.entries:
                self._expr(v, env)
            return MAP
        if isinstance(e, BinOp):
            lt = self._expr(e.left, env)
            rt = self._expr(e.right, env)
            if e.op in ("+", "-", "*", "/", "%"):
                if e.op == "+" and (lt == STR or rt == STR):
                    if lt not in (STR, ANY) or rt not in (STR, ANY):
                        if not (lt == STR and rt == STR):
                            # allow any+ for agent flexibility if one is any
                            if lt != ANY and rt != ANY and {lt, rt} != {STR}:
                                if STR not in (lt, rt):
                                    pass
                    if lt == STR or rt == STR:
                        if lt not in (STR, ANY) or rt not in (STR, ANY):
                            self._err(f"cannot {e.op} {lt} and {rt}", e)
                        return STR
                if lt not in (INT, FLOAT, ANY, NUM) or rt not in (INT, FLOAT, ANY, NUM):
                    if lt not in (ANY,) and rt not in (ANY,):
                        self._err(f"numeric op '{e.op}' on {lt} and {rt}", e)
                return FLOAT if e.op == "/" else unify(lt, rt) if lt != ANY and rt != ANY else ANY
            if e.op in ("==", "!=", "<", ">", "<=", ">="):
                return BOOL
            if e.op in ("&&", "||"):
                return BOOL
            return ANY
        if isinstance(e, UnaryOp):
            t = self._expr(e.expr, env)
            if e.op == "!":
                return BOOL
            return t
        if isinstance(e, Call):
            return self._call(e, env)
        if isinstance(e, Index):
            self._expr(e.target, env)
            self._expr(e.index, env)
            return ANY
        if isinstance(e, Attr):
            base = self._expr(e.target, env)
            # module.attr
            if isinstance(e.target, Name):
                mod = e.target.id
                if mod in RUNTIME and e.attr in RUNTIME[mod]:
                    return RUNTIME[mod][e.attr]
                # imported local module — unknown attrs ok as any
            return ANY
        if isinstance(e, Pipe):
            self._expr(e.left, env)
            self._expr(e.right, env)
            return ANY
        if isinstance(e, Lambda):
            return ANY
        if isinstance(e, Match):
            self._expr(e.scrut, env)
            for arm in e.arms:
                local = env.copy()
                self._pat_binds(arm.pat, local)
                self._block(arm.body, local)
            return ANY
        return ANY

    def _call(self, e: Call, env: Env) -> str:
        # f(args)
        if isinstance(e.func, Name):
            name = e.func.id
            if name in env.fns:
                sig = env.fns[name]
                if len(e.args) != len(sig.params):
                    self._err(
                        f"'{name}' expects {len(sig.params)} arg(s), got {len(e.args)}",
                        e,
                    )
                for arg, expect in zip(e.args, sig.params):
                    got = self._expr(arg, env)
                    if not compatible(got, expect):
                        self._err(f"'{name}' arg type {got}, expected {expect}", e)
                return sig.ret
            for a in e.args:
                self._expr(a, env)
            return ANY
        # mod.fn(args) via Attr
        if isinstance(e.func, Attr) and isinstance(e.func.target, Name):
            mod = e.func.target.id
            attr = e.func.attr
            for a in e.args:
                self._expr(a, env)
            if mod in RUNTIME and attr in RUNTIME[mod]:
                return RUNTIME[mod][attr]
            return ANY
        self._expr(e.func, env)
        for a in e.args:
            self._expr(a, env)
        return ANY


def _import_name(module: str) -> str:
    """`./lib/util` → `util`, `fs` → `fs`."""
    m = module.replace("\\", "/").rstrip("/")
    if m.endswith(".ksb"):
        m = m[:-4]
    return m.split("/")[-1]


def typecheck(mod: Module, *, path: str | None = None) -> list[TypeError_]:
    return TypeChecker(path=path or mod.path).check(mod)


def typecheck_source(source: str, *, path: str | None = None) -> list[TypeError_]:
    from ksb.parser import parse

    return typecheck(parse(source, path=path), path=path)
