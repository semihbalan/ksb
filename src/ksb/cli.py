"""KSB command-line interface."""

from __future__ import annotations

import argparse
import json
import sys
import traceback
from pathlib import Path

from ksb import __version__
from ksb.codegen import compile_source
from ksb.errors import KsbError
from ksb.fmt import format_source
from ksb.lexer import lex
from ksb.modules import load_bundle
from ksb.parser import parse
from ksb.tokens import Tok
from ksb.typecheck import typecheck


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="ksb",
        description="KSB — dense scripting language for AI agents (→ Python)",
    )
    parser.add_argument("-V", "--version", action="version", version=f"ksb {__version__}")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_run = sub.add_parser("run", help="transpile and execute a .ksb file")
    p_run.add_argument("file", type=Path)
    p_run.add_argument("args", nargs="*", help="args passed to script (sys.argv)")
    p_run.add_argument("--check", action="store_true", help="typecheck before run")

    p_build = sub.add_parser("build", help="transpile .ksb → .py")
    p_build.add_argument("file", type=Path)
    p_build.add_argument("-o", "--output", type=Path, default=None)
    p_build.add_argument("--check", action="store_true", help="typecheck before build")

    p_parse = sub.add_parser("parse", help="parse and print AST summary")
    p_parse.add_argument("file", type=Path)
    p_parse.add_argument("--json", action="store_true")

    p_lex = sub.add_parser("lex", help="tokenize and print tokens (debug)")
    p_lex.add_argument("file", type=Path)

    p_eval = sub.add_parser("eval", help="eval a KSB snippet")
    p_eval.add_argument("code", help="KSB source (usually @main ...)")

    p_fmt = sub.add_parser("fmt", help="pretty-print KSB source")
    p_fmt.add_argument("file", type=Path)
    p_fmt.add_argument("-w", "--write", action="store_true", help="write back to file")

    p_check = sub.add_parser("check", help="typecheck a .ksb file")
    p_check.add_argument("file", type=Path)

    args = parser.parse_args(argv)

    try:
        if args.cmd == "run":
            return cmd_run(args.file, args.args, check=args.check)
        if args.cmd == "build":
            return cmd_build(args.file, args.output, check=args.check)
        if args.cmd == "parse":
            return cmd_parse(args.file, args.json)
        if args.cmd == "lex":
            return cmd_lex(args.file)
        if args.cmd == "eval":
            return cmd_eval(args.code)
        if args.cmd == "fmt":
            return cmd_fmt(args.file, write=args.write)
        if args.cmd == "check":
            return cmd_check(args.file)
    except KsbError as e:
        print(e.format(), file=sys.stderr)
        return 1
    except Exception as e:  # noqa: BLE001
        print(f"ksb:E99 internal: {e}", file=sys.stderr)
        traceback.print_exc()
        return 1
    return 0


def _read(path: Path) -> str:
    if not path.exists():
        raise KsbError("E30", f"file not found: {path}")
    return path.read_text(encoding="utf-8")


def _maybe_check(path: Path, source: str) -> int:
    from ksb.modules import bundle_module
    from ksb.parser import parse as parse_src

    mod = parse_src(source, path=str(path))
    if path.exists():
        mod = bundle_module(mod, path)
    errs = typecheck(mod, path=str(path))
    for e in errs:
        print(e.format(), file=sys.stderr)
    return len(errs)


def cmd_build(path: Path, output: Path | None, check: bool = False) -> int:
    src = _read(path)
    if check and _maybe_check(path, src):
        return 1
    py = compile_source(src, path=str(path))
    out = output or path.with_suffix(".py")
    out.write_text(py, encoding="utf-8")
    print(f"wrote {out}")
    return 0


def cmd_run(path: Path, script_args: list[str], check: bool = False) -> int:
    src = _read(path)
    if check and _maybe_check(path, src):
        return 1
    py = compile_source(src, path=str(path))
    g: dict = {"__name__": "__main__", "__file__": str(path)}
    code = compile(py, str(path.with_suffix(".py")), "exec")
    old_argv = sys.argv
    sys.argv = [str(path), *script_args]
    try:
        exec(code, g, g)
    finally:
        sys.argv = old_argv
    return 0


def cmd_parse(path: Path, as_json: bool) -> int:
    src = _read(path)
    mod = parse(src, path=str(path))
    if as_json:
        print(json.dumps(_ast_to_json(mod), indent=2, default=str))
    else:
        print(f"module path={mod.path!r} stmts={len(mod.body)}")
        for s in mod.body:
            print(f"  {type(s).__name__}", end="")
            if hasattr(s, "name"):
                print(f" name={getattr(s, 'name')!r}", end="")
            if hasattr(s, "module"):
                print(f" module={getattr(s, 'module')!r}", end="")
            print()
    return 0


def cmd_lex(path: Path) -> int:
    src = _read(path)
    for t in lex(src, path=str(path)):
        if t.kind is Tok.EOF:
            print("EOF")
            break
        if t.kind is Tok.NEWLINE:
            print(f"{t.line}:{t.col}\tNEWLINE")
            continue
        print(f"{t.line}:{t.col}\t{t.kind.name}\t{t.value!r}")
    return 0


def cmd_eval(code: str) -> int:
    py = compile_source(code, path="<eval>", bundle=False)
    g: dict = {"__name__": "__main__"}
    exec(compile(py, "<eval>", "exec"), g, g)
    return 0


def cmd_fmt(path: Path, write: bool = False) -> int:
    src = _read(path)
    out = format_source(src, path=str(path))
    if write:
        path.write_text(out, encoding="utf-8")
        print(f"formatted {path}")
    else:
        sys.stdout.write(out)
    return 0


def cmd_check(path: Path) -> int:
    src = _read(path)
    n = _maybe_check(path, src)
    if n == 0:
        print(f"ok {path}")
        return 0
    print(f"{n} error(s)", file=sys.stderr)
    return 1


def _ast_to_json(obj):
    if obj is None or isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, list):
        return [_ast_to_json(x) for x in obj]
    if isinstance(obj, tuple):
        return [_ast_to_json(x) for x in obj]
    if hasattr(obj, "__dataclass_fields__"):
        d = {"_type": type(obj).__name__}
        for k in obj.__dataclass_fields__:
            d[k] = _ast_to_json(getattr(obj, k))
        return d
    return str(obj)


if __name__ == "__main__":
    raise SystemExit(main())
