from pathlib import Path

from ksb.cli import cmd_run, cmd_build
from ksb.codegen import compile_source

ROOT = Path(__file__).resolve().parents[1]
EX = ROOT / "examples"


def test_hello_run(tmp_path, monkeypatch, capsys):
    code = (EX / "hello.ksb").read_text(encoding="utf-8")
    py = compile_source(code, path="hello.ksb")
    ns: dict = {"__name__": "__main__"}
    exec(py, ns, ns)
    # main exists
    assert ns["main"]() == "hello ksb"


def test_examples_compile():
    for p in EX.glob("*.ksb"):
        if p.name.startswith("_"):
            continue
        src = p.read_text(encoding="utf-8")
        py = compile_source(src, path=str(p))
        assert "def " in py or "from ksb" in py


def test_build_write(tmp_path):
    src = EX / "max.ksb"
    out = tmp_path / "max.py"
    assert cmd_build(src, out) == 0
    assert out.exists()
    ns: dict = {}
    exec(out.read_text(encoding="utf-8"), ns, ns)
    assert ns["main"]() == 7
