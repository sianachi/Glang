"""Differential test for the self-hosted declaration parser + full Parser.

Parses whole programs with both the Python Parser and the Glang one (via
compiler/parse_dump.lang) and compares canonical program forms.  Runs over both
hand-written snippets and real .lang files (examples + stdlib) for breadth.
"""

import glob
import os
import subprocess
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from lexer.lexer import Lexer
from parser.parser import Parser
from tests.glang_show import show_program

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

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
    'import "std/map.lang";\nimport "std/io.lang";\nint main() { return 0; }',
]

# A spread of real source files — strong, broad coverage.
REAL_FILES = sorted(
    glob.glob(os.path.join(_ROOT, "Toolchain", "examples", "*.lang"))
    + glob.glob(os.path.join(_ROOT, "Toolchain", "stdlib", "*.lang"))
)


def py_prog(src: str) -> str:
    return show_program(Parser(Lexer(src).tokenize()).parse())


def glang_prog(src: str) -> str:
    proc = subprocess.run(
        [sys.executable, "bootstrap/main.py", "run", "Toolchain/compiler/parse_dump.lang"],
        input=src.encode("utf-8"), capture_output=True, cwd=_ROOT,
    )
    return proc.stdout.decode("utf-8").strip()


@pytest.mark.parametrize("src", SNIPPETS)
def test_decl_snippets(src):
    assert glang_prog(src) == py_prog(src)


@pytest.mark.parametrize("path", REAL_FILES, ids=lambda p: os.path.basename(p))
def test_real_files(path):
    src = open(path, encoding="utf-8").read()
    assert glang_prog(src) == py_prog(src)
