"""Differential test for the self-hosted Pass 1 collector.

Runs `compiler/pass1_dump.lang` (parse -> pass1_collect -> dump populated env)
against a Python reference that runs the real `Pass1Collector` and dumps the
resulting `GlobalEnv` in the identical sorted-line format.  Covers functions,
classes (fields/methods/static/inheritance/interfaces/ctor/dtor), enums,
unions, interfaces, modifiers, and the error cases pass1 raises.

Test in ISOLATION: only non-generic, non-namespace sources (generics leave
GenericType nodes that resolve_type rejects; namespaces are flattened by an
earlier pass).  Both paths must emit matching `ERROR <msg>` on failure.
"""

import os
import subprocess
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from lexer.lexer import Lexer
from parser.parser import Parser
from analyser.symbol_table import GlobalEnv
from analyser.pass1_collector import Pass1Collector
from analyser.type_utils import type_str
from errors.errors import TypeError as GTypeError

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ── Python reference dumper (mirrors compiler/pass1_dump.lang line-for-line) ──

def _join_sorted(xs):
    return ",".join(sorted(xs))


def _bool_word(b):
    return "yes" if b else "no"


def _dump_class(info):
    superw = info.superclass if info.superclass else "-"
    s = "class " + info.name
    s += " super=" + superw
    s += " fields=[" + _join_sorted(info.fields.keys()) + "]"
    s += " static_fields=[" + _join_sorted(info.static_fields.keys()) + "]"
    s += " methods=[" + _join_sorted(info.instance_methods.keys()) + "]"
    s += " static_methods=[" + _join_sorted(info.static_methods.keys()) + "]"
    # Python always inserts "~destructor" (None when no dtor); the Glang dump
    # only carries real entries, so drop None-valued vtable keys to match.
    vt_keys = [k for k, v in info.vtable.items() if v is not None]
    s += " vtable=[" + _join_sorted(vt_keys) + "]"
    s += " ifaces=[" + _join_sorted(info.interfaces) + "]"
    s += " ctor=" + _bool_word(info.constructor is not None)
    s += " dtor=" + _bool_word(info.destructor is not None)
    s += " access=" + info.access
    return s


def _dump_func(info):
    ptypes = [type_str(p.type) for p in info.params]
    s = "func " + info.name
    s += " ret=" + type_str(info.return_type)
    s += " params=[" + ",".join(ptypes) + "]"
    return s


def _dump_enum(info):
    entries = [f"{k}={v}" for k, v in info.variants.items()]
    return "enum " + info.name + " variants=[" + _join_sorted(entries) + "]"


def _dump_union(info):
    tps = list(info.type_params)
    vparts = []
    for uv in info.variants.values():
        fparts = [type_str(fd.type) + " " + fd.name for fd in uv.fields]
        vparts.append(uv.name + "{" + ",".join(fparts) + "}")
    return ("union " + info.name
            + " type_params=[" + ",".join(tps) + "]"
            + " variants=[" + _join_sorted(vparts) + "]")


def _dump_interface(info):
    return "interface " + info.name + " methods=[" + _join_sorted(info.methods.keys()) + "]"


def _dump_modifier(target, bucket):
    return "modifier " + target + " methods=[" + _join_sorted(bucket.keys()) + "]"


def _dump_env(env):
    lines = []
    for info in env.classes.values():
        lines.append(_dump_class(info))
    for info in env.functions.values():
        lines.append(_dump_func(info))
    for info in env.enums.values():
        lines.append(_dump_enum(info))
    for info in env.unions.values():
        lines.append(_dump_union(info))
    for info in env.interfaces.values():
        lines.append(_dump_interface(info))
    for target, bucket in env.modifier_methods.items():
        lines.append(_dump_modifier(target, bucket))
    return "\n".join(sorted(lines))


def py_dump(src: str) -> str:
    prog = Parser(Lexer(src).tokenize()).parse()
    env = GlobalEnv()
    try:
        Pass1Collector(env).collect(prog)
    except GTypeError as e:
        return "ERROR " + e.msg
    return _dump_env(env)


def glang_dump(src: str) -> str:
    proc = subprocess.run(
        [sys.executable, "bootstrap/main.py", "run", "Toolchain/compiler/pass1_dump.lang"],
        input=src.encode("utf-8"), capture_output=True, cwd=_ROOT,
    )
    return proc.stdout.decode("utf-8").strip()


# ── cases ────────────────────────────────────────────────────────────────────

OK_SNIPPETS = [
    # functions
    "int main() { return 0; }",
    "void f(int a, string b) { } int g() { return 0; }",
    "int* ptr(int a, bool b) { return null; }",
    "void takesFn(fn(int, bool) -> void cb) { }",
    # classes
    "class Empty { }",
    "class Point { int x; int y; Point(int a, int b) { this.x = a; this.y = b; } int sum() { return this.x + this.y; } }",
    "class C { static int count = 0; int id; static int next() { return count; } }",
    "class WithDtor { Node* head; ~WithDtor() { } } class Node { int v; }",
    "private class Secret { int code; }",
    # inheritance + interfaces
    "interface Pet { void speak(); }\nclass Animal { int legs; void speak() { } void breathe() { } }\nclass Dog extends Animal implements Pet { void speak() { } void fetch() { } }",
    "interface A { void m(); }\ninterface B { int n(int x); }\nclass Both implements A, B { void m() { } int n(int x) { return x; } }",
    "class Base { int x; void shared() { } }\nclass Mid extends Base { int y; void mid() { } }\nclass Leaf extends Mid { int z; void shared() { } }",
    # enums
    "enum Color { RED, GREEN, BLUE }",
    "enum Status { OK = 200, NOT_FOUND = 404 }",
    "enum Mixed { A, B = 10, C }",
    # unions
    "union Tree { Leaf { int value; } Node { Tree* left; Tree* right; } }",
    "union Shape { Circle { float r; } Rect { float w; float h; } Empty { } }",
    # interfaces alone
    "interface Shape { float area(); void draw(int layer); }",
    # modifiers
    "class Foo { int v; } modifier for Foo { int bar() { return this.v; } int baz(int n) { return n; } }",
    # mix
    "enum E { X, Y }\ninterface I { void go(); }\nclass K implements I { E state; void go() { } }\nint helper(K k) { return 0; }",
]

ERR_SNIPPETS = [
    # duplicate names
    "int x() { return 0; } int x() { return 1; }",
    "class A { } class A { }",
    "enum E { A } enum E { B }",
    "class Dup { } int Dup() { return 0; }",
    # unknown super / interface
    "class A extends B { }",
    "class A implements I { }",
    "interface I { } class A extends I { }",
    "class B { } class A implements B { }",
    # circular inheritance
    "class A extends B { } class B extends A { }",
    "class A extends A { }",
    # interface completeness
    "interface Pet { void speak(); }\nclass Dog implements Pet { void bark() { } }",
    "interface Pet { void speak(); }\nclass Dog implements Pet { int speak() { return 1; } }",
    # duplicate enum / union variants
    "enum E { A, A }",
    "union U { V { int x; } V { int y; } }",
    # direct field cycle
    "class A { B b; } class B { A a; }",
    "class A { A self; }",
    # unknown type in a field / param / return
    "class A { Bogus x; }",
    "int f(Nope n) { return 0; }",
    # duplicate modifier method
    "class Foo { } modifier for Foo { int m() { return 0; } int m() { return 1; } }",
]


@pytest.mark.parametrize("src", OK_SNIPPETS)
def test_pass1_ok(src):
    assert glang_dump(src) == py_dump(src)


@pytest.mark.parametrize("src", ERR_SNIPPETS)
def test_pass1_errors(src):
    out = py_dump(src)
    assert out.startswith("ERROR"), f"expected Python to raise, got: {out!r}"
    assert glang_dump(src) == out


# A spread of real non-generic, non-namespace example files for breadth.
def _eligible_real_files():
    import glob
    files = sorted(glob.glob(os.path.join(_ROOT, "Toolchain", "examples", "*.lang")))
    out = []
    for path in files:
        src = open(path, encoding="utf-8").read()
        if "<" in src and ">" in src:
            # crude generic/namespace filter — skip anything that might leave
            # GenericType nodes or namespace blocks (pass1 runs after those).
            continue
        if "namespace" in src or "import" in src:
            continue
        out.append(path)
    return out


@pytest.mark.parametrize("path", _eligible_real_files(), ids=os.path.basename)
def test_pass1_real_files(path):
    src = open(path, encoding="utf-8").read()
    assert glang_dump(src) == py_dump(src)
