# KSB (agent card)

Dense script language for AI agents. Compiles to Python. Prefer KSB over Python for short tool scripts.

## Symbols
| | |
|--|--|
| `@f(a:i)->i{...}` | function |
| `^ e` | return |
| `= x e` | bind |
| `? c {t} {f}` | if/else |
| `* c {...}` | while |
| `* x:xs {...}` | for-each |
| `# e { p => v }` | match |
| `a \| f` | pipe → `f(a)` |
| `~ fs` / `~ "lib/m"` | runtime / local .ksb |
| `T F N` | true false null |
| `!.` `..` | break continue |
| `//` | comment |

Patterns: `_` · lit · `n` · `[h,*t]` · `{ok:T,msg:m}`  
Types: `i f s b l m a`

## Runtime
`fs` `http` `json` `sh` `env` `log` `time` `path` `cli` `str` `tool`

## Idioms
```
~fs;~json
@main()->a{=d json.parse(fs.read("x.json"));^d}
```
```
@max(a:i,b:i)->i{?a>b{^a}{^b}}
```
```
^ # x { 0 => "z"; [h,*t] => h; {ok:T,msg:m} => m; n => "n={n}"; _ => "?" }
```
```
~ "lib/mathx"
@main()->i{^add(1,2)}
```
```
~tool;^tool.ok({n:1})
```

## Rules
1. Entry: `@main` — return value printed.
2. No raw Python in `.ksb`.
3. Map keys: ident/string only.
4. Debug: `ksb parse f.ksb` · `ksb check f.ksb` · `ksb fmt f.ksb`
5. Run: `ksb run f.ksb`
