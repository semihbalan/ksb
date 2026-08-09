"""User module resolution: `~ util` loads util.ksb beside the importer."""

from __future__ import annotations

from pathlib import Path

from ksb.ast_nodes import FnDef, Import, Module, Stmt
from ksb.errors import KsbError
from ksb.parser import parse

# Built-in runtime modules (not .ksb files)
RUNTIME_MODULES = frozenset(
    {
        "fs",
        "http",
        "json",
        "sh",
        "env",
        "log",
        "time",
        "path",
        "cli",
        "tool",
        "str",
    }
)


def is_runtime(name: str) -> bool:
    base = name.replace("\\", "/").split("/")[-1]
    if base.endswith(".ksb"):
        base = base[:-4]
    return base in RUNTIME_MODULES and "/" not in name.replace("\\", "/") and not name.startswith(".")


def resolve_module_path(spec: str, from_file: Path | None) -> Path:
    """Resolve a local module spec to a .ksb path."""
    s = spec.replace("\\", "/")
    if s.endswith(".ksb"):
        rel = s
    else:
        rel = s + ".ksb"
    candidates: list[Path] = []
    if from_file is not None:
        base = from_file.parent
        candidates.append((base / rel).resolve())
        candidates.append((base / s / "mod.ksb").resolve())
    candidates.append(Path(rel).resolve())
    for c in candidates:
        if c.is_file():
            return c
    raise KsbError(
        "E50",
        f"module not found: {spec} (looked for {rel})",
        path=str(from_file) if from_file else None,
    )


def load_bundle(entry: Path, *, source: str | None = None) -> Module:
    """Parse entry and inline local `~ mod` imports (fn defs only).

    Runtime imports (`~ fs`) stay as Import nodes.
    Local modules' functions are merged into the module body (before user code).
    """
    entry = entry.resolve()
    text = source if source is not None else entry.read_text(encoding="utf-8")
    root = parse(text, path=str(entry))
    return bundle_module(root, entry)


def bundle_module(mod: Module, entry: Path, *, _stack: set[str] | None = None) -> Module:
    stack = _stack if _stack is not None else set()
    key = str(entry.resolve())
    if key in stack:
        raise KsbError("E51", f"circular import: {entry.name}", path=str(entry))
    stack.add(key)

    runtime_imports: list[Import] = []
    local_fns: list[FnDef] = []
    other: list[Stmt] = []
    seen_runtime: set[str] = set()
    seen_fns: set[str] = set()

    for stmt in mod.body:
        if isinstance(stmt, Import):
            spec = stmt.module
            if is_runtime(spec) or (spec in RUNTIME_MODULES):
                base = spec
                if base not in seen_runtime:
                    runtime_imports.append(Import(module=base, line=stmt.line, col=stmt.col))
                    seen_runtime.add(base)
            else:
                path = resolve_module_path(spec, entry)
                child = parse(path.read_text(encoding="utf-8"), path=str(path))
                child = bundle_module(child, path, _stack=stack)
                for cstmt in child.body:
                    if isinstance(cstmt, Import):
                        if cstmt.module not in seen_runtime and is_runtime(cstmt.module):
                            runtime_imports.append(cstmt)
                            seen_runtime.add(cstmt.module)
                    elif isinstance(cstmt, FnDef):
                        if cstmt.name == "main":
                            continue  # do not import main
                        if cstmt.name in seen_fns:
                            raise KsbError(
                                "E52",
                                f"duplicate function '{cstmt.name}' from module {spec}",
                                path=str(entry),
                                line=stmt.line,
                                col=stmt.col,
                            )
                        seen_fns.add(cstmt.name)
                        local_fns.append(cstmt)
        else:
            if isinstance(stmt, FnDef):
                if stmt.name in seen_fns:
                    raise KsbError(
                        "E52",
                        f"duplicate function '{stmt.name}'",
                        path=str(entry),
                        line=stmt.line,
                        col=stmt.col,
                    )
                seen_fns.add(stmt.name)
            other.append(stmt)

    stack.discard(key)
    body: list[Stmt] = [*runtime_imports, *local_fns, *other]
    return Module(body=body, path=mod.path or str(entry), line=mod.line, col=mod.col)
