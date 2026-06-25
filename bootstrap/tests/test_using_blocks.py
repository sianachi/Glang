"""Tests for the C#-style `using (T x = expr) { ... }` resource block."""

import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from lexer.lexer import Lexer
from parser.parser import Parser
from analyser.analyser import Analyser
from interpreter.interpreter import Interpreter
from errors.errors import (
    TypeError as GTE,
    RuntimeError as GRE,
    ParseError,
)


# ---------------------------------------------------------------------------
# Harness
# ---------------------------------------------------------------------------

def _build(src: str):
    prog = Parser(Lexer(src).tokenize()).parse()
    env = Analyser().analyse(prog)
    return prog, Interpreter(env)


def run(src: str) -> int:
    prog, interp = _build(src)
    return interp.run(prog)


def run_out(src: str):
    prog, interp = _build(src)
    code = interp.run(prog)
    return code, interp.output


def err(src: str, fragment: str):
    with pytest.raises(GTE) as exc:
        Analyser().analyse(Parser(Lexer(src).tokenize()).parse())
    assert fragment in str(exc.value)


# A heap resource with an observable destructor.
RES = """
class Res {
    int id;
    Res(int id) { this.id = id; print("open " + toString(this.id)); }
    ~Res() { print("close " + toString(this.id)); }
}
"""

# A value resource with an observable dispose().
HANDLE = """
class Handle {
    int* data;
    Handle(int n) { this.data = alloc(int, n); }
    int get(int i) { return this.data[i]; }
    void set(int i, int v) { this.data[i] = v; }
    void dispose() { print("disposed"); free(this.data); }
}
"""


# ---------------------------------------------------------------------------
# Disposal paths
# ---------------------------------------------------------------------------

class TestDisposalPaths:
    def test_class_pointer_runs_destructor_at_scope_exit(self):
        _, out = run_out(RES + """
            int main() {
                using (Res* r = new Res(1)) {
                    print("body");
                }
                print("after");
                return 0;
            }
        """)
        assert out == ["open 1", "body", "close 1", "after"]

    def test_class_value_calls_dispose(self):
        _, out = run_out(HANDLE + """
            int main() {
                using (Handle h = Handle(4)) {
                    h.set(0, 9);
                    print(h.get(0));
                }
                print("after");
                return 0;
            }
        """)
        assert out == ["9", "disposed", "after"]

    def test_raw_pointer_is_freed(self):
        # Capture the pointer; touching it after the block is use-after-free.
        with pytest.raises(GRE) as exc:
            run("""
                int main() {
                    int* keep = null;
                    using (int* p = alloc(int, 2)) {
                        p[0] = 5;
                        keep = p;
                    }
                    return keep[0];
                }
            """)
        assert "use after free" in str(exc.value)

    def test_destructor_chain_runs_for_subclass(self):
        _, out = run_out("""
            class Base {
                Base() { }
                ~Base() { print("~Base"); }
            }
            class Derived extends Base {
                Derived() : super() { }
                ~Derived() { print("~Derived"); }
            }
            int main() {
                using (Derived* d = new Derived()) { }
                return 0;
            }
        """)
        assert out == ["~Derived", "~Base"]

    def test_null_resource_is_noop(self):
        assert run(RES + """
            int main() {
                using (Res* r = null) { }
                return 7;
            }
        """) == 7

    def test_manual_delete_inside_block_is_safe(self):
        _, out = run_out(RES + """
            int main() {
                using (Res* r = new Res(1)) {
                    delete r;
                    print("released early");
                }
                print("no double free");
                return 0;
            }
        """)
        assert out == ["open 1", "close 1", "released early", "no double free"]

    def test_manual_free_inside_block_is_safe(self):
        assert run("""
            int main() {
                using (int* p = alloc(int, 2)) {
                    free(p);
                }
                return 3;
            }
        """) == 3

    def test_nested_using_disposes_inner_first(self):
        _, out = run_out(RES + """
            int main() {
                using (Res* a = new Res(1)) {
                    using (Res* b = new Res(2)) {
                        print("inner");
                    }
                    print("outer");
                }
                return 0;
            }
        """)
        assert out == ["open 1", "open 2", "inner", "close 2", "outer", "close 1"]


# ---------------------------------------------------------------------------
# Early exits
# ---------------------------------------------------------------------------

class TestEarlyExits:
    def test_return_disposes_before_leaving(self):
        _, out = run_out(RES + """
            int helper() {
                using (Res* r = new Res(1)) {
                    print("returning");
                    return 5;
                }
            }
            int main() {
                int v = helper();
                print("got " + toString(v));
                return 0;
            }
        """)
        assert out == ["open 1", "returning", "close 1", "got 5"]

    def test_break_disposes_each_iteration(self):
        _, out = run_out(RES + """
            int main() {
                for (int i = 1; i <= 3; ++i) {
                    using (Res* r = new Res(i)) {
                        if (i == 2) { break; }
                        print("iter " + toString(i));
                    }
                }
                return 0;
            }
        """)
        assert out == ["open 1", "iter 1", "close 1", "open 2", "close 2"]

    def test_continue_disposes(self):
        _, out = run_out(RES + """
            int main() {
                for (int i = 1; i <= 2; ++i) {
                    using (Res* r = new Res(i)) {
                        continue;
                    }
                }
                return 0;
            }
        """)
        assert out == ["open 1", "close 1", "open 2", "close 2"]

    def test_exit_skips_disposal(self):
        code, out = run_out(RES + """
            int main() {
                using (Res* r = new Res(1)) {
                    exit(9);
                }
                return 0;
            }
        """)
        assert code == 9
        assert out == ["open 1"]  # no "close 1": exit() is immediate

    def test_function_whose_only_return_is_inside_using(self):
        # The return checker must accept this non-void function.
        assert run(RES + """
            int f() {
                using (Res* r = new Res(1)) {
                    return 4;
                }
            }
            int main() { return f(); }
        """) == 4


# ---------------------------------------------------------------------------
# Static checks
# ---------------------------------------------------------------------------

class TestStaticChecks:
    def test_primitive_value_rejected(self):
        err("""
            int main() {
                using (int x = 3) { }
                return 0;
            }
        """, "requires a pointer or a class value with dispose()")

    def test_class_value_without_dispose_rejected(self):
        err("""
            class Plain { int x; Plain(int x) { this.x = x; } }
            int main() {
                using (Plain p = Plain(1)) { }
                return 0;
            }
        """, "needs a zero-argument dispose() method")

    def test_resource_variable_is_const(self):
        err(RES + """
            int main() {
                using (Res* r = new Res(1)) {
                    r = null;
                }
                return 0;
            }
        """, "cannot assign to const 'r'")

    def test_resource_variable_scoped_to_block(self):
        err(RES + """
            int main() {
                using (Res* r = new Res(1)) { }
                delete r;
                return 0;
            }
        """, "undefined variable 'r'")

    def test_initialiser_required(self):
        with pytest.raises(ParseError):
            Parser(Lexer("int main() { using (int* p) { } return 0; }").tokenize()).parse()

    def test_using_namespace_inside_body_is_parse_error(self):
        with pytest.raises(ParseError) as exc:
            Parser(Lexer("""
                int main() {
                    using namespace math;
                    return 0;
                }
            """).tokenize()).parse()
        assert "top level" in str(exc.value)

    def test_type_mismatch_in_header(self):
        err(RES + """
            int main() {
                using (Res* r = 5) { }
                return 0;
            }
        """, "cannot initialise")


# ---------------------------------------------------------------------------
# Interactions with namespaces and generics
# ---------------------------------------------------------------------------

class TestIntegration:
    def test_namespaced_resource_class(self):
        _, out = run_out("""
            namespace fs {
                class File {
                    string path;
                    File(string path) { this.path = path; }
                    ~File() { print("closed " + this.path); }
                }
            }
            int main() {
                using (fs::File* f = new fs::File("a.txt")) {
                    print("writing");
                }
                return 0;
            }
        """)
        assert out == ["writing", "closed a.txt"]

    def test_generic_resource_class(self):
        _, out = run_out("""
            class Buffer<T> {
                T* data;
                Buffer(int n) { this.data = alloc(T, n); }
                void set(int i, T v) { this.data[i] = v; }
                T get(int i) { return this.data[i]; }
                void dispose() { print("buffer released"); free(this.data); }
            }
            int main() {
                using (Buffer<int> b = Buffer<int>(4)) {
                    b.set(0, 11);
                    print(b.get(0));
                }
                return 0;
            }
        """)
        assert out == ["11", "buffer released"]

    def test_memory_owner_in_using(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "prog.lang")
            with open(path, "w", encoding="utf-8") as f:
                f.write("""
                    import "std/memory.lang";
                    int main() {
                        int total = 0;
                        using (MemoryOwner<int> o = MemoryOwner<int>(4)) {
                            for (int i = 0; i < 4; ++i) { o.set(i, i + 1); }
                            for (int i = 0; i < 4; ++i) { total = total + o.get(i); }
                        }
                        return total;
                    }
                """)
            from glang_loader.loader import Loader
            prog = Loader().load(path)
            env = Analyser().analyse(prog)
            assert Interpreter(env).run(prog) == 10
