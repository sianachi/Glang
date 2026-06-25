"""Differential test for the self-hosted namespace resolver.

Format A: parse a whole program with the Python parser, run the resolver with
both the Python NamespaceResolver and the Glang one (via compiler/ns_dump.lang),
and compare canonical program forms (tests.glang_show.show_program).

For programs the resolver rejects, both sides must print `ERROR <msg>` with the
identical message text.

Inputs: the snippets exercised by tests/test_namespaces.py (success + error
cases) plus every real .lang file under examples/ and stdlib/ that uses
`namespace`/top-level `using`.
"""

import glob
import os
import subprocess
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from lexer.lexer import Lexer
from parser.parser import Parser
from analyser.namespace_resolver import NamespaceResolver
from errors.errors import TypeError as GTE
from tests.glang_show import show_program

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# ── success snippets (from test_namespaces.py) ──────────────────────────────
OK_SNIPPETS = [
    "namespace math { int abs(int x) { return x; } enum Sign { POS, NEG } }",
    """
    namespace math { int abs(int x) { if (x < 0) { return -x; } return x; } }
    int main() { return math::abs(-3); }
    """,
    """
    namespace math {
        int sign(int x) { if (x < 0) { return -1; } return 1; }
        int abs(int x) { return x * sign(x); }
    }
    int main() { return math::abs(-7); }
    """,
    """
    namespace math {
        int sign(int x) { return 100; }
        int f() { int sign = 5; return sign; }
    }
    int main() { return math::f(); }
    """,
    """
    namespace a { int f() { return 1; } }
    namespace b { int f() { return 2; } }
    int main() { return a::f() + b::f(); }
    """,
    """
    int f() { return 10; }
    namespace a { int f() { return 1; } }
    int main() { return f() + a::f(); }
    """,
    """
    int f() { return 10; }
    namespace a { int f() { return 1; } int g() { return f(); } }
    int main() { return a::g(); }
    """,
    """
    int ten() { return 10; }
    namespace a { int g() { return ten(); } }
    int main() { return a::g(); }
    """,
    """
    namespace a {
        int one() { return 1; }
        namespace b { int two() { return 2; } int sum() { return one() + two(); } }
    }
    int main() { return a::b::sum() + a::b::two(); }
    """,
    """
    namespace a {
        namespace b { int f() { return 4; } }
        int g() { return b::f(); }
    }
    int main() { return a::g(); }
    """,
    """
    namespace a { int one() { return 1; } }
    namespace a { int two() { return one() + 1; } }
    int main() { return a::two(); }
    """,
    # classes / enums / generics in namespaces
    """
    namespace geo {
        class Point { int x; Point(int x) { this.x = x; } int getX() { return this.x; } }
    }
    int main() { geo::Point* p = new geo::Point(9); int x = p->getX(); delete p; return x; }
    """,
    """
    namespace geo { class Point { int x; Point(int x) { this.x = x; } } }
    int main() { geo::Point p = geo::Point(5); return p.x; }
    """,
    """
    namespace geo {
        class Point { int x; Point(int x) { this.x = x; } }
        int probe() { Point p = Point(6); return p.x; }
    }
    int main() { return geo::probe(); }
    """,
    """
    namespace traffic { enum Light { RED, GREEN = 5, BLUE } }
    int main() { traffic::Light l = traffic::Light.GREEN; return (int)l; }
    """,
    """
    namespace traffic {
        enum Light { RED, GREEN = 5 }
        int green() { return (int)(Light.GREEN); }
    }
    int main() { return traffic::green(); }
    """,
    """
    namespace cfg {
        class Defaults { static int answer = 42; static int get() { return Defaults.answer; } }
    }
    int main() { return cfg::Defaults.get(); }
    """,
    """
    namespace zoo {
        class Animal { int legs; Animal(int legs) { this.legs = legs; } }
        class Dog extends Animal { Dog() : super(4) { } }
    }
    int main() { zoo::Dog d = zoo::Dog(); return d.legs; }
    """,
    """
    namespace zoo {
        interface Noisy { int volume(); }
        class Dog implements Noisy { Dog() { } int volume() { return 11; } }
    }
    int main() { zoo::Dog d = zoo::Dog(); return d.volume(); }
    """,
    """
    namespace col {
        class Pair<T> { T a; T b; Pair(T a, T b) { this.a = a; this.b = b; } T first() { return this.a; } }
    }
    int main() { col::Pair<int> p = col::Pair<int>(3, 4); return p.first() + p.b; }
    """,
    """
    namespace util { T identity<T>(T x) { return x; } }
    int main() { return util::identity<int>(8); }
    """,
    """
    namespace math { int twice(int x) { return x * 2; } }
    int main() { fn(int) -> int f = math::twice; return f(21); }
    """,
    """
    namespace traffic { enum Light { RED, GREEN } }
    int main() { traffic::Light l = (traffic::Light)1; return (int)l; }
    """,
    """
    namespace geo {
        class Point { int x; Point(int x) { this.x = x; } }
        int getX(Point p) { return p.x; }
    }
    int main() { geo::Point p = geo::Point(13); return geo::getX(p); }
    """,
    # using directives
    """
    namespace math {
        int abs(int x) { if (x < 0) { return -x; } return x; }
        int sign(int x) { if (x < 0) { return -1; } return 1; }
    }
    using namespace math;
    int main() { return abs(-3) + sign(9); }
    """,
    """
    namespace math { int abs(int x) { if (x < 0) { return -x; } return x; } }
    using math::abs;
    int main() { return abs(-5); }
    """,
    """
    int f() { return 10; }
    namespace a { int f() { return 1; } }
    using namespace a;
    int main() { return f(); }
    """,
    """
    namespace geo {
        class Point { int x; Point(int x) { this.x = x; } }
        enum Axis { X, Y = 7 }
    }
    using namespace geo;
    int main() {
        Point p = Point(3);
        Point* q = new Point(4);
        int total = p.x + q->x + (int)(Axis.Y);
        delete q;
        return total;
    }
    """,
    """
    namespace col {
        class Pair<T> { T a; T b; Pair(T a, T b) { this.a = a; this.b = b; } }
    }
    using namespace col;
    int main() { Pair<int> p = Pair<int>(3, 4); return p.a + p.b; }
    """,
    """
    namespace math { int abs(int x) { return 100; } }
    using namespace math;
    int main() { int abs = 6; return abs; }
    """,
    """
    namespace math { int abs(int x) { if (x < 0) { return -x; } return x; } }
    using namespace math;
    using namespace math;
    int main() { return abs(-2); }
    """,
]

# ── error snippets: both sides must produce identical `ERROR <msg>` ─────────
ERR_SNIPPETS = [
    """
    namespace math { int abs(int x) { return x; } }
    using namespace maths;
    int main() { return 0; }
    """,
    """
    namespace math { int abs(int x) { return x; } }
    using math::sing;
    int main() { return 0; }
    """,
    """
    namespace a { namespace b { int f() { return 1; } } }
    using a::b;
    int main() { return 0; }
    """,
    """
    namespace a { int f() { return 1; } }
    namespace b { int f() { return 2; } }
    using namespace a;
    using namespace b;
    int main() { return f(); }
    """,
    """
    int abs(int x) { return x; }
    namespace math { int abs(int x) { return -x; } }
    using math::abs;
    int main() { return 0; }
    """,
    """
    namespace a { int f() { return 1; } }
    namespace b { int f() { return 2; } }
    using a::f;
    using b::f;
    int main() { return 0; }
    """,
]

# ── real files using namespace / top-level using ────────────────────────────
def _uses_namespace(path):
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            s = line.lstrip()
            if s.startswith("namespace ") or s.startswith("using namespace "):
                return True
            # `using qualified::name;` (not the `using (...)` resource block)
            if s.startswith("using ") and "::" in s.split(";", 1)[0] and "(" not in s.split(";", 1)[0]:
                return True
    return False


REAL_FILES = sorted(
    p for p in (
        glob.glob(os.path.join(_ROOT, "examples", "*.lang"))
        + glob.glob(os.path.join(_ROOT, "stdlib", "*.lang"))
    )
    if _uses_namespace(p)
)


# ── helpers ─────────────────────────────────────────────────────────────────
def py_resolve(src: str) -> str:
    prog = Parser(Lexer(src).tokenize()).parse()
    try:
        NamespaceResolver().run(prog)
    except GTE as e:
        return "ERROR " + e.msg
    return show_program(prog)


def glang_resolve(src: str) -> str:
    proc = subprocess.run(
        [sys.executable, "main.py", "run", "compiler/ns_dump.lang"],
        input=src.encode("utf-8"), capture_output=True, cwd=_ROOT,
    )
    return proc.stdout.decode("utf-8").strip()


@pytest.mark.parametrize("src", OK_SNIPPETS, ids=lambda s: s.strip()[:40])
def test_ok_snippets(src):
    assert glang_resolve(src) == py_resolve(src)


@pytest.mark.parametrize("src", ERR_SNIPPETS, ids=lambda s: s.strip()[:40])
def test_err_snippets(src):
    expected = py_resolve(src)
    assert expected.startswith("ERROR ")
    assert glang_resolve(src) == expected


@pytest.mark.parametrize("path", REAL_FILES, ids=lambda p: os.path.basename(p))
def test_real_files(path):
    src = open(path, encoding="utf-8").read()
    assert glang_resolve(src) == py_resolve(src)
