"""Recursive-descent parser for KSB."""

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
    MatchArm,
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
from ksb.errors import ParseError
from ksb.lexer import lex
from ksb.tokens import Tok, Token


class Parser:
    def __init__(self, tokens: list[Token], *, path: str | None = None) -> None:
        self.tokens = tokens
        self.path = path
        self.i = 0

    def parse(self) -> Module:
        body: list[Stmt] = []
        self._skip_seps()
        while not self._check(Tok.EOF):
            body.append(self._toplevel())
            self._skip_seps()
        return Module(body=body, path=self.path, line=1, col=1)

    def _toplevel(self) -> Stmt:
        if self._check(Tok.TILDE):
            return self._import()
        if self._check(Tok.AT):
            return self._fn()
        return self._stmt()

    def _import(self) -> Import:
        t = self._expect(Tok.TILDE)
        # ~ fs  |  ~ util  |  ~ "lib/util"  |  ~ ./lib/util (as ident path via string)
        if self._check(Tok.STRING):
            name = str(self._adv().value)
        elif self._check(Tok.IDENT):
            # allow dotted-ish paths as single ident only; use string for subdirs
            name = str(self._adv().value)
            # ~ ./x not possible as ident; optional slash path: IDENT ( '/' IDENT )*
            while self._match(Tok.SLASH):
                part = self._expect(Tok.IDENT)
                name = name + "/" + str(part.value)
        else:
            raise ParseError(
                "E16",
                "expected module name after ~",
                line=self._cur().line,
                col=self._cur().col,
                path=self.path,
            )
        self._end_stmt()
        return Import(module=name, line=t.line, col=t.col)

    def _fn(self) -> FnDef:
        at = self._expect(Tok.AT)
        name = self._expect(Tok.IDENT)
        self._expect(Tok.LPAREN)
        params: list[tuple[str, str | None]] = []
        if not self._check(Tok.RPAREN):
            params.append(self._param())
            while self._match(Tok.COMMA):
                params.append(self._param())
        self._expect(Tok.RPAREN)
        ret: str | None = None
        if self._match(Tok.ARROW):
            ret = str(self._expect(Tok.IDENT).value)
        body = self._block()
        return FnDef(name=str(name.value), params=params, ret_type=ret, body=body, line=at.line, col=at.col)

    def _param(self) -> tuple[str, str | None]:
        name = str(self._expect(Tok.IDENT).value)
        typ: str | None = None
        if self._match(Tok.COLON):
            typ = str(self._expect(Tok.IDENT).value)
        return name, typ

    def _block(self) -> list[Stmt]:
        self._expect(Tok.LBRACE)
        stmts: list[Stmt] = []
        self._skip_seps()
        while not self._check(Tok.RBRACE) and not self._check(Tok.EOF):
            stmts.append(self._stmt())
            self._skip_seps()
        self._expect(Tok.RBRACE)
        return stmts

    def _stmt(self) -> Stmt:
        if self._check(Tok.EQ):
            return self._assign()
        if self._check(Tok.CARET):
            return self._return()
        if self._check(Tok.QMARK):
            return self._if()
        if self._check(Tok.STAR):
            return self._loop()
        if self._check(Tok.HASH):
            m = self._match_expr()
            self._end_stmt()
            return m
        if self._check(Tok.BANG) and self._peek_kind(1) is Tok.DOT:
            t = self._adv()
            self._adv()  # .
            self._end_stmt()
            return Break(line=t.line, col=t.col)
        if self._check(Tok.DOT) and self._peek_kind(1) is Tok.DOT:
            t = self._adv()
            self._adv()
            self._end_stmt()
            return Continue(line=t.line, col=t.col)
        # expression statement
        e = self._expr()
        self._end_stmt()
        return ExprStmt(expr=e, line=e.line, col=e.col)

    def _assign(self) -> Assign:
        t = self._expect(Tok.EQ)
        name = self._expect(Tok.IDENT)
        value = self._expr()
        self._end_stmt()
        return Assign(name=str(name.value), value=value, line=t.line, col=t.col)

    def _return(self) -> Return:
        t = self._expect(Tok.CARET)
        if (
            self._check(Tok.SEMI)
            or self._check(Tok.NEWLINE)
            or self._check(Tok.RBRACE)
            or self._check(Tok.EOF)
        ):
            self._end_stmt()
            return Return(value=None, line=t.line, col=t.col)
        value = self._expr()
        self._end_stmt()
        return Return(value=value, line=t.line, col=t.col)

    def _if(self) -> If:
        t = self._expect(Tok.QMARK)
        cond = self._expr()
        then_body = self._block()
        else_body: list[Stmt] | None = None
        if self._check(Tok.LBRACE):
            else_body = self._block()
        self._end_stmt()
        return If(cond=cond, then_body=then_body, else_body=else_body, line=t.line, col=t.col)

    def _loop(self) -> Stmt:
        t = self._expect(Tok.STAR)
        # foreach: * IDENT : expr { }
        if self._check(Tok.IDENT) and self._peek_kind(1) is Tok.COLON:
            var = str(self._expect(Tok.IDENT).value)
            self._expect(Tok.COLON)
            it = self._expr()
            body = self._block()
            self._end_stmt()
            return ForEach(var=var, iter=it, body=body, line=t.line, col=t.col)
        cond = self._expr()
        body = self._block()
        self._end_stmt()
        return While(cond=cond, body=body, line=t.line, col=t.col)

    def _match_expr(self) -> Match:
        """`# scrut { arm; arm }` arms: `pat => expr` | `pat => { stmts }`"""
        t = self._expect(Tok.HASH)
        scrut = self._expr()
        self._expect(Tok.LBRACE)
        arms: list[MatchArm] = []
        self._skip_seps()
        while not self._check(Tok.RBRACE) and not self._check(Tok.EOF):
            arms.append(self._match_arm())
            self._skip_seps()
        self._expect(Tok.RBRACE)
        if not arms:
            raise ParseError("E13", "match needs at least one arm", line=t.line, col=t.col, path=self.path)
        return Match(scrut=scrut, arms=arms, line=t.line, col=t.col)

    def _match_arm(self) -> MatchArm:
        pat = self._pattern()
        arrow = self._expect(Tok.FATARROW)
        if self._check(Tok.LBRACE):
            body = self._block()
        else:
            # bare expression arm → return value (works as match-expr)
            e = self._expr()
            body = [Return(value=e, line=e.line, col=e.col)]
        self._match(Tok.SEMI)
        return MatchArm(pat=pat, body=body, line=arrow.line, col=arrow.col)

    def _pattern(self) -> Pat:
        t = self._cur()
        # list
        if self._check(Tok.LBRACK):
            return self._pat_list()
        # map
        if self._check(Tok.LBRACE):
            return self._pat_map()
        # literals
        if self._match(Tok.INT):
            return PatLiteral(value=t.value, kind="int", line=t.line, col=t.col)
        if self._match(Tok.FLOAT):
            return PatLiteral(value=t.value, kind="float", line=t.line, col=t.col)
        if self._match(Tok.STRING):
            return PatLiteral(value=t.value, kind="str", line=t.line, col=t.col)
        if self._check(Tok.IDENT):
            name = str(t.value)
            self._adv()
            if name == "_":
                return PatWildcard(line=t.line, col=t.col)
            if name == "T":
                return PatLiteral(value=True, kind="bool", line=t.line, col=t.col)
            if name == "F":
                return PatLiteral(value=False, kind="bool", line=t.line, col=t.col)
            if name == "N":
                return PatLiteral(value=None, kind="null", line=t.line, col=t.col)
            return PatBind(name=name, line=t.line, col=t.col)
        # unary minus number
        if self._match(Tok.MINUS):
            num = self._cur()
            if self._match(Tok.INT):
                return PatLiteral(value=-int(num.value), kind="int", line=t.line, col=t.col)
            if self._match(Tok.FLOAT):
                return PatLiteral(value=-float(num.value), kind="float", line=t.line, col=t.col)
            raise ParseError("E14", "expected number after '-' in pattern", line=t.line, col=t.col, path=self.path)
        raise ParseError(
            "E14",
            f"expected pattern, got {t.kind.name}",
            line=t.line,
            col=t.col,
            path=self.path,
        )

    def _pat_list(self) -> PatList:
        t = self._expect(Tok.LBRACK)
        elts: list[Pat] = []
        rest: str | None = None
        if not self._check(Tok.RBRACK):
            # *rest alone or first elt
            if self._check(Tok.STAR):
                self._adv()
                rest = str(self._expect(Tok.IDENT).value)
            else:
                elts.append(self._pattern())
                while self._match(Tok.COMMA):
                    if self._check(Tok.RBRACK):
                        break
                    if self._check(Tok.STAR):
                        self._adv()
                        rest = str(self._expect(Tok.IDENT).value)
                        break
                    elts.append(self._pattern())
        self._expect(Tok.RBRACK)
        return PatList(elts=elts, rest=rest, line=t.line, col=t.col)

    def _pat_map(self) -> PatMap:
        t = self._expect(Tok.LBRACE)
        entries: list[tuple[str, Pat]] = []
        if not self._check(Tok.RBRACE):
            entries.append(self._pat_map_entry())
            while self._match(Tok.COMMA):
                if self._check(Tok.RBRACE):
                    break
                entries.append(self._pat_map_entry())
        self._expect(Tok.RBRACE)
        return PatMap(entries=entries, line=t.line, col=t.col)

    def _pat_map_entry(self) -> tuple[str, Pat]:
        if self._check(Tok.IDENT):
            key = str(self._adv().value)
        elif self._check(Tok.STRING):
            key = str(self._adv().value)
        else:
            t = self._cur()
            raise ParseError("E15", "expected map pattern key", line=t.line, col=t.col, path=self.path)
        self._expect(Tok.COLON)
        return key, self._pattern()

    # --- expressions (Pratt-ish layered) ---

    def _expr(self) -> Expr:
        return self._pipe()

    def _pipe(self) -> Expr:
        left = self._or()
        while not self._at_line_boundary() and self._match(Tok.PIPE):
            right = self._or()
            left = Pipe(left=left, right=right, line=left.line, col=left.col)
        return left

    def _or(self) -> Expr:
        left = self._and()
        while not self._at_line_boundary() and self._match(Tok.OR):
            right = self._and()
            left = BinOp(op="||", left=left, right=right, line=left.line, col=left.col)
        return left

    def _and(self) -> Expr:
        left = self._cmp()
        while not self._at_line_boundary() and self._match(Tok.AND):
            right = self._cmp()
            left = BinOp(op="&&", left=left, right=right, line=left.line, col=left.col)
        return left

    def _cmp(self) -> Expr:
        left = self._add()
        while not self._at_line_boundary():
            if self._match(Tok.EQEQ):
                op = "=="
            elif self._match(Tok.NE):
                op = "!="
            elif self._match(Tok.LE):
                op = "<="
            elif self._match(Tok.GE):
                op = ">="
            elif self._match(Tok.LT):
                op = "<"
            elif self._match(Tok.GT):
                op = ">"
            else:
                break
            right = self._add()
            left = BinOp(op=op, left=left, right=right, line=left.line, col=left.col)
        return left

    def _add(self) -> Expr:
        left = self._mul()
        while not self._at_line_boundary():
            if self._match(Tok.PLUS):
                op = "+"
            elif self._match(Tok.MINUS):
                op = "-"
            else:
                break
            right = self._mul()
            left = BinOp(op=op, left=left, right=right, line=left.line, col=left.col)
        return left

    def _mul(self) -> Expr:
        left = self._unary()
        while not self._at_line_boundary():
            if self._match(Tok.STAR):
                op = "*"
            elif self._match(Tok.SLASH):
                op = "/"
            elif self._match(Tok.PERCENT):
                op = "%"
            else:
                break
            right = self._unary()
            left = BinOp(op=op, left=left, right=right, line=left.line, col=left.col)
        return left

    def _unary(self) -> Expr:
        if self._check(Tok.MINUS) or self._check(Tok.BANG):
            t = self._adv()
            op = str(t.value)
            expr = self._unary()
            return UnaryOp(op=op, expr=expr, line=t.line, col=t.col)
        return self._postfix()

    def _postfix(self) -> Expr:
        expr = self._primary()
        while not self._at_line_boundary():
            if self._match(Tok.LPAREN):
                args: list[Expr] = []
                if not self._check(Tok.RPAREN):
                    args.append(self._expr())
                    while self._match(Tok.COMMA):
                        args.append(self._expr())
                self._expect(Tok.RPAREN)
                expr = Call(func=expr, args=args, line=expr.line, col=expr.col)
            elif self._match(Tok.LBRACK):
                idx = self._expr()
                self._expect(Tok.RBRACK)
                expr = Index(target=expr, index=idx, line=expr.line, col=expr.col)
            elif self._match(Tok.DOT):
                attr = self._expect(Tok.IDENT)
                expr = Attr(target=expr, attr=str(attr.value), line=expr.line, col=expr.col)
            else:
                break
        return expr

    def _primary(self) -> Expr:
        t = self._cur()
        if self._match(Tok.INT):
            return Literal(value=t.value, kind="int", line=t.line, col=t.col)
        if self._match(Tok.FLOAT):
            return Literal(value=t.value, kind="float", line=t.line, col=t.col)
        if self._match(Tok.STRING):
            return Literal(value=t.value, kind="str", line=t.line, col=t.col)
        if self._check(Tok.IDENT):
            name = str(t.value)
            self._adv()
            if name == "T":
                return Literal(value=True, kind="bool", line=t.line, col=t.col)
            if name == "F":
                return Literal(value=False, kind="bool", line=t.line, col=t.col)
            if name == "N":
                return Literal(value=None, kind="null", line=t.line, col=t.col)
            return Name(id=name, line=t.line, col=t.col)
        if self._match(Tok.LPAREN):
            e = self._expr()
            self._expect(Tok.RPAREN)
            return e
        if self._check(Tok.LBRACK):
            return self._list()
        if self._check(Tok.LBRACE):
            return self._map()
        if self._check(Tok.PIPE):
            return self._lambda()
        if self._check(Tok.HASH):
            return self._match_expr()
        raise ParseError(
            "E10",
            f"expected expression, got {t.kind.name}",
            line=t.line,
            col=t.col,
            path=self.path,
        )

    def _list(self) -> ListLit:
        t = self._expect(Tok.LBRACK)
        elts: list[Expr] = []
        if not self._check(Tok.RBRACK):
            elts.append(self._expr())
            while self._match(Tok.COMMA):
                if self._check(Tok.RBRACK):
                    break
                elts.append(self._expr())
        self._expect(Tok.RBRACK)
        return ListLit(elts=elts, line=t.line, col=t.col)

    def _map(self) -> MapLit:
        t = self._expect(Tok.LBRACE)
        entries: list[tuple[str, Expr]] = []
        if not self._check(Tok.RBRACE):
            # require key: value
            if not self._check(Tok.IDENT) and not self._check(Tok.STRING):
                raise ParseError(
                    "E11",
                    "map keys must be identifier or string (or use block after ?/*/@)",
                    line=self._cur().line,
                    col=self._cur().col,
                    path=self.path,
                )
            entries.append(self._map_entry())
            while self._match(Tok.COMMA):
                if self._check(Tok.RBRACE):
                    break
                entries.append(self._map_entry())
        self._expect(Tok.RBRACE)
        return MapLit(entries=entries, line=t.line, col=t.col)

    def _map_entry(self) -> tuple[str, Expr]:
        if self._check(Tok.IDENT):
            key = str(self._adv().value)
        elif self._check(Tok.STRING):
            key = str(self._adv().value)
        else:
            t = self._cur()
            raise ParseError("E11", "expected map key", line=t.line, col=t.col, path=self.path)
        self._expect(Tok.COLON)
        val = self._expr()
        return key, val

    def _lambda(self) -> Lambda:
        t = self._expect(Tok.PIPE)
        param = str(self._expect(Tok.IDENT).value)
        self._expect(Tok.PIPE)
        if self._check(Tok.LBRACE):
            body: list[Stmt] | Expr = self._block()
        else:
            body = self._expr()
        return Lambda(param=param, body=body, line=t.line, col=t.col)

    # --- token helpers ---

    def _cur(self) -> Token:
        return self.tokens[self.i]

    def _peek_kind(self, off: int = 0) -> Tok:
        j = self.i + off
        if j >= len(self.tokens):
            return Tok.EOF
        return self.tokens[j].kind

    def _check(self, kind: Tok) -> bool:
        return self._cur().kind is kind

    def _adv(self) -> Token:
        t = self._cur()
        if t.kind is not Tok.EOF:
            self.i += 1
        return t

    def _match(self, kind: Tok) -> bool:
        if self._check(kind):
            self._adv()
            return True
        return False

    def _expect(self, kind: Tok) -> Token:
        if self._check(kind):
            return self._adv()
        t = self._cur()
        raise ParseError(
            "E12",
            f"expected {kind.name}, got {t.kind.name}",
            line=t.line,
            col=t.col,
            path=self.path,
        )

    def _optional_semi(self) -> None:
        self._match(Tok.SEMI)

    def _skip_seps(self) -> None:
        while self._check(Tok.SEMI) or self._check(Tok.NEWLINE):
            self._adv()

    def _end_stmt(self) -> None:
        """Consume optional ; and leave newlines for the outer skip."""
        self._match(Tok.SEMI)

    def _at_line_boundary(self) -> bool:
        """True if next token is newline/EOF — binops must not cross lines."""
        return self._check(Tok.NEWLINE) or self._check(Tok.EOF)


def parse(source: str, *, path: str | None = None) -> Module:
    tokens = lex(source, path=path)
    return Parser(tokens, path=path).parse()
