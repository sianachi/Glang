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

    def test_string_index_and_builtins(self):
        src = main(
            'string s = "hello"; '
            'print(s[1]); '
            'print(len(s)); '
            'print(substr(s, 1, 3)); '
            'print(parseInt("0x2a")); '
            'print(parseFloat("3.5")); '
            'print(toString(true)); '
            'print(toString(42)); '
            'print(startsWith(s, "he")); '
            'print(endsWith(s, "lo")); '
            'print(contains(s, "ell")); '
            'print(indexOf(s, "ll")); '
            'print(indexOf(s, "zz")); '
            'return indexOf(s, "ll");'
        )
        code, out = run_out(src)
        assert code == 2
        assert out == [
            "e",
            "5",
            "el",
            "42",
            "3.5",
            "true",
            "42",
            "true",
            "true",
            "true",
            "2",
            "-1",
        ]

    def test_len_array(self):
        src = (
            "class Buf { int[3] data; Buf() {} }\n"
            + main("Buf* b = new Buf(); int n = len(b->data); delete b; return n;")
        )
        assert run(src) == 3

    def test_string_index_out_of_bounds_raises(self):
        with pytest.raises(GRE):
            run(main('string s = "hi"; print(s[2]); return 0;'))

    def test_substr_out_of_bounds_raises(self):
        with pytest.raises(GRE):
            run(main('print(substr("hello", 3, 9)); return 0;'))

    def test_parse_int_invalid_raises(self):
        with pytest.raises(GRE):
            run(main('return parseInt("nope");'))

    def test_parse_float_invalid_raises(self):
        with pytest.raises(GRE):
            run(main('print(parseFloat("nope")); return 0;'))


# ---------------------------------------------------------------------------
# Operator overloading
# ---------------------------------------------------------------------------

class TestOperatorOverloading:
    VEC2 = """
    class Vec2 {
        int x;
        int y;
        Vec2(int x, int y) { this.x = x; this.y = y; }
        Vec2 operator+(Vec2 other) {
            return Vec2(this.x + other.x, this.y + other.y);
        }
        bool operator==(Vec2 other) {
            return this.x == other.x && this.y == other.y;
        }
        bool operator<(Vec2 other) {
            return this.x + this.y < other.x + other.y;
        }
        int operator[](int index) {
            if (index == 0) { return this.x; }
            return this.y;
        }
    }
    """

    def test_operator_plus_and_compound_assignment(self):
        src = self.VEC2 + main(
            "Vec2 a = Vec2(1, 2); "
            "Vec2 b = Vec2(3, 4); "
            "Vec2 c = a + b; "
            "a += b; "
            "print(c.x); "
            "print(c.y); "
            "print(a.x); "
            "return a.y;"
        )
        code, out = run_out(src)
        assert code == 6
        assert out == ["4", "6", "4"]

    def test_operator_equality_and_inequality_fallback(self):
        src = self.VEC2 + main(
            "Vec2 a = Vec2(2, 5); "
            "Vec2 b = Vec2(2, 5); "
            "Vec2 c = Vec2(5, 2); "
            "if (a == b && a != c) { return 1; } "
            "return 0;"
        )
        assert run(src) == 1

    def test_operator_comparison(self):
        src = self.VEC2 + main(
            "Vec2 a = Vec2(1, 1); "
            "Vec2 b = Vec2(2, 3); "
            "if (a < b) { return 1; } "
            "return 0;"
        )
        assert run(src) == 1

    def test_operator_index(self):
        src = self.VEC2 + main("Vec2 a = Vec2(8, 13); return a[1];")
        assert run(src) == 13


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

    def test_do_while_runs_at_least_once(self):
        assert run(main("int i = 0; do { i = i + 1; } while (false); return i;")) == 1

    def test_do_while_continue_checks_condition(self):
        assert run(main(
            "int i = 0; int s = 0;"
            "do { ++i; if (i == 2) { continue; } s = s + i; } while (i < 3);"
            "return s;"
        )) == 4

    def test_foreach_string(self):
        assert run(main(
            'int count = 0; foreach (char c in "abcd") { count = count + 1; } return count;'
        )) == 4

    def test_foreach_array(self):
        assert run(
            "class Buf { int[3] data; Buf() {} }\n"
            + main(
                "Buf b = Buf();"
                "b.data[0] = 1; b.data[1] = 2; b.data[2] = 3;"
                "int sum = 0;"
                "foreach (int x in b.data) { sum = sum + x; }"
                "return sum;"
            )
        ) == 6

    def test_foreach_iterable_class(self):
        assert run(
            "class Bag { Bag() {} int length() { return 3; } int get(int i) { return i + 2; } }\n"
            + main(
                "Bag b = Bag(); int sum = 0;"
                "foreach (int x in b) { sum = sum + x; }"
                "return sum;"
            )
        ) == 9

    def test_foreach_break_and_continue(self):
        assert run(main(
            "int count = 0;"
            "foreach (char c in \"abcd\") {"
            "  if (c == 'b') { continue; }"
            "  if (c == 'd') { break; }"
            "  count = count + 1;"
            "}"
            "return count;"
        )) == 2

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


class TestFunctionPointersAndClosures:
    def test_store_and_call_function_pointer(self):
        src = (
            "int add(int a, int b) { return a + b; }\n"
            + main("fn(int, int) -> int op = add; return op(3, 4);")
        )
        assert run(src) == 7

    def test_pass_and_return_function_pointer(self):
        src = (
            "int inc(int x) { return x + 1; }\n"
            "int apply(fn(int) -> int f, int x) { return f(x); }\n"
            "fn(int) -> int choose() { return inc; }\n"
            + main("fn(int) -> int f = choose(); return apply(f, 6);")
        )
        assert run(src) == 7

    def test_static_method_function_pointer(self):
        src = (
            "class C { static int twice(int x) { return x * 2; } }\n"
            + main("fn(int) -> int f = C.twice; return f(6);")
        )
        assert run(src) == 12

    def test_null_function_pointer_call_raises(self):
        with pytest.raises(GRE):
            run(main("fn(int) -> int f = null; return f(1);"))

    def test_closure_capture_snapshot(self):
        src = main(
            "int x = 10; "
            "fn() -> int f = () -> int { return x; }; "
            "x = 20; "
            "return f();"
        )
        assert run(src) == 10

    def test_closure_mutates_private_capture(self):
        src = main(
            "int x = 0; "
            "fn() -> int f = () -> int { x = x + 1; return x; }; "
            "int a = f(); "
            "int b = f(); "
            "return a * 100 + b * 10 + x;"
        )
        assert run(src) == 120

    def test_closure_uses_this(self):
        src = (
            "class C { "
            "  int base; "
            "  C(int b) { this.base = b; } "
            "  fn(int) -> int make() { "
            "    return (int x) -> int { return this.base + x; }; "
            "  } "
            "}\n"
            + main(
                "C* c = new C(5); "
                "fn(int) -> int f = c->make(); "
                "int r = f(3); "
                "delete c; "
                "return r;"
            )
        )
        assert run(src) == 8


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


class TestBlockAlloc:
    def test_alloc_block_write_read(self):
        body = (
            "int* p = alloc(int, 4);"
            "for (int i = 0; i < 4; ++i) { p[i] = i * i; }"
            "int sum = 0;"
            "for (int i = 0; i < 4; ++i) { sum = sum + p[i]; }"
            "free(p); return sum;"
        )
        assert run(main(body)) == 14

    def test_alloc_block_is_zero_initialised(self):
        assert run(main("int* p = alloc(int, 3); int v = p[2]; free(p); return v;")) == 0

    def test_alloc_block_index_assignment(self):
        assert run(main("int* p = alloc(int, 2); p[1] = 7; int v = p[1]; free(p); return v;")) == 7

    def test_block_index_out_of_bounds_raises(self):
        with pytest.raises(GRE):
            run(main("int* p = alloc(int, 2); return p[5];"))

    def test_block_use_after_free_raises(self):
        with pytest.raises(GRE):
            run(main("int* p = alloc(int, 2); free(p); p[0] = 1; return 0;"))

    def test_string_block(self):
        body = (
            'string* names = alloc(string, 2);'
            'names[0] = "a"; names[1] = "b";'
            'string r = names[0] + names[1]; free(names); return len(r);'
        )
        assert run(main(body)) == 2


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
    def test_self_referential_node_links(self):
        src = (
            "class Node {\n"
            "  int value;\n"
            "  Node* next;\n"
            "  Node(int v) { this.value = v; this.next = null; }\n"
            "}\n"
            + main(
                "Node* first = new Node(10); "
                "Node* second = new Node(32); "
                "first->next = second; "
                "int result = first->value + first->next->value; "
                "delete second; "
                "delete first; "
                "return result;"
            )
        )
        assert run(src) == 42

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


class TestByte:
    def test_add_wraps(self):
        assert run(main("byte a = 200; byte b = 100; byte c = a + b; return (int) c;")) == 44

    def test_subtract_wraps(self):
        assert run(main("byte a = 10; byte b = 20; byte c = a - b; return (int) c;")) == 246

    def test_multiply_wraps(self):
        assert run(main("byte a = 100; byte b = 3; byte c = a * b; return (int) c;")) == 44

    def test_and_with_literal(self):
        assert run(main("byte a = 200; byte m = a & 0x0F; return (int) m;")) == 8

    def test_shift_left_wraps(self):
        assert run(main("byte a = 200; byte s = a << 1; return (int) s;")) == 144

    def test_bitwise_not_masks(self):
        assert run(main("byte a = 200; byte n = ~a; return (int) n;")) == 55

    def test_increment_wraps(self):
        assert run(main("byte a = 255; ++a; return (int) a;")) == 0

    def test_compound_assign_wraps(self):
        assert run(main("byte a = 250; a += 10; return (int) a;")) == 4

    def test_literal_coercion_masks_on_cast(self):
        assert run(main("byte a = (byte) 300; return (int) a;")) == 44

    def test_int_to_byte_masks(self):
        assert run(main("int i = 511; byte b = (byte) i; return (int) b;")) == 255

    def test_byte_to_char_roundtrip(self):
        assert run(main("byte b = 65; char c = (char) b; if (c == 'A') { return 1; } return 0;")) == 1

    def test_alloc_block_zero_init(self):
        assert run(main("byte* p = alloc(byte, 3); byte v = p[1]; free(p); return (int) v;")) == 0

    def test_alloc_block_write_read(self):
        body = (
            "byte* p = alloc(byte, 3); p[0] = 10; p[1] = (byte) 300; p[2] = 0xFF;"
            "byte v = p[2]; free(p); return (int) v;"
        )
        assert run(main(body)) == 255

    def test_comparison(self):
        assert run(main("byte a = 5; byte b = 9; if (a < b) { return 1; } return 0;")) == 1


class TestByteInterop:
    def test_bytes_from_string_codepoints(self):
        body = "byte* p = bytesFromString(\"Hi!\"); byte b = p[0]; free(p); return (int) b;"
        assert run(main(body)) == ord("H")

    def test_string_from_bytes_roundtrip(self):
        _, out = run_out(
            'int main() { byte* p = bytesFromString("Hi!"); '
            'string s = stringFromBytes(p, 3); print(s); free(p); return 0; }'
        )
        assert out == ["Hi!"]

    def test_string_from_bytes_out_of_bounds_raises(self):
        with pytest.raises(GRE):
            run(main('byte* p = bytesFromString("hi"); '
                     'string s = stringFromBytes(p, 5); free(p); return 0;'))


# ---------------------------------------------------------------------------
# Compiler I/O: getArgCount / getArg / printErr / exit
# ---------------------------------------------------------------------------

def _build_with_args(src: str, prog_args=None):
    tokens = Lexer(src).tokenize()
    prog = Parser(tokens).parse()
    env = Analyser().analyse(prog)
    interp = Interpreter(env, prog_args=prog_args)
    return prog, interp


class TestCompilerIO:
    def test_get_arg_count_zero_by_default(self):
        prog, interp = _build_with_args(main("return getArgCount();"))
        assert interp.run(prog) == 0

    def test_get_arg_count_with_args(self):
        prog, interp = _build_with_args(
            main("return getArgCount();"), prog_args=["a", "b"]
        )
        assert interp.run(prog) == 2

    def test_get_arg_returns_correct_value(self):
        prog, interp = _build_with_args(
            'int main() { print(getArg(0)); print(getArg(1)); return 0; }',
            prog_args=["hello", "world"],
        )
        interp.run(prog)
        assert interp.output == ["hello", "world"]

    def test_get_arg_out_of_bounds_raises(self):
        with pytest.raises(GRE):
            prog, interp = _build_with_args(main("string s = getArg(5); return 0;"))
            interp.run(prog)

    def test_print_err_goes_to_err_output_not_output(self):
        prog, interp = _build_with_args(main('printErr("oops"); return 0;'))
        interp.run(prog)
        assert interp.err_output == ["oops"]
        assert interp.output == []

    def test_print_err_int(self):
        prog, interp = _build_with_args(main("printErr(42); return 0;"))
        interp.run(prog)
        assert interp.err_output == ["42"]

    def test_exit_zero(self):
        prog, interp = _build_with_args(main("exit(0); return 99;"))
        assert interp.run(prog) == 0

    def test_exit_nonzero(self):
        prog, interp = _build_with_args(main("exit(42); return 0;"))
        assert interp.run(prog) == 42

    def test_exit_from_nested_function(self):
        src = (
            "void helper() { exit(7); }\n"
            "int main() { helper(); return 0; }\n"
        )
        prog, interp = _build_with_args(src)
        assert interp.run(prog) == 7

    def test_exit_short_circuits_remaining_code(self):
        prog, interp = _build_with_args(
            main('exit(1); print("never reached"); return 0;')
        )
        interp.run(prog)
        assert interp.output == []
