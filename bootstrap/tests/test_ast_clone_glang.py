"""Differential + aliasing tests for the self-hosted AST deep-clone module.

FAITHFULNESS: for many sources, running the cloned program through
compiler/clone_dump.lang must produce the EXACT same canonical form
(showProgram) as running the original through compiler/parse_dump.lang.
A clone that drops/aliases/reorders any field would diverge here.

NO-ALIASING: a standalone Glang program parses a tiny program, clones it,
mutates a FieldDecl name in the clone, and confirms the original is unchanged.
"""

import glob
import os
import subprocess
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Targeted snippets exercising every union and record shape.
SNIPPETS = [
    'import "std/list.lang";',
    "int main() { return 0; }",
    "int add<T>(T a, T b) { return a + b; }",
    "T identity<T extends Comparable>(T x) { return x; }",
    "void f(const int a, string b) { print(b); }",
    "class Empty { }",
    "class Point { int x; int y; Point(int a, int b) { this.x = a; this.y = b; } int sum() { return this.x + this.y; } }",
    "class Dog extends Animal implements Pet, Trackable { Dog() : super(4) { } void speak() { bark(); } }",
    "class C { static int count = 0; int id; static int next() { return count; } }",
    "class WithDtor { Node* head; ~WithDtor() { cleanup(); } }",
    "class Vec { int x; Vec operator+(Vec other) { return this; } bool operator==(Vec o) { return true; } int operator[](int i) { return i; } }",
    "interface Shape { float area(); void draw(int layer); }",
    "enum Color { RED, GREEN, BLUE }",
    "enum Status { OK = 200, NOT_FOUND = 404 }",
    "union Tree { Leaf { int value; } Node { Tree* left; Tree* right; } }",
    "union Opt<T> { Some { T value; } None { } }",
    "namespace math { int abs(int x) { return x; } enum Sign { POS, NEG } }",
    "using namespace math;",
    "using math::abs;",
    "modifier<T> for List<T> { int second() { return this.get(1); } }",
    "private class Secret { int code; }",
    "class Box<T> { T value; Box(T v) { this.value = v; } T get() { return this.value; } }",
    # Exercise the harder Expr/Stmt/TypeNode/Pattern shapes:
    "void f() { int x = 0; x += 1; x -= 2; while (x < 10) { x = x + 1; } do { x--; } while (x > 0); }",
    "void f() { for (int i = 0; i < 10; ++i) { if (i == 5) { break; } else { continue; } } }",
    "void f(int[5] arr) { foreach (const int v in arr) { print(v); } }",
    "int f() { int* p = alloc(int, 3); int* q = alloc(int); *p = 1; int y = p[0]; delete q; free(p); return *p; }",
    "void f() { fn(int)->int g = (int x) -> int { return x + 1; }; int r = g(5); }",
    "void f() { try { risky(); } catch (IoError* e) { handle(e); } catch (Exception* e) { rethrow(); } }",
    "void f(Tree* t) { match (*t) { Tree.Leaf(v) => { print(v); } Tree.Node(l, r) => { walk(l); } _ => { } } }",
    "void f() { Foo* x = null; Foo? y = bar(); int z = (int) 3.5; }",
    "void f() { obj.method(1, 2); ptr->field; arr[i + 1] = obj.field; }",
    "void f() { using (Resource* r = open()) { use(r); } }",
    "void f() { throw new IoError(\"bad\"); }",
    "void f() { g<int, string>(1, \"a\"); Box<int>* b = new Box<int>(3); }",
    'import "std/map.lang";\nimport "std/io.lang";\nint main() { return 0; }',
]

REAL_FILES = sorted(
    glob.glob(os.path.join(_ROOT, "Toolchain", "examples", "*.lang"))
    + glob.glob(os.path.join(_ROOT, "Toolchain", "stdlib", "*.lang"))
)


def _run(driver: str, src: str) -> str:
    proc = subprocess.run(
        [sys.executable, "bootstrap/main.py", "run", driver],
        input=src.encode("utf-8"), capture_output=True, cwd=_ROOT,
    )
    return proc.stdout.decode("utf-8").strip()


def orig_form(src: str) -> str:
    return _run("Toolchain/compiler/parse_dump.lang", src)


def clone_form(src: str) -> str:
    return _run("Toolchain/compiler/clone_dump.lang", src)


@pytest.mark.parametrize("src", SNIPPETS)
def test_clone_faithful_snippets(src):
    assert clone_form(src) == orig_form(src)


@pytest.mark.parametrize("path", REAL_FILES, ids=lambda p: os.path.basename(p))
def test_clone_faithful_real_files(path):
    src = open(path, encoding="utf-8").read()
    assert clone_form(src) == orig_form(src)


def test_clone_no_aliasing():
    proc = subprocess.run(
        [sys.executable, "bootstrap/main.py", "run", "Toolchain/compiler/clone_alias_check.lang"],
        capture_output=True, cwd=_ROOT,
    )
    out = proc.stdout.decode("utf-8").strip().splitlines()
    assert out == ["orig:x", "clone:MUTATED", "INDEPENDENT"], out
