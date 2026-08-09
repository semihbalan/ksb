from ksb.codegen import compile_source


def test_max_transpile():
    py = compile_source(
        """
@ max(a:i,b:i)->i {
  ? a>b { ^a } { ^b }
}
@ main()->i {
  ^ max(3,7)
}
"""
    )
    assert "def max(a, b):" in py
    assert "if (a > b):" in py
    assert "return a" in py
    assert "def main():" in py
    ns: dict = {}
    exec(py, ns, ns)
    assert ns["main"]() == 7


def test_pipe():
    py = compile_source(
        """
@ double(x:i)->i { ^ x*2 }
@ main()->i { ^ 3 | double }
"""
    )
    ns: dict = {}
    exec(py, ns, ns)
    assert ns["main"]() == 6


def test_sum_loop():
    py = compile_source(
        """
@ sum(xs:l)->i {
  = n 0
  * x:xs { = n n+x }
  ^ n
}
@ main()->i { ^ sum([1,2,3,4,5]) }
"""
    )
    ns: dict = {}
    exec(py, ns, ns)
    assert ns["main"]() == 15
