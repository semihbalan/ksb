from ksb.ast_nodes import FnDef, If, ForEach, Import, Module
from ksb.parser import parse


def test_fn_if():
    mod = parse("@ max(a:i,b:i)->i { ? a>b { ^a } { ^b } }")
    assert isinstance(mod, Module)
    fn = mod.body[0]
    assert isinstance(fn, FnDef)
    assert fn.name == "max"
    assert len(fn.params) == 2
    assert isinstance(fn.body[0], If)


def test_foreach_import():
    mod = parse("~ fs\n@ main() { * x:xs { = n n+x } }")
    assert isinstance(mod.body[0], Import)
    assert mod.body[0].module == "fs"
    fn = mod.body[1]
    assert isinstance(fn, FnDef)
    assert isinstance(fn.body[0], ForEach)


def test_dense():
    mod = parse("@max(a:i,b:i)->i{?a>b{^a}{^b}}")
    assert isinstance(mod.body[0], FnDef)
