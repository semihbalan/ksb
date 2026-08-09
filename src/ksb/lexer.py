"""Lexer for KSB source."""

from __future__ import annotations

from ksb.errors import LexError
from ksb.tokens import Tok, Token


class Lexer:
    def __init__(self, source: str, *, path: str | None = None) -> None:
        self.source = source
        self.path = path
        self.i = 0
        self.line = 1
        self.col = 1
        self.n = len(source)

    def tokenize(self) -> list[Token]:
        out: list[Token] = []
        while True:
            t = self.next_token()
            out.append(t)
            if t.kind is Tok.EOF:
                break
        return out

    def next_token(self) -> Token:
        self._skip_ws_and_comments()
        if self.i >= self.n:
            return Token(Tok.EOF, None, self.line, self.col)

        line, col = self.line, self.col
        c = self._peek()

        # significant newline (statement boundary)
        if c == "\n":
            self._adv()
            # collapse consecutive newlines / comment-only lines
            while True:
                self._skip_ws_and_comments()
                if self._peek() == "\n":
                    self._adv()
                    continue
                break
            return Token(Tok.NEWLINE, "\\n", line, col)

        # identifiers / bools / null
        if c.isalpha() or c == "_":
            return self._ident(line, col)

        # numbers
        if c.isdigit() or (c == "." and self._peek(1).isdigit()):
            return self._number(line, col)

        # strings
        if c in "\"'":
            return self._string(line, col)

        # two-char ops
        two = self._peek() + self._peek(1)
        multi = {
            "->": Tok.ARROW,
            "=>": Tok.FATARROW,
            "||": Tok.OR,
            "&&": Tok.AND,
            "!=": Tok.NE,
            "==": Tok.EQEQ,
            "<=": Tok.LE,
            ">=": Tok.GE,
        }
        if two in multi:
            self._adv()
            self._adv()
            return Token(multi[two], two, line, col)

        single = {
            "@": Tok.AT,
            "^": Tok.CARET,
            "~": Tok.TILDE,
            "?": Tok.QMARK,
            "#": Tok.HASH,
            "=": Tok.EQ,
            ";": Tok.SEMI,
            ",": Tok.COMMA,
            ":": Tok.COLON,
            ".": Tok.DOT,
            "|": Tok.PIPE,
            "!": Tok.BANG,
            "<": Tok.LT,
            ">": Tok.GT,
            "+": Tok.PLUS,
            "-": Tok.MINUS,
            "*": Tok.STAR,
            "/": Tok.SLASH,
            "%": Tok.PERCENT,
            "(": Tok.LPAREN,
            ")": Tok.RPAREN,
            "{": Tok.LBRACE,
            "}": Tok.RBRACE,
            "[": Tok.LBRACK,
            "]": Tok.RBRACK,
        }
        if c in single:
            self._adv()
            return Token(single[c], c, line, col)

        raise LexError("E01", f"unexpected char {c!r}", line=line, col=col, path=self.path)

    # --- internals ---

    def _peek(self, off: int = 0) -> str:
        j = self.i + off
        if j >= self.n:
            return "\0"
        return self.source[j]

    def _adv(self) -> str:
        if self.i >= self.n:
            return "\0"
        c = self.source[self.i]
        self.i += 1
        if c == "\n":
            self.line += 1
            self.col = 1
        else:
            self.col += 1
        return c

    def _skip_ws_and_comments(self) -> None:
        """Skip spaces/tabs/CR and comments. Newlines become NEWLINE tokens."""
        while self.i < self.n:
            c = self._peek()
            if c in " \t\r":
                self._adv()
                continue
            # line comment //  (newline after comment is still significant)
            if c == "/" and self._peek(1) == "/":
                self._adv()
                self._adv()
                while self.i < self.n and self._peek() != "\n":
                    self._adv()
                continue
            # block comment /* */
            if c == "/" and self._peek(1) == "*":
                line, col = self.line, self.col
                self._adv()
                self._adv()
                closed = False
                while self.i < self.n:
                    if self._peek() == "*" and self._peek(1) == "/":
                        self._adv()
                        self._adv()
                        closed = True
                        break
                    self._adv()
                if not closed:
                    raise LexError("E02", "unterminated block comment", line=line, col=col, path=self.path)
                continue
            break

    def _ident(self, line: int, col: int) -> Token:
        start = self.i
        while self._peek().isalnum() or self._peek() == "_":
            self._adv()
        text = self.source[start : self.i]
        # T F N are literals but still IDENT tokens; parser special-cases
        return Token(Tok.IDENT, text, line, col)

    def _number(self, line: int, col: int) -> Token:
        start = self.i
        is_float = False
        while self._peek().isdigit():
            self._adv()
        if self._peek() == "." and self._peek(1).isdigit():
            is_float = True
            self._adv()
            while self._peek().isdigit():
                self._adv()
        text = self.source[start : self.i]
        if is_float:
            return Token(Tok.FLOAT, float(text), line, col)
        return Token(Tok.INT, int(text), line, col)

    def _string(self, line: int, col: int) -> Token:
        quote = self._adv()
        parts: list[str] = []
        while self.i < self.n:
            c = self._peek()
            if c == "\n":
                raise LexError("E03", "unterminated string", line=line, col=col, path=self.path)
            if c == quote:
                self._adv()
                return Token(Tok.STRING, "".join(parts), line, col)
            if c == "\\":
                self._adv()
                esc = self._adv()
                mapping = {"n": "\n", "t": "\t", "r": "\r", "\\": "\\", '"': '"', "'": "'", "{": "{", "}": "}"}
                if esc not in mapping:
                    raise LexError("E04", f"bad escape \\{esc}", line=self.line, col=self.col, path=self.path)
                parts.append(mapping[esc])
                continue
            parts.append(self._adv())
        raise LexError("E03", "unterminated string", line=line, col=col, path=self.path)


def lex(source: str, *, path: str | None = None) -> list[Token]:
    return Lexer(source, path=path).tokenize()
