from pathlib import Path

from ksb.codegen import compile_source

ROOT = Path(__file__).resolve().parents[1]


def test_local_module_bundle():
    path = ROOT / "examples" / "use_mod.ksb"
    src = path.read_text(encoding="utf-8")
    py = compile_source(src, path=str(path))
    assert "def add(" in py
    assert "def clamp(" in py
    ns: dict = {}
    exec(py, ns, ns)
    assert ns["main"]() == 50
