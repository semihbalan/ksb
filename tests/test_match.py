from ksb.ast_nodes import Match, PatList, PatLiteral, PatBind, PatWildcard
from ksb.codegen import compile_source
from ksb.parser import parse


def test_parse_match_literal_and_bind():
    mod = parse(
        """
@ f(x)->s {
  ^ # x {
    0 => "z"
    n => "n"
    _ => "?"
  }
}
"""
    )
    fn = mod.body[0]
    ret = fn.body[0]
    m = ret.value
    assert isinstance(m, Match)
    assert len(m.arms) == 3
    assert isinstance(m.arms[0].pat, PatLiteral)
    assert isinstance(m.arms[1].pat, PatBind)
    assert isinstance(m.arms[2].pat, PatWildcard)


def test_parse_list_rest():
    mod = parse("# xs { [h, *t] => h; [] => N }")
    m = mod.body[0]
    assert isinstance(m, Match)
    assert isinstance(m.arms[0].pat, PatList)
    assert m.arms[0].pat.rest == "t"


def test_match_run_classify():
    py = compile_source(
        """
@ classify(x:a)->s {
  ^ # x {
    0 => "zero"
    1 => "one"
    n => "other"
  }
}
@ main()->s { ^ classify(1) }
"""
    )
    ns: dict = {}
    exec(py, ns, ns)
    assert ns["main"]() == "one"
    assert ns["classify"](0) == "zero"
    assert ns["classify"](9) == "other"


def test_match_list_and_map():
    py = compile_source(
        """
@ head(xs:l)->a {
  ^ # xs {
    [] => N
    [h, *t] => h
    _ => N
  }
}
@ st(r:m)->s {
  ^ # r {
    {ok: T, msg: m} => m
    {ok: F, err: e} => e
    _ => "?"
  }
}
@ main()->a {
  ^ [head([5,6]), head([]), st({ok: T, msg: "ok"})]
}
"""
    )
    ns: dict = {}
    exec(py, ns, ns)
    assert ns["main"]() == [5, None, "ok"]


def test_match_stmt_side_effect():
    py = compile_source(
        """
@ main()->i {
  = n 0
  # 1 {
    1 => { = n 42 }
    _ => { = n -1 }
  }
  ^ n
}
"""
    )
    ns: dict = {}
    exec(py, ns, ns)
    assert ns["main"]() == 42
