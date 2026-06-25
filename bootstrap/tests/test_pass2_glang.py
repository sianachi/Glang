"""Differential test for the self-hosted Pass2 type checker.

Runs the full self-hosted analyser pipeline (compiler/analyse_dump.lang:
parse -> inject Exception -> namespace_resolve -> monomorphize -> pass1 ->
Pass2Checker.check_program) against the real Python `Analyser().analyse`.

For each source:
  * Python either succeeds (-> "OK") or raises TypeError (-> its .msg).
  * The Glang driver prints "OK" or "TYPEERROR\t<msg>" (msg percent-encoded).
We assert the OUTCOME matches (OK vs error) AND, on error, that the Python
.msg substring appears in the Glang msg.
"""

import os
import subprocess
import sys
import urllib.parse

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from lexer.lexer import Lexer
from parser.parser import Parser
from analyser.analyser import Analyser
from errors.errors import TypeError as GTypeError

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def py_outcome(src: str):
    """Returns ('ok', '') or ('err', msg)."""
    try:
        prog = Parser(Lexer(src).tokenize()).parse()
        Analyser().analyse(prog)
    except GTypeError as e:
        return ("err", e.msg)
    return ("ok", "")


def glang_outcome(src: str):
    proc = subprocess.run(
        [sys.executable, "bootstrap/main.py", "run", "Toolchain/compiler/analyse_dump.lang"],
        input=src.encode("utf-8"), capture_output=True, cwd=_ROOT,
    )
    out = proc.stdout.decode("utf-8").strip()
    first = out.splitlines()[0] if out else ""
    if first == "OK":
        return ("ok", "")
    if first.startswith("TYPEERROR\t"):
        msg = urllib.parse.unquote(first[len("TYPEERROR\t"):])
        return ("err", msg)
    # PARSEERROR / LEXERROR / unexpected → surface raw for debugging
    return ("other", out)


def check(src: str):
    pk, pmsg = py_outcome(src)
    gk, gmsg = glang_outcome(src)
    assert gk == pk, (
        f"outcome mismatch for {src!r}: python={pk}({pmsg!r}) glang={gk}({gmsg!r})"
    )
    if pk == "err":
        assert pmsg in gmsg, (
            f"error msg mismatch for {src!r}: python={pmsg!r} not in glang={gmsg!r}"
        )


# ── OK cases ──────────────────────────────────────────────────────────────

OK_CASES = [
    # var decls + literals
    "int main() { int x = 5; float f = 1.5; bool b = true; string s = \"hi\"; char c = 'a'; return 0; }",
    "int main() { var x = 5; var s = \"hi\"; return 0; }",
    "int main() { const int x = 5; return x; }",
    "int main() { int x = 1; x = 2; x += 3; x *= 2; return x; }",
    "int main() { byte b = 5; b = b & 15; return 0; }",
    "int main() { int x = 0; int* p = &x; *p = 5; return *p; }",
    # control flow
    "int main() { int s = 0; for (int i = 0; i < 10; ++i) { s += i; } return s; }",
    "int main() { int i = 0; while (i < 3) { i = i + 1; } return i; }",
    "int main() { int i = 0; do { i = i + 1; } while (i < 3); return i; }",
    "int main() { int x = 5; if (x > 0) { return 1; } else if (x < 0) { return 2; } else { return 0; } }",
    "int main() { for (int i = 0; i < 3; ++i) { if (i == 1) { continue; } if (i == 2) { break; } } return 0; }",
    "int main() { int* a = alloc(int, 3); foreach (char c in \"ab\") { } print(a[0]); return 0; }",
    "int main() { string s = \"abc\"; foreach (char c in s) { print(c); } return 0; }",
    "int main() { foreach (var v in \"abc\") { print(v); } return 0; }",
    # expressions
    "int main() { int x = (1 + 2) * 3 - 4 / 2 % 3; return x; }",
    "int main() { bool b = (1 < 2) && (3 > 2) || false; return 0; }",
    "int main() { int x = 5; int y = (int) 1.5; float f = (float) x; return 0; }",
    "int main() { print(toString(5)); print(len(\"abc\")); return 0; }",
    "int main() { string s = substr(\"hello\", 1, 3); return 0; }",
    # classes / this / fields / methods
    "class Point { int x; int y; Point(int a, int b) { this.x = a; this.y = b; } int sum() { return this.x + this.y; } } int main() { Point* p = new Point(1, 2); return p->sum(); }",
    "class C { int v; C(int x) { this.v = x; } int get() { return this.v; } } int main() { C c = C(5); return c.get(); }",
    "class C { const int v; C() { this.v = 5; } } int main() { return 0; }",
    "class C { static int count = 0; static int next() { return C.count; } } int main() { return C.next(); }",
    # inheritance / super / subtyping
    "class Animal { int legs; Animal(int n) { this.legs = n; } } class Dog extends Animal { Dog() : super(4) { } } int main() { Dog* d = new Dog(); Animal* a = d; return a->legs; }",
    "class Animal { void speak() { } } class Dog extends Animal { void bark() { } } int main() { Dog* d = new Dog(); d->speak(); return 0; }",
    # interfaces
    "interface Shape { float area(); } class Circle implements Shape { float r; Circle(float x) { this.r = x; } float area() { return this.r; } } int main() { Circle* c = new Circle(1.0); Shape* s = c; return 0; }",
    # enums
    "enum Color { RED, GREEN, BLUE } int main() { Color c = Color.GREEN; int v = (int) c; return v; }",
    # unions / match
    "union Tree { Leaf { int v; } Node { Tree* l; Tree* r; } } int main() { Tree t = Tree.Leaf(5); match (t) { Tree.Leaf(v) => { print(v); } Tree.Node(l, r) => { } } return 0; }",
    "union Opt { Some { int v; } None { } } int sum(Opt o) { match (o) { Opt.Some(v) => { return v; } Opt.None() => { return 0; } } } int main() { return sum(Opt.None); }",
    "union Shape { Circle { float r; } } int main() { Shape* s = new Shape.Circle(1.0); return 0; }",
    # closures
    "int main() { fn(int) -> int f = (int x) -> int { return x + 1; }; return f(5); }",
    "int main() { int base = 10; fn(int) -> int add = (int x) -> int { return x + base; }; return add(5); }",
    # operator overload
    "class Vec { int x; Vec(int a) { this.x = a; } Vec operator+(Vec o) { return Vec(this.x + o.x); } } int main() { Vec a = Vec(1); Vec b = Vec(2); Vec c = a + b; return 0; }",
    "class Vec { int x; Vec(int a) { this.x = a; } bool operator==(Vec o) { return this.x == o.x; } } int main() { Vec a = Vec(1); Vec b = Vec(2); bool e = a == b; bool n = a != b; return 0; }",
    # operator[] + foreach iterable class
    "class List2 { int n; List2() { this.n = 0; } int length() { return this.n; } int get(int i) { return i; } } int main() { List2 l = List2(); foreach (int v in l) { } return 0; }",
    # memory
    "int main() { int* p = alloc(int, 1); *p = 5; free(p); return 0; }",
    "int main() { int* p = alloc(int, 10); free(p); return 0; }",
    # exceptions
    "class MyErr extends Exception { MyErr(string m) : super(m) { } } int main() { try { throw new MyErr(\"x\"); } catch (MyErr* e) { print(e->message); } return 0; }",
    # access control
    "class C { private int secret; C() { this.secret = 1; } int reveal() { return this.secret; } } int main() { C* c = new C(); return c->reveal(); }",
    "class Base { protected int x; Base() { this.x = 1; } } class Sub extends Base { Sub() : super() { } int get() { return this.x; } } int main() { return 0; }",
    # nullable
    "int main() { int? x = null; int y = x ?? 5; return y; }",
]

# ── ERR cases ──────────────────────────────────────────────────────────────

ERR_CASES = [
    "int main() { int x = \"hi\"; return 0; }",
    "int main() { string s = 5; return 0; }",
    "int main() { var x = null; return 0; }",
    "int main() { undefinedVar = 5; return 0; }",
    "int main() { int x = 5; x = \"hi\"; return 0; }",
    "int main() { const int x = 5; x = 6; return 0; }",
    "int main() { if (5) { } return 0; }",
    "int main() { while (\"x\") { } return 0; }",
    "void f() { break; } int main() { return 0; }",
    "void f() { continue; } int main() { return 0; }",
    "int f() { } int main() { return 0; }",
    "int f() { return \"x\"; } int main() { return 0; }",
    "void f() { return 5; } int main() { return 0; }",
    "int main() { return undefined(); }",
    "int main() { int x = 5; return x.foo; }",
    "int main() { print(1, 2); return 0; }",
    "int main() { len(5); return 0; }",
    "int main() { int x = 1; int y = x + \"s\"; return 0; }",
    "int main() { bool b = !5; return 0; }",
    "int main() { int x = (int) \"hi\"; return 0; }",
    "class C { int v; } int main() { C* c = new C(); return c->missing; }",
    "class C { int v; C(int x) { this.v = x; } } int main() { C* c = new C(); return 0; }",
    "class C { int v; } int main() { C* c = new C(1, 2); return 0; }",
    "int main() { return new Bogus(); }",
    "class C { private int s; C() { this.s = 1; } } int main() { C* c = new C(); return c->s; }",
    "class Animal { Animal(int n) { } } class Dog extends Animal { Dog() { } } int main() { return 0; }",
    "enum Color { RED } int main() { Color c = Color.BLUE; return 0; }",
    "union Opt { Some { int v; } None { } } int main() { Opt o = Opt.None; match (o) { Opt.Some(v) => { } } return 0; }",
    "union Opt { Some { int v; } None { } } int main() { Opt o = Opt.Some(\"x\"); return 0; }",
    "int main() { this.x = 5; return 0; }",
    "int main() { super(); return 0; }",
    "int main() { int x = 300; byte b = (byte) x; b = 300; return 0; }",
    "int main() { foreach (int v in 5) { } return 0; }",
    "int main() { int x = 5; *x = 1; return 0; }",
    "int main() { int x = 5; return x->field; }",
    "int main() { delete 5; return 0; }",
    "int main() { int* a = alloc(int, 3); a[0] = \"hi\"; return 0; }",
    "class V { int x; V(int a) { this.x = a; } void operatorBad(V o) { } } int main() { return 0; }",
    "int main() { match (5) { } return 0; }",
]


@pytest.mark.parametrize("src", OK_CASES)
def test_pass2_ok(src):
    pk, pmsg = py_outcome(src)
    assert pk == "ok", f"expected Python OK but got error {pmsg!r} for {src!r}"
    check(src)


@pytest.mark.parametrize("src", ERR_CASES)
def test_pass2_err(src):
    pk, pmsg = py_outcome(src)
    assert pk == "err", f"expected Python error but got OK for {src!r}"
    check(src)
