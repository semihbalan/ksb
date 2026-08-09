from ksb.fmt import format_source


def test_fmt_dense_max():
    dense = "@max(a:i,b:i)->i{?a>b{^a}{^b}}"
    out = format_source(dense)
    assert "@ max(" in out or "@ max" in out
    assert "? " in out
    assert "^ a" in out
    # round-trip parse
    from ksb.parser import parse
    from ksb.codegen import compile_source

    parse(out)
    ns: dict = {}
    exec(compile_source(out, bundle=False), ns, ns)
    assert ns["max"](3, 9) == 9
