import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from lexer.lexer import Lexer
from parser.parser import Parser
from parser.ast_nodes import NamespaceDecl, FunctionDecl
from analyser.analyser import Analyser
from interpreter.interpreter import Interpreter
from errors.errors import TypeError as GTE, ParseError


# ---------------------------------------------------------------------------
# Harness
# ---------------------------------------------------------------------------

def parse(src: str):
    return Parser(Lexer(src).tokenize()).parse()


def analyse(src: str):
    return Analyser().analyse(parse(src))


def run(src: str) -> int:
    prog = parse(src)
    env = Analyser().analyse(prog)
    return Interpreter(env).run(prog)


def run_out(src: str):
    prog = parse(src)
    env = Analyser().analyse(prog)
    interp = Interpreter(env)
    code = interp.run(prog)
    return code, interp.output


def err(src: str, fragment: str):
    with pytest.raises(GTE) as exc:
        analyse(src)
    assert fragment in str(exc.value)


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

class TestParsing:
    def test_namespace_block(self):
        prog = parse("namespace math { int abs(int x) { return x; } }")
        assert len(prog.declarations) == 1
        ns = prog.declarations[0]
        assert isinstance(ns, NamespaceDecl)
        assert ns.name == "math"
        assert isinstance(ns.declarations[0], FunctionDecl)
        assert ns.declarations[0].name == "abs"

    def test_qualified_namespace_name(self):
        prog = parse("namespace a::b { int f() { return 1; } }")
        assert prog.declarations[0].name == "a::b"

    def test_nested_namespace(self):
        prog = parse("namespace a { namespace b { int f() { return 1; } } }")
        inner = prog.declarations[0].declarations[0]
        assert isinstance(inner, NamespaceDecl)
        assert inner.name == "b"

    def test_import_inside_namespace_rejected(self):
        with pytest.raises(ParseError):
            parse('namespace a { import "std/math.lang"; }')

    def test_namespace_may_hold_class_enum_interface(self):
        prog = parse("""
            namespace shapes {
                enum Kind { CIRCLE, SQUARE }
                interface Drawable { int area(); }
                class Box { int w; Box(int w) { this.w = w; } }
            }
        """)
        assert len(prog.declarations[0].declarations) == 3


# ---------------------------------------------------------------------------
# Resolution & type checking
# ---------------------------------------------------------------------------

class TestResolution:
    def test_qualified_call_from_outside(self):
        env = analyse("""
            namespace math { int abs(int x) { if (x < 0) { return -x; } return x; } }
            int main() { return math::abs(-3); }
        """)
        assert "math::abs" in env.functions

    def test_unqualified_sibling_call(self):
        assert run("""
            namespace math {
                int sign(int x) { if (x < 0) { return -1; } return 1; }
                int abs(int x) { return x * sign(x); }
            }
            int main() { return math::abs(-7); }
        """) == 7

    def test_unqualified_call_not_visible_outside(self):
        err("""
            namespace math { int abs(int x) { return x; } }
            int main() { return abs(-3); }
        """, "abs")

    def test_local_variable_shadows_member(self):
        # `sign` is a local int here; the call through the function pointer
        # variable must not be rewritten to math::sign.
        assert run("""
            namespace math {
                int sign(int x) { return 100; }
                int f() {
                    int sign = 5;
                    return sign;
                }
            }
            int main() { return math::f(); }
        """) == 5

    def test_duplicate_member_rejected(self):
        err("""
            namespace a { int f() { return 1; } }
            namespace a { int f() { return 2; } }
        """, "a::f")

    def test_same_name_in_different_namespaces(self):
        assert run("""
            namespace a { int f() { return 1; } }
            namespace b { int f() { return 2; } }
            int main() { return a::f() + b::f(); }
        """) == 3

    def test_namespace_member_and_global_coexist(self):
        assert run("""
            int f() { return 10; }
            namespace a { int f() { return 1; } }
            int main() { return f() + a::f(); }
        """) == 11

    def test_member_prefers_namespace_over_global(self):
        assert run("""
            int f() { return 10; }
            namespace a {
                int f() { return 1; }
                int g() { return f(); }
            }
            int main() { return a::g(); }
        """) == 1

    def test_member_falls_back_to_global(self):
        assert run("""
            int ten() { return 10; }
            namespace a { int g() { return ten(); } }
            int main() { return a::g(); }
        """) == 10

    def test_nested_namespace_resolution(self):
        assert run("""
            namespace a {
                int one() { return 1; }
                namespace b {
                    int two() { return 2; }
                    int sum() { return one() + two(); }
                }
            }
            int main() { return a::b::sum() + a::b::two(); }
        """) == 5

    def test_relative_qualified_reference(self):
        assert run("""
            namespace a {
                namespace b { int f() { return 4; } }
                int g() { return b::f(); }
            }
            int main() { return a::g(); }
        """) == 4

    def test_reopened_namespace_extends(self):
        assert run("""
            namespace a { int one() { return 1; } }
            namespace a { int two() { return one() + 1; } }
            int main() { return a::two(); }
        """) == 2


# ---------------------------------------------------------------------------
# Classes, enums, generics inside namespaces
# ---------------------------------------------------------------------------

class TestNamespacedTypes:
    def test_class_in_namespace(self):
        assert run("""
            namespace geo {
                class Point {
                    int x;
                    Point(int x) { this.x = x; }
                    int getX() { return this.x; }
                }
            }
            int main() {
                geo::Point* p = new geo::Point(9);
                int x = p->getX();
                delete p;
                return x;
            }
        """) == 9

    def test_stack_construction_and_var_decl(self):
        assert run("""
            namespace geo {
                class Point { int x; Point(int x) { this.x = x; } }
            }
            int main() {
                geo::Point p = geo::Point(5);
                return p.x;
            }
        """) == 5

    def test_unqualified_class_use_inside_namespace(self):
        assert run("""
            namespace geo {
                class Point { int x; Point(int x) { this.x = x; } }
                int probe() {
                    Point p = Point(6);
                    return p.x;
                }
            }
            int main() { return geo::probe(); }
        """) == 6

    def test_enum_in_namespace(self):
        assert run("""
            namespace traffic {
                enum Light { RED, GREEN = 5, BLUE }
            }
            int main() {
                traffic::Light l = traffic::Light.GREEN;
                return (int)l;
            }
        """) == 5

    def test_enum_unqualified_inside_namespace(self):
        assert run("""
            namespace traffic {
                enum Light { RED, GREEN = 5 }
                int green() { return (int)(Light.GREEN); }
            }
            int main() { return traffic::green(); }
        """) == 5

    def test_static_members(self):
        assert run("""
            namespace cfg {
                class Defaults {
                    static int answer = 42;
                    static int get() { return Defaults.answer; }
                }
            }
            int main() { return cfg::Defaults.get(); }
        """) == 42

    def test_extends_within_namespace(self):
        assert run("""
            namespace zoo {
                class Animal { int legs; Animal(int legs) { this.legs = legs; } }
                class Dog extends Animal { Dog() : super(4) { } }
            }
            int main() {
                zoo::Dog d = zoo::Dog();
                return d.legs;
            }
        """) == 4

    def test_interface_within_namespace(self):
        assert run("""
            namespace zoo {
                interface Noisy { int volume(); }
                class Dog implements Noisy {
                    Dog() { }
                    int volume() { return 11; }
                }
            }
            int main() {
                zoo::Dog d = zoo::Dog();
                return d.volume();
            }
        """) == 11

    def test_generic_class_in_namespace(self):
        assert run("""
            namespace col {
                class Pair<T> {
                    T a;
                    T b;
                    Pair(T a, T b) { this.a = a; this.b = b; }
                    T first() { return this.a; }
                }
            }
            int main() {
                col::Pair<int> p = col::Pair<int>(3, 4);
                return p.first() + p.b;
            }
        """) == 7

    def test_generic_function_in_namespace(self):
        assert run("""
            namespace util {
                T identity<T>(T x) { return x; }
            }
            int main() { return util::identity<int>(8); }
        """) == 8

    def test_function_pointer_to_namespaced_function(self):
        assert run("""
            namespace math { int twice(int x) { return x * 2; } }
            int main() {
                fn(int) -> int f = math::twice;
                return f(21);
            }
        """) == 42

    def test_qualified_cast(self):
        assert run("""
            namespace traffic { enum Light { RED, GREEN } }
            int main() {
                traffic::Light l = (traffic::Light)1;
                return (int)l;
            }
        """) == 1

    def test_namespaced_class_as_field_and_param(self):
        assert run("""
            namespace geo {
                class Point { int x; Point(int x) { this.x = x; } }
                int getX(Point p) { return p.x; }
            }
            int main() {
                geo::Point p = geo::Point(13);
                return geo::getX(p);
            }
        """) == 13


# ---------------------------------------------------------------------------
# Interaction with existing syntax
# ---------------------------------------------------------------------------

class TestNoRegressions:
    def test_constructor_super_colon_still_works(self):
        # Single ':' must still lex for `Ctor() : super(...)`.
        assert run("""
            class A { int v; A(int v) { this.v = v; } }
            class B extends A { B() : super(3) { } }
            int main() { B b = B(); return b.v; }
        """) == 3

    def test_discarded_comparison_not_a_decl(self):
        # `a < b > c;` style statements must still parse as expressions.
        assert run("""
            int main() {
                int a = 1;
                int b = 2;
                bool r = a < b;
                if (r) { return 1; }
                return 0;
            }
        """) == 1
