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
        assert decl.type_param_bounds == {}

    def test_multiple_type_params(self):
        prog = parse("class Pair<K, V> { K k; V v; Pair() {} }")
        assert prog.declarations[0].type_params == ["K", "V"]

    def test_generic_class_records_bounds(self):
        prog = parse("class Box<T extends Named> { T value; Box(T v) { this.value = v; } }")
        decl = prog.declarations[0]
        assert isinstance(decl, ClassDecl)
        assert decl.type_params == ["T"]
        assert isinstance(decl.type_param_bounds["T"][0], NamedType)
        assert decl.type_param_bounds["T"][0].name == "Named"

    def test_generic_function_records_type_params(self):
        prog = parse("T identity<T>(T x) { return x; }")
        decl = prog.declarations[0]
        assert isinstance(decl, FunctionDecl)
        assert decl.type_params == ["T"]

    def test_generic_function_records_bounds(self):
        prog = parse("T keep<T extends Named>(T x) { return x; }")
        decl = prog.declarations[0]
        assert isinstance(decl, FunctionDecl)
        assert decl.type_params == ["T"]
        assert isinstance(decl.type_param_bounds["T"][0], NamedType)
        assert decl.type_param_bounds["T"][0].name == "Named"

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

    def test_generic_function_infers_type_args(self):
        src = "T identity<T>(T x) { return x; }\n"
        src += "int main() { print(identity(42)); return identity(7); }"
        code, out = run_out(src)
        assert code == 7
        assert out == ["42"]

    def test_generic_function_infers_nested_generic_arg(self):
        src = BOX + """
        T unwrap<T>(Box<T> box) { return box.get(); }
        int main() {
            Box<int> b = Box<int>(11);
            return unwrap(b);
        }
        """
        code, out = run_out(src)
        assert code == 11

    def test_generic_class_constructor_infers_type_args(self):
        src = BOX + """
        int main() {
            Box<int> b = Box(9);
            return b.get();
        }
        """
        code, out = run_out(src)
        assert code == 9

    def test_var_local_type_inference(self):
        src = "T identity<T>(T x) { return x; }\n"
        src += "int main() { var x = identity(42); print(x); return x; }"
        code, out = run_out(src)
        assert code == 42
        assert out == ["42"]

    def test_var_infers_generic_class_construction(self):
        src = BOX + """
        int main() {
            var b = Box(7);
            return b.get();
        }
        """
        code, out = run_out(src)
        assert code == 7

    def test_generic_bound_accepts_interface_implementation(self):
        src = """
        interface Named { string name(); }
        class Person implements Named {
            Person() {}
            string name() { return "Ada"; }
        }
        T keep<T extends Named>(T x) { return x; }
        int main() {
            Person p = Person();
            var q = keep(p);
            print(q.name());
            return 0;
        }
        """
        code, out = run_out(src)
        assert out == ["Ada"]

    def test_generic_class_bound_accepts_interface_implementation(self):
        src = """
        interface Named { string name(); }
        class Person implements Named {
            Person() {}
            string name() { return "Ada"; }
        }
        class Box<T extends Named> {
            T value;
            Box(T v) { this.value = v; }
            T get() { return this.value; }
        }
        int main() {
            var box = Box(Person());
            print(box.get().name());
            return 0;
        }
        """
        code, out = run_out(src)
        assert out == ["Ada"]

    def test_multiple_bounds_parse_as_a_list(self):
        prog = parse("T d<T extends Named & Aged>(T x) { return x; }")
        bounds = prog.declarations[0].type_param_bounds["T"]
        assert [b.name for b in bounds] == ["Named", "Aged"]

    def test_multiple_bounds_accept_type_satisfying_all(self):
        src = """
        interface Named { string name(); }
        interface Aged { int age(); }
        class Person implements Named, Aged {
            Person() {}
            string name() { return "Ada"; }
            int age() { return 36; }
        }
        string describe<T extends Named & Aged>(T x) {
            return x.name() + toString(x.age());
        }
        int main() {
            print(describe(Person()));
            return 0;
        }
        """
        code, out = run_out(src)
        assert out == ["Ada36"]

    def test_multiple_bounds_reject_type_missing_one(self):
        # OnlyNamed satisfies Named but not Aged, so it fails the Aged bound.
        err(
            """
            interface Named { string name(); }
            interface Aged { int age(); }
            class OnlyNamed implements Named {
                OnlyNamed() {}
                string name() { return "x"; }
            }
            string describe<T extends Named & Aged>(T x) { return x.name(); }
            int main() { print(describe(OnlyNamed())); return 0; }
            """,
            "does not satisfy bound 'Aged'",
        )

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

    def test_inference_conflict_raises(self):
        err(
            'T choose<T>(T a, T b) { return a; } int main() { choose(1, "x"); return 0; }',
            "cannot infer type argument 'T'",
        )

    def test_inference_requires_evidence(self):
        err(
            "T make<T>() { return T(); } int main() { make(); return 0; }",
            "cannot infer type argument 'T'",
        )

    def test_bound_rejects_non_implementation(self):
        err(
            """
            interface Named { string name(); }
            class Rock { Rock() {} }
            T keep<T extends Named>(T x) { return x; }
            int main() { Rock r = Rock(); keep(r); return 0; }
            """,
            "does not satisfy bound",
        )

    def test_var_cannot_infer_from_null(self):
        err("int main() { var x = null; return 0; }", "cannot infer type of 'var'")
