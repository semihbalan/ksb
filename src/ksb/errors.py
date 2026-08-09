"""Short, agent-friendly errors."""

from __future__ import annotations


class KsbError(Exception):
    """Base KSB error with optional source location."""

    def __init__(
        self,
        code: str,
        message: str,
        *,
        line: int | None = None,
        col: int | None = None,
        path: str | None = None,
    ) -> None:
        self.code = code
        self.message = message
        self.line = line
        self.col = col
        self.path = path
        super().__init__(self.format())

    def format(self) -> str:
        loc = ""
        if self.path:
            loc += self.path
        if self.line is not None:
            loc += f":{self.line}"
            if self.col is not None:
                loc += f":{self.col}"
        if loc:
            return f"ksb:{self.code} {loc} {self.message}"
        return f"ksb:{self.code} {self.message}"


class LexError(KsbError):
    pass


class ParseError(KsbError):
    pass


class CodegenError(KsbError):
    pass


class TypeCheckError(KsbError):
    pass
