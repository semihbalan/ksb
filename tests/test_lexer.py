from ksb.lexer import lex
from ksb.tokens import Tok


def test_basic_tokens():
    toks = lex('@main()->i{^1}')
    kinds = [t.kind for t in toks if t.kind is not Tok.EOF]
    assert Tok.AT in kinds
    assert Tok.IDENT in kinds
    assert Tok.ARROW in kinds
    assert Tok.CARET in kinds
    assert Tok.INT in kinds


def test_string_and_comment():
    toks = lex('// hi\n= x "ab\\nc"')
    strings = [t for t in toks if t.kind is Tok.STRING]
    assert strings[0].value == "ab\nc"


def test_ops():
    toks = lex("a==b!=c<=d>=e&&f||g")
    kinds = [t.kind for t in toks if t.kind is not Tok.EOF]
    assert Tok.EQEQ in kinds
    assert Tok.NE in kinds
    assert Tok.LE in kinds
    assert Tok.AND in kinds
    assert Tok.OR in kinds
