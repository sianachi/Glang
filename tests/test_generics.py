import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from lexer.lexer import Lexer
from parser.parser import Parser
from parser.ast_nodes import (
    ClassDecl, FunctionDecl, GenericType, NamedType,
)
from analyser.analyser import Analyser
from analyser.monomorphize import Monomorphizer, mangle
from interpreter.interpreter import Interpreter
from errors.errors import TypeError as GTypeError


# ---------------------------------------------------------------------------
# Harness
# ---------------------------------------------------------------------------

def parse(src: str):
    return Parser(Lexer(src).tokenize()).parse()


def run_out(src: str):
    prog = parse(src)
    env = Analyser().analyse(prog)
    interp = Interpreter(env)
    return interp.run(prog), interp.output


def class_names(src: str) -> set:
    """The concrete class names registered after monomorphization."""
    prog = parse(src)
    env = Analyser().analyse(prog)
    return set(env.classes.keys())


def err(src: str, fragment: str) -> None:
    with pytest.raises(GTypeError) as info:
        Analyser().analyse(parse(src))
    assert fragment in info.value.msg, f"expected {fragment!r} in {info.value.msg!r}"


BOX = """
class Box<T> {
    T value;
    Box(T v) { this.value = v; }
    T get() { return this.value; }
    void set(T v) { this.value = v; }
}
"""


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

class TestGenericParsing:
    def test_generic_class_records_type_params(self):
        prog = parse("class Box<T> { T value; Box(T v) { this.value = v; } }")
        decl = prog.declarations[0]
        assert isinstance(decl, ClassDecl)
        assert decl.type_params == ["T"]

    def test_multiple_type_params(self):
        prog = parse("class Pair<K, V> { K k; V v; Pair() {} }")
        assert prog.declarations[0].type_params == ["K", "V"]

    def test_generic_function_records_type_params(self):
        prog = parse("T identity<T>(T x) { return x; }")
        decl = prog.declarations[0]
        assert isinstance(decl, FunctionDecl)
        assert decl.type_params == ["T"]

    def test_generic_type_in_field(self):
        prog = parse("class C { List<int> xs; C() {} }")
        field = prog.declarations[0].fields[0]
        assert isinstance(field.type, GenericType)
        assert field.type.name == "List"

    def test_comparison_is_not_generic(self):
        # `a < b` must still parse as a comparison, not a generic.
        prog = parse("bool f(int a, int b) { return a < b; }")
        assert isinstance(prog.declarations[0], FunctionDecl)


# ---------------------------------------------------------------------------
# Monomorphization
# ---------------------------------------------------------------------------

class TestMonomorphization:
    def test_distinct_instantiations_are_separate_classes(self):
        src = BOX + """
        int main() {
            Box<int> a = Box<int>(1);
            Box<string> b = Box<string>("x");
            return 0;
        }
        """
        names = class_names(src)
        assert "Box<int>" in names
        assert "Box<string>" in names
        assert "Box" not in names  # the template itself is gone

    def test_template_removed_from_program(self):
        prog = parse(BOX + "int main() { Box<int> a = Box<int>(1); return 0; }")
        Monomorphizer().run(prog)
        names = {getattr(d, "name", None) for d in prog.declarations}
        assert "Box<int>" in names
        assert "Box" not in names

    def test_unused_template_is_dropped(self):
        # A generic class never instantiated produces no concrete class.
        names = class_names(BOX + "int main() { return 0; }")
        assert not any(n.startswith("Box") for n in names)

    def test_mangle_format(self):
        assert mangle("List", [NamedType("int")]) == "List<int>"
        assert mangle("Map", [NamedType("string"), NamedType("int")]) == "Map<string,int>"


# ---------------------------------------------------------------------------
# Execution
# ---------------------------------------------------------------------------

class TestGenericExecution:
    def test_box_int_and_string(self):
        src = BOX + """
        int main() {
            Box<int> a = Box<int>(7);
            Box<string> b = Box<string>("hi");
            print(a.get());
            print(b.get());
            return a.get();
        }
        """
        code, out = run_out(src)
        assert code == 7
        assert out == ["7", "hi"]

    def test_generic_function_explicit_args(self):
        src = "T identity<T>(T x) { return x; }\n"
        src += "int main() { print(identity<int>(42)); return 0; }"
        code, out = run_out(src)
        assert out == ["42"]

    def test_growable_generic_list(self):
        src = """
        class List<T> {
            T* data; int cap; int size;
            List() { this.cap = 2; this.size = 0; this.data = alloc(T, 2); }
            void add(T x) {
                if (this.size == this.cap) {
                    int nc = this.cap * 2;
                    T* b = alloc(T, nc);
                    for (int i = 0; i < this.size; ++i) { b[i] = this.data[i]; }
                    free(this.data); this.data = b; this.cap = nc;
                }
                this.data[this.size] = x; this.size = this.size + 1;
            }
            T get(int i) { return this.data[i]; }
            int length() { return this.size; }
        }
        int main() {
            List<int> xs = List<int>();
            for (int i = 0; i < 5; ++i) { xs.add(i); }
            int total = 0;
            for (int i = 0; i < xs.length(); ++i) { total = total + xs.get(i); }
            print(xs.length());
            return total;
        }
        """
        code, out = run_out(src)
        assert out == ["5"]
        assert code == 0 + 1 + 2 + 3 + 4

    def test_nested_generic(self):
        src = BOX + """
        int main() {
            Box<Box<int>> bb = Box<Box<int>>(Box<int>(42));
            Box<int> inner = bb.get();
            print(inner.get());
            return 0;
        }
        """
        code, out = run_out(src)
        assert out == ["42"]


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------

class TestGenericErrors:
    def test_unknown_generic_class(self):
        err("int main() { Foo<int> x = Foo<int>(); return 0; }",
            "is not a generic")

    def test_arity_mismatch(self):
        err("class P<A, B> { A a; P() {} }\n"
            "int main() { P<int> p = P<int>(); return 0; }",
            "expects 2 type argument(s)")

    def test_type_error_inside_instantiation(self):
        # Box<int>.get() returns int; assigning to a string must fail.
        err(BOX + 'int main() { Box<int> a = Box<int>(1); string s = a.get(); return 0; }',
            "")
