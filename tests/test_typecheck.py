from ksb.typecheck import typecheck_source


def test_ok_annotated():
    errs = typecheck_source(
        """
@ add(a:i,b:i)->i { ^ a+b }
@ main()->i { ^ add(1,2) }
"""
    )
    assert errs == []


def test_arity_error():
    errs = typecheck_source(
        """
@ add(a:i,b:i)->i { ^ a+b }
@ main()->i { ^ add(1) }
"""
    )
    assert any("expects 2" in e.message for e in errs)


def test_unknown_name():
    errs = typecheck_source("@ main() { ^ missing }")
    assert any("unknown name" in e.message for e in errs)
