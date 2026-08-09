# KSB — Kernel Script for Bots

**Ultra-dense scripting language for AI agents.** Fewer tokens than Python for tool scripts. Compiles to **Python 3**.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-green.svg)](https://www.python.org/downloads/)

```ksb
@ max(a:i,b:i)->i {
  ? a>b { ^a } { ^b }
}
@ main()->i { ^ max(3,7) }
```

Dense form:

```ksb
@max(a:i,b:i)->i{?a>b{^a}{^b}}
@main()->i{^max(3,7)}
```

## Why KSB?

| Problem for agents | KSB |
|--------------------|-----|
| Long keywords burn tokens | `@` `^` `?` `*` `#` |
| Huge stdlib surface | Small agent runtime |
| Style noise | `ksb fmt` + rigid grammar |
| Silent type mistakes | `ksb check` optional types |

Paste [`KSB.md`](./KSB.md) into an agent system prompt (~400 tokens).

## Install

```bash
pip install -e ".[dev]"   # from clone
# or later: pip install ksb
ksb -V
```

## CLI

```bash
ksb run examples/hello.ksb
ksb run examples/match.ksb
ksb run examples/use_mod.ksb
ksb run examples/agent_kit.ksb

ksb build app.ksb -o app.py
ksb fmt app.ksb          # pretty-print to stdout
ksb fmt app.ksb -w       # write back
ksb check app.ksb        # typecheck
ksb parse app.ksb
ksb lex app.ksb
```

## Language (cheat sheet)

| Syntax | Meaning |
|--------|---------|
| `@ f(a:i)->i { ... }` | function |
| `^ e` | return |
| `= x e` | bind |
| `? c {t} {f}` | if / else |
| `* c { ... }` | while |
| `* x:xs { ... }` | for-each |
| `# e { p => v; _ => v }` | match |
| `a \| f` | pipe → `f(a)` |
| `~ fs` / `~ "lib/mathx"` | import runtime or local `.ksb` |
| `T` `F` `N` | true / false / null |

**Patterns:** `_` · literals · bind `n` · `[h,*t]` · `{ok:T, msg:m}`

**Types (optional):** `i` `f` `s` `b` `l` `m` `a`

## Runtime modules

| Module | Highlights |
|--------|------------|
| `fs` | read, write, exists, list, mkdir, remove, copy, cwd |
| `http` | get, post, put, delete, get_json, post_json |
| `json` | parse, dump |
| `sh` | run |
| `env` | get, set |
| `log` | info, err |
| `time` | now, ms, sleep, iso |
| `path` | join, dirname, basename, abs, ext |
| `cli` | args, argc, arg |
| `str` | split, join, trim, replace, contains, lower, upper |
| `tool` | ok, err, wrap — agent result shapes |

## Local modules

```ksb
// lib/mathx.ksb
@ add(a:i,b:i)->i { ^ a+b }

// app.ksb
~ "lib/mathx"
@ main()->i { ^ add(1,2) }
```

Functions from imported `.ksb` files are inlined at compile time (no `main` import).

## Architecture

```
.ksb → lex → parse → [bundle local mods] → [typecheck] → codegen → Python 3
                                              ↓
                                    ksb.runtime (agent stdlib)
```

## Development

```bash
pip install -e ".[dev]"
pytest -q
```

See [CONTRIBUTING.md](./CONTRIBUTING.md).

## License

[MIT](./LICENSE) — free for humans and agents.
