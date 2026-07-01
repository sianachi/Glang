"""Differential test for the self-hosted expression parser (expr_parser.lang).

Each expression is parsed by both the Python ExprParser and the Glang one (via
compiler/expr_dump.lang, run through the interpreter); their canonical S-expr
forms must agree.  show_expr below is the exact Python twin of ast.lang::showExpr.
Closures are excluded — their bodies are statements, handled in a later slice.
"""

import os
import subprocess
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from lexer.lexer import Lexer
from parser.token_stream import TokenStream
from parser.type_parser import TypeParser
from parser.expr_parser import ExprParser
from parser import ast_nodes as A
from compiler.ast_serializer import _type_str

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _targs(ta):
    return "" if not ta else "<" + ",".join(_type_str(t) for t in ta) + ">"


def _args(args):
    return "[" + " ".join(show_expr(a) for a in args) + "]"


def show_expr(e) -> str:
    if isinstance(e, A.LiteralExpr):     return f"lit:{e.kind}:{e.value}"
    if isinstance(e, A.IdentifierExpr):  return f"id:{e.name}"
    if isinstance(e, A.NullExpr):        return "null"
    if isinstance(e, A.ThisExpr):        return "this"
    if isinstance(e, A.SuperExpr):       return "super"
    if isinstance(e, A.UnaryExpr):       return f"(u {e.op} {show_expr(e.operand)})"
    if isinstance(e, A.BinaryExpr):      return f"(b {e.op} {show_expr(e.left)} {show_expr(e.right)})"
    if isinstance(e, A.TernaryExpr):     return f"(?: {show_expr(e.cond)} {show_expr(e.then_expr)} {show_expr(e.else_expr)})"
    if isinstance(e, A.AddressOfExpr):   return f"(addr {show_expr(e.operand)})"
    if isinstance(e, A.DerefExpr):       return f"(deref {show_expr(e.operand)})"
    if isinstance(e, A.CastExpr):        return f"(cast {_type_str(e.target_type)} {show_expr(e.expr)})"
    if isinstance(e, A.CallExpr):        return f"(call {e.name}{_targs(e.type_args)} {_args(e.args)})"
    if isinstance(e, A.IndirectCallExpr):return f"(icall {show_expr(e.callee)} {_args(e.args)})"
    if isinstance(e, A.MethodCallExpr):
        sep = "->" if e.is_arrow else "."
        return f"(mcall {sep}{e.method} {show_expr(e.object)} {_args(e.args)})"
    if isinstance(e, A.NewExpr):         return f"(new {e.class_name}{_targs(e.type_args)} {_args(e.args)})"
    if isinstance(e, A.DeleteExpr):      return f"(delete {show_expr(e.operand)})"
    if isinstance(e, A.AllocExpr):
        cs = show_expr(e.count) if e.count is not None else "_"
        return f"(alloc {_type_str(e.type)} {cs})"
    if isinstance(e, A.FreeExpr):        return f"(free {show_expr(e.operand)})"
    if isinstance(e, A.FieldAccessExpr): return f"(field {e.field_name} {show_expr(e.object)})"
    if isinstance(e, A.ArrowAccessExpr): return f"(arrow {e.field_name} {show_expr(e.pointer)})"
    if isinstance(e, A.IndexExpr):       return f"(index {show_expr(e.array)} {show_expr(e.index)})"
    raise AssertionError(f"unhandled expr {type(e).__name__}")


EXPRS = [
    # literals / atoms
    "42", "3.14", "true", "false", "null", "'a'", '"hi"', "foo", "a::b::c", "this", "super",
    # precedence
    "1 + 2 * 3", "1 * 2 + 3", "a || b && c", "1 << 2 + 3", "a == b != c",
    "a ?? b ?? c", "a | b & c ^ d", "1 + 2 + 3", "2 * 3 % 4",
    "a < b", "a <= b == c",
    # unary / prefix
    "-x", "!a", "~b", "++x", "--y", "*p", "&x", "- -x", "!!a", "*&p",
    # postfix chains
    "a.b", "p->q", "arr[i]", "a.b.c", "m[k][j]",
    "f(1, 2)", "f()", "obj.m(1, 2)", "p->m()", "a.b().c->d(1)[2]",
    "g(x)(y)", "ptrfn(1)",
    # generic call
    "f<int>(x)", "f<int, string>(a, b)", "make<Map<string, int>>()",
    # new / alloc / free / delete
    "new Foo(1)", "new Foo<int>(x)", "new Shape.Circle(r)", "new Shape.Nil",
    "alloc(int, n)", "alloc(Foo)", "free(p)", "delete x",
    # casts
    "(int)x", "(int*)p", "(float)y", "(ns::T)z", "(Foo)w",
    # nesting
    "f(g(x), h[i])", "(a + b) * c", "-(a + b)", "a + b * c - d / e",
]


def py_expr(src: str) -> str:
    toks = Lexer(src).tokenize()
    s = TokenStream(toks)
    ep = ExprParser(s, TypeParser(s))
    return show_expr(ep.parse_expr())


def glang_expr(src: str) -> str:
    proc = subprocess.run(
        [sys.executable, "bootstrap/main.py", "run", "Toolchain/compiler/expr_dump.lang"],
        input=src.encode("utf-8"), capture_output=True, cwd=_ROOT,
    )
    return proc.stdout.decode("utf-8").strip()


@pytest.mark.parametrize("src", EXPRS)
def test_expr_matches_python(src):
    assert glang_expr(src) == py_expr(src)
