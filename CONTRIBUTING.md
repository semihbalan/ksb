# Contributing to KSB

Thanks for helping improve KSB — a dense language for AI agents.

## Dev setup

```bash
git clone https://github.com/semihbalan/ksb.git
cd ksb
pip install -e ".[dev]"
pytest -q
```

## Layout

| Path | Role |
|------|------|
| `src/ksb/lexer.py` | Tokenizer |
| `src/ksb/parser.py` | Recursive-descent parser |
| `src/ksb/codegen.py` | Python emitter |
| `src/ksb/fmt.py` | Pretty printer |
| `src/ksb/typecheck.py` | Optional type checks |
| `src/ksb/modules.py` | Local `~ mod` resolution |
| `src/ksb/runtime/ksb_rt.py` | Agent stdlib |
| `examples/` | Sample programs |
| `KSB.md` | Agent prompt card (keep short) |

## Guidelines

1. Keep agent errors short (`ksb:E## file:line:col message`).
2. Prefer small, test-covered changes.
3. Update `KSB.md` if you change surface syntax.
4. MIT license — by contributing you agree your changes are MIT.

## PR checklist

- [ ] `pytest -q` passes
- [ ] New syntax has an example under `examples/`
- [ ] README / KSB.md updated if needed
