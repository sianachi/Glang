import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from lexer.lexer import Lexer
from parser.parser import Parser
from analyser.analyser import Analyser
from interpreter.interpreter import Interpreter
from errors.errors import RuntimeError as GRE


# ---------------------------------------------------------------------------
# Harness
# ---------------------------------------------------------------------------

def _build(src: str):
    tokens = Lexer(src).tokenize()
    prog = Parser(tokens).parse()
    env = Analyser().analyse(prog)
    return prog, Interpreter(env)


def run(src: str) -> int:
    """Lex -> parse -> analyse -> interpret; return main()'s exit code."""
    prog, interp = _build(src)
    return interp.run(prog)


def run_out(src: str):
    """Like run(), but also return the captured print() output lines."""
    prog, interp = _build(src)
    code = interp.run(prog)
    return code, interp.output


def main(body: str) -> str:
    """Wrap a statement body in an int main()."""
    return f"int main() {{ {body} }}"


# ---------------------------------------------------------------------------
# Arithmetic & precedence
# ---------------------------------------------------------------------------

class TestArithmetic:
    def test_precedence(self):
        assert run(main("return 2 + 3 * 4;")) == 14

    def test_parens(self):
        assert run(main("return (2 + 3) * 4;")) == 20

    def test_int_division_truncates(self):
        assert run(main("return 7 / 2;")) == 3

    def test_negative_division_truncates_toward_zero(self):
        assert run(main("return (-7) / 2;")) == -3

    def test_modulo(self):
        assert run(main("return 7 % 3;")) == 1

    def test_negative_modulo_c_style(self):
        assert run(main("return (-7) % 2;")) == -1

    def test_division_by_zero(self):
        with pytest.raises(GRE):
            run(main("int z = 0; return 5 / z;"))

    def test_float_arithmetic(self):
        assert run(main("float a = 1.5; float b = 2.5; float c = a + b; "
                        "if (c == 4.0) { return 1; } return 0;")) == 1

    def test_bitwise_and(self):
        assert run(main("return 12 & 10;")) == 8

    def test_bitwise_or(self):
        assert run(main("return 12 | 10;")) == 14

    def test_xor(self):
        assert run(main("return 12 ^ 10;")) == 6

    def test_shift_left(self):
        assert run(main("return 1 << 4;")) == 16

    def test_shift_right_arithmetic(self):
        assert run(main("return (-8) >> 1;")) == -4

    def test_bitwise_not(self):
        assert run(main("return ~0;")) == -1


# ---------------------------------------------------------------------------
# Logical & comparison
# ---------------------------------------------------------------------------

class TestLogical:
    SRC = (
        "bool t() { print(\"t\"); return true; }\n"
        "bool f() { print(\"f\"); return false; }\n"
    )

    def test_and_short_circuits(self):
        code, out = run_out(self.SRC + main("if (f() && t()) { return 1; } return 0;"))
        assert code == 0
        assert out == ["f"]  # t() never evaluated

    def test_or_short_circuits(self):
        code, out = run_out(self.SRC + main("if (t() || f()) { return 1; } return 0;"))
        assert code == 1
        assert out == ["t"]  # f() never evaluated

    def test_not(self):
        assert run(main("bool b = false; if (!b) { return 1; } return 0;")) == 1

    def test_comparisons(self):
        assert run(main("if (3 < 5 && 5 <= 5 && 6 > 2 && 2 >= 2) { return 1; } return 0;")) == 1

    def test_equality(self):
        assert run(main("if (3 == 3 && 3 != 4) { return 1; } return 0;")) == 1


# ---------------------------------------------------------------------------
# Strings
# ---------------------------------------------------------------------------

class TestStrings:
    def test_concatenation_output(self):
        code, out = run_out(main('string s = "ab" + "cd"; print(s); return 0;'))
        assert code == 0
        assert out == ["abcd"]

    def test_string_equality(self):
        assert run(main('string s = "ab" + "c"; if (s == "abc") { return 1; } return 0;')) == 1

    def test_string_inequality(self):
        assert run(main('if ("a" != "b") { return 1; } return 0;')) == 1


# ---------------------------------------------------------------------------
# print builtin
# ---------------------------------------------------------------------------

class TestPrint:
    def test_print_int(self):
        _, out = run_out(main("print(42); return 0;"))
        assert out == ["42"]

    def test_print_bool(self):
        _, out = run_out(main("print(true); print(false); return 0;"))
        assert out == ["true", "false"]

    def test_print_char(self):
        _, out = run_out(main("print('z'); return 0;"))
        assert out == ["z"]


# ---------------------------------------------------------------------------
# Control flow
# ---------------------------------------------------------------------------

class TestControlFlow:
    def test_if_elseif_else(self):
        src = (
            "int classify(int n) {\n"
            "  if (n < 0) { return -1; } else if (n == 0) { return 0; } else { return 1; }\n"
            "}\n"
            + main("return classify(5) + classify(-3) + classify(0);")
        )
        assert run(src) == 0

    def test_while(self):
        assert run(main("int i = 0; int s = 0; while (i < 5) { s = s + i; i = i + 1; } return s;")) == 10

    def test_for(self):
        assert run(main("int s = 0; for (int i = 0; i < 5; ++i) { s = s + i; } return s;")) == 10

    def test_break(self):
        assert run(main(
            "int s = 0; for (int i = 0; i < 10; ++i) { if (i == 5) { break; } s = s + 1; } return s;"
        )) == 5

    def test_continue(self):
        assert run(main(
            "int s = 0; for (int i = 0; i < 5; ++i) { if (i == 2) { continue; } s = s + i; } return s;"
        )) == 8

    def test_nested_loops(self):
        assert run(main(
            "int c = 0; for (int i = 0; i < 3; ++i) { for (int j = 0; j < 3; ++j) { c = c + 1; } } return c;"
        )) == 9


# ---------------------------------------------------------------------------
# Functions
# ---------------------------------------------------------------------------

class TestFunctions:
    def test_recursion_factorial(self):
        src = (
            "int fact(int n) { if (n <= 1) { return 1; } return n * fact(n - 1); }\n"
            + main("return fact(5);")
        )
        assert run(src) == 120

    def test_recursion_fibonacci(self):
        src = (
            "int fib(int n) { if (n < 2) { return n; } return fib(n - 1) + fib(n - 2); }\n"
            + main("return fib(10);")
        )
        assert run(src) == 55

    def test_out_parameters(self):
        src = (
            "void divmod(int a, int b, int* q, int* r) { *q = a / b; *r = a % b; }\n"
            + main("int q = 0; int r = 0; divmod(17, 5, &q, &r); return q * 100 + r;")
        )
        assert run(src) == 302

    def test_void_function(self):
        src = (
            "void noop() { return; }\n"
            + main("noop(); return 7;")
        )
        assert run(src) == 7


# ---------------------------------------------------------------------------
# Pointers & memory
# ---------------------------------------------------------------------------

class TestPointers:
    def test_alloc_write_read_free(self):
        assert run(main("int* p = alloc(int); *p = 42; int v = *p; free(p); return v;")) == 42

    def test_address_of_aliasing(self):
        assert run(main("int x = 1; int* p = &x; *p = 99; return x;")) == 99

    def test_null_comparison(self):
        assert run(main("int* p = null; if (p == null) { return 1; } return 0;")) == 1

    def test_non_null_comparison(self):
        assert run(main("int* p = alloc(int); int r = 0; if (p != null) { r = 1; } free(p); return r;")) == 1


# ---------------------------------------------------------------------------
# Runtime errors
# ---------------------------------------------------------------------------

class TestRuntimeErrors:
    def test_null_dereference(self):
        with pytest.raises(GRE):
            run(main("int* p = null; return *p;"))

    def test_double_free(self):
        with pytest.raises(GRE):
            run(main("int* p = alloc(int); free(p); free(p); return 0;"))

    def test_use_after_free(self):
        with pytest.raises(GRE):
            run(main("int* p = alloc(int); *p = 1; free(p); return *p;"))

    def test_array_out_of_bounds(self):
        src = (
            "class Buf { int[3] data; Buf() {} }\n"
            + main("Buf* b = new Buf(); return b->data[5];")
        )
        with pytest.raises(GRE):
            run(src)


# ---------------------------------------------------------------------------
# Classes
# ---------------------------------------------------------------------------

class TestClasses:
    def test_fields_and_methods(self):
        src = (
            "class Counter {\n"
            "  int n;\n"
            "  Counter() { this.n = 0; }\n"
            "  void inc() { this.n = this.n + 1; }\n"
            "  int get() { return this.n; }\n"
            "}\n"
            + main("Counter* c = new Counter(); c->inc(); c->inc(); int v = c->get(); delete c; return v;")
        )
        assert run(src) == 2

    def test_array_field_indexing(self):
        src = (
            "class Buf { int[3] data; Buf() {} }\n"
            + main("Buf* b = new Buf(); b->data[1] = 7; return b->data[1];")
        )
        assert run(src) == 7

    def test_static_field_and_method(self):
        src = (
            "class C { static int count = 5; static int get() { return C.count; } }\n"
            + main("return C.get();")
        )
        assert run(src) == 5

    def test_static_field_mutation_via_constructor(self):
        src = (
            "class C {\n"
            "  static int count = 0;\n"
            "  C() { C.count += 1; }\n"
            "  static int get() { return C.count; }\n"
            "}\n"
            + main("C* a = new C(); C* b = new C(); return C.get();")
        )
        assert run(src) == 2


# ---------------------------------------------------------------------------
# Inheritance & polymorphism
# ---------------------------------------------------------------------------

class TestInheritance:
    ANIMALS = (
        "class Animal { int sound() { return 1; } }\n"
        "class Dog extends Animal { int sound() { return 2; } }\n"
    )

    def test_virtual_dispatch_through_base_pointer(self):
        assert run(self.ANIMALS + main("Animal* a = new Dog(); return a->sound();")) == 2

    def test_super_method_call(self):
        src = (
            "class Animal { int sound() { return 1; } }\n"
            "class Dog extends Animal { int sound() { return super.sound() + 10; } }\n"
            + main("Dog* d = new Dog(); return d->sound();")
        )
        assert run(src) == 11

    def test_super_constructor_chaining(self):
        src = (
            "class Animal { int legs; Animal(int l) { this.legs = l; } }\n"
            "class Dog extends Animal { Dog() : super(4) {} }\n"
            + main("Dog* d = new Dog(); int v = d->legs; delete d; return v;")
        )
        assert run(src) == 4

    def test_interface_implementation(self):
        src = (
            "interface Shape { int area(); }\n"
            "class Square implements Shape {\n"
            "  int side;\n"
            "  Square(int s) { this.side = s; }\n"
            "  int area() { return this.side * this.side; }\n"
            "}\n"
            + main("Square* sq = new Square(3); int a = sq->area(); delete sq; return a;")
        )
        assert run(src) == 9


# ---------------------------------------------------------------------------
# Destructors
# ---------------------------------------------------------------------------

class TestDestructors:
    def test_destructor_chain_order(self):
        # ~Derived subtracts 10, ~Base subtracts 1; both run on delete.
        src = (
            "class Base {\n"
            "  static int live = 0;\n"
            "  Base() { Base.live += 1; }\n"
            "  ~Base() { Base.live -= 1; }\n"
            "}\n"
            "class Derived extends Base {\n"
            "  Derived() : super() {}\n"
            "  ~Derived() { Base.live -= 10; }\n"
            "}\n"
            + main("Base* b = new Derived(); delete b; return Base.live;")
        )
        assert run(src) == -10

    def test_delete_null_is_noop(self):
        src = (
            "class Base { Base() {} }\n"
            + main("Base* b = null; delete b; return 0;")
        )
        assert run(src) == 0

    def test_double_delete_errors(self):
        src = (
            "class Base { Base() {} ~Base() {} }\n"
            + main("Base* b = new Base(); delete b; delete b; return 0;")
        )
        with pytest.raises(GRE):
            run(src)


# ---------------------------------------------------------------------------
# Casts
# ---------------------------------------------------------------------------

class TestCasts:
    def test_float_to_int_truncates(self):
        assert run(main("float f = 3.9; int i = (int) f; return i;")) == 3

    def test_int_to_char(self):
        assert run(main("char c = (char) 65; if (c == 'A') { return 1; } return 0;")) == 1

    def test_char_to_int(self):
        assert run(main("char c = 'A'; int n = (int) c; return n;")) == 65
