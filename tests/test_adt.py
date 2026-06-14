"""Tests for algebraic data types (union declarations) and match statements."""
import sys, os, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from loader.loader import Loader
from analyser.analyser import Analyser
from analyser.pass1_collector import Pass1Collector
from analyser.symbol_table import GlobalEnv
from parser.parser import Parser
from lexer.lexer import Lexer
from interpreter.interpreter import Interpreter
from errors.errors import TypeError as GTE, ParseError


def run_out(src: str):
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "prog.lang")
        with open(path, "w", encoding="utf-8") as f:
            f.write(src)
        prog = Loader().load(path)
        env = Analyser().analyse(prog)
        interp = Interpreter(env)
        code = interp.run(prog)
        return code, interp.output


def run_err(src: str, fragment: str):
    with pytest.raises((GTE, ParseError)) as exc_info:
        run_out(src)
    assert fragment in str(exc_info.value), str(exc_info.value)


def main(body: str) -> str:
    return f"int main() {{\n{body}\nreturn 0;\n}}"


# ---------------------------------------------------------------------------
# Basic union declaration and construction
# ---------------------------------------------------------------------------

SIMPLE_UNION = """\
union Shape {
    Circle { int radius; }
    Square { int side; }
    Point  { }
}
"""


class TestUnionDecl:
    def test_single_variant(self):
        _, out = run_out(SIMPLE_UNION + main("""\
Shape s = Shape.Circle(5);
print("ok");
"""))
        assert out == ["ok"]

    def test_no_field_variant(self):
        _, out = run_out(SIMPLE_UNION + main("""\
Shape s = Shape.Point;
print("ok");
"""))
        assert out == ["ok"]

    def test_multi_field_variant(self):
        _, out = run_out(SIMPLE_UNION + main("""\
Shape s = Shape.Square(10);
print("ok");
"""))
        assert out == ["ok"]

    def test_pointer_variant(self):
        _, out = run_out(SIMPLE_UNION + main("""\
Shape* s = new Shape.Circle(3);
delete s;
print("ok");
"""))
        assert out == ["ok"]


# ---------------------------------------------------------------------------
# match statement
# ---------------------------------------------------------------------------

class TestMatchBasic:
    def test_dispatch_first_variant(self):
        _, out = run_out(SIMPLE_UNION + main("""\
Shape s = Shape.Circle(7);
match (s) {
    Shape.Circle(r) => { print(r); }
    Shape.Square(x) => { print(x); }
    Shape.Point     => { print("point"); }
}
"""))
        assert out == ["7"]

    def test_dispatch_second_variant(self):
        _, out = run_out(SIMPLE_UNION + main("""\
Shape s = Shape.Square(4);
match (s) {
    Shape.Circle(r) => { print(r); }
    Shape.Square(x) => { print(x); }
    Shape.Point     => { print("point"); }
}
"""))
        assert out == ["4"]

    def test_dispatch_no_field_variant(self):
        _, out = run_out(SIMPLE_UNION + main("""\
Shape s = Shape.Point;
match (s) {
    Shape.Circle(r) => { print(r); }
    Shape.Square(x) => { print(x); }
    Shape.Point     => { print("point"); }
}
"""))
        assert out == ["point"]

    def test_wildcard_arm(self):
        _, out = run_out(SIMPLE_UNION + main("""\
Shape s = Shape.Square(9);
match (s) {
    Shape.Circle(r) => { print(r); }
    _ => { print("other"); }
}
"""))
        assert out == ["other"]

    def test_pointer_scrutinee(self):
        _, out = run_out(SIMPLE_UNION + main("""\
Shape* sp = new Shape.Circle(2);
match (*sp) {
    Shape.Circle(r) => { print(r); }
    Shape.Square(x) => { print(x); }
    Shape.Point     => { print("point"); }
}
delete sp;
"""))
        assert out == ["2"]

    def test_return_from_arm(self):
        src = SIMPLE_UNION + """\
int area(Shape s) {
    match (s) {
        Shape.Circle(r) => { return r * r; }
        Shape.Square(x) => { return x * x; }
        Shape.Point     => { return 0; }
    }
}
""" + main("print(area(Shape.Circle(3)));")
        _, out = run_out(src)
        assert out == ["9"]

    def test_multiple_bindings(self):
        src = """\
union Vec2 {
    Vec { int x; int y; }
}
""" + main("""\
Vec2 v = Vec2.Vec(3, 4);
match (v) {
    Vec2.Vec(a, b) => { print(a + b); }
}
""")
        _, out = run_out(src)
        assert out == ["7"]


# ---------------------------------------------------------------------------
# Analyser error cases
# ---------------------------------------------------------------------------

class TestUnionErrors:
    def test_unknown_variant(self):
        run_err(SIMPLE_UNION + main("Shape s = Shape.Triangle(1);"),
                "no variant 'Triangle'")

    def test_wrong_arg_count(self):
        run_err(SIMPLE_UNION + main("Shape s = Shape.Circle(1, 2);"),
                "expects 1 argument")

    def test_arg_type_mismatch(self):
        run_err(SIMPLE_UNION + main('Shape s = Shape.Circle("bad");'),
                "cannot assign")

    def test_match_non_exhaustive(self):
        run_err(SIMPLE_UNION + main("""\
Shape s = Shape.Circle(1);
match (s) {
    Shape.Circle(r) => { print(r); }
}
"""), "non-exhaustive match")

    def test_match_non_union_scrutinee(self):
        run_err(main("""\
int x = 5;
match (x) {
    _ => { print(x); }
}
"""), "must be a union type")

    def test_wrong_binding_count(self):
        run_err(SIMPLE_UNION + main("""\
Shape s = Shape.Circle(1);
match (s) {
    Shape.Circle(a, b) => { print(a); }
    Shape.Square(x)    => { print(x); }
    Shape.Point        => { }
}
"""), "field(s), but pattern binds")

    def test_no_field_variant_constructed_with_parens(self):
        # Point has no fields; passing args is an error
        run_err(SIMPLE_UNION + main("Shape s = Shape.Point(1);"),
                "expects 0 argument")

    def test_duplicate_union_name(self):
        run_err(SIMPLE_UNION + "union Shape { X { } }\n" + main("return 0;"),
                "already defined")


# ---------------------------------------------------------------------------
# Recursive union (self-referential via pointer)
# ---------------------------------------------------------------------------

class TestRecursiveUnion:
    def test_linked_list_like(self):
        src = """\
union IntList {
    Cons { int head; IntList* tail; }
    Nil  { }
}

int sum(IntList lst) {
    match (lst) {
        IntList.Cons(h, t) => { return h + sum(*t); }
        IntList.Nil        => { return 0; }
    }
}
""" + main("""\
IntList* tail = new IntList.Nil;
IntList* mid  = new IntList.Cons(2, tail);
IntList* head = new IntList.Cons(1, mid);
print(sum(*head));
delete head;
delete mid;
delete tail;
""")
        _, out = run_out(src)
        assert out == ["3"]
