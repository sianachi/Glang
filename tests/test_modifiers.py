"""Tests for the object modifier feature.

Covers:
  - Modifier on a user-defined class (instance method extension)
  - Modifier on a primitive type (string)
  - Generic modifier instantiation (modifier<T> for List<T>)
  - Modifier methods participate in chaining
  - Error: calling a non-existent modifier method
  - Error: duplicate modifier method for the same type
  - Modifier co-exists with class own methods (no shadowing)
  - Modifier `this` refers to the receiver correctly
"""

import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from loader.loader import Loader
from analyser.analyser import Analyser
from interpreter.interpreter import Interpreter
from errors.errors import TypeError as GTE
from errors.errors import RuntimeError as GRE


def run_out(src: str):
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "prog.lang")
        with open(path, "w", encoding="utf-8") as f:
            f.write(src)
        program = Loader().load(path)
        env = Analyser().analyse(program)
        interp = Interpreter(env)
        code = interp.run(program)
        return code, interp.output


def run(src: str) -> int:
    code, _ = run_out(src)
    return code


def ok(src: str):
    run(src)


def err(src: str, fragment: str):
    with pytest.raises((GTE, GRE)) as exc_info:
        run_out(src)
    assert fragment in str(exc_info.value), str(exc_info.value)


# ---------------------------------------------------------------------------
# Modifier on a user-defined class
# ---------------------------------------------------------------------------

class TestUserDefinedClassModifier:
    def test_basic_modifier_method_called(self):
        _, out = run_out("""
        class Counter {
            int value;
            Counter() { this.value = 0; }
            void inc() { this.value = this.value + 1; }
            int get() { return this.value; }
        }

        modifier for Counter {
            int doubled() { return this.get() * 2; }
        }

        int main() {
            Counter c = Counter();
            c.inc(); c.inc(); c.inc();
            print(c.doubled());
            return 0;
        }
        """)
        assert out == ["6"]

    def test_modifier_sees_class_fields_via_this(self):
        _, out = run_out("""
        class Point {
            int x;
            int y;
            Point(int x, int y) { this.x = x; this.y = y; }
        }

        modifier for Point {
            int sumCoords() { return this.x + this.y; }
        }

        int main() {
            Point p = Point(3, 7);
            print(p.sumCoords());
            return 0;
        }
        """)
        assert out == ["10"]

    def test_modifier_and_own_methods_coexist(self):
        _, out = run_out("""
        class Box {
            int v;
            Box(int v) { this.v = v; }
            int get() { return this.v; }
        }

        modifier for Box {
            int triple() { return this.get() * 3; }
        }

        int main() {
            Box b = Box(4);
            print(b.get());
            print(b.triple());
            return 0;
        }
        """)
        assert out == ["4", "12"]

    def test_modifier_with_parameter(self):
        _, out = run_out("""
        class Acc {
            int n;
            Acc() { this.n = 0; }
            void add(int x) { this.n = this.n + x; }
            int get() { return this.n; }
        }

        modifier for Acc {
            void addMany(int a, int b, int c) {
                this.add(a);
                this.add(b);
                this.add(c);
            }
        }

        int main() {
            Acc a = Acc();
            a.addMany(1, 2, 3);
            print(a.get());
            return 0;
        }
        """)
        assert out == ["6"]

    def test_modifier_returns_new_object(self):
        _, out = run_out("""
        class Pair {
            int a;
            int b;
            Pair(int a, int b) { this.a = a; this.b = b; }
        }

        modifier for Pair {
            Pair swapped() { return Pair(this.b, this.a); }
        }

        int main() {
            Pair p = Pair(10, 20);
            Pair q = p.swapped();
            print(q.a);
            print(q.b);
            return 0;
        }
        """)
        assert out == ["20", "10"]


# ---------------------------------------------------------------------------
# Generic modifier instantiation
# ---------------------------------------------------------------------------

class TestGenericModifier:
    def test_generic_modifier_on_custom_class(self):
        _, out = run_out("""
        class Wrap<T> {
            T val;
            Wrap(T v) { this.val = v; }
            T get() { return this.val; }
        }

        modifier<T> for Wrap<T> {
            bool isEqual(T other) { return this.get() == other; }
        }

        int main() {
            Wrap<int> w = Wrap<int>(42);
            print(w.isEqual(42));
            print(w.isEqual(99));
            return 0;
        }
        """)
        assert out == ["true", "false"]

    def test_generic_modifier_multiple_instantiations(self):
        _, out = run_out("""
        class Box<T> {
            T v;
            Box(T v) { this.v = v; }
            T get() { return this.v; }
        }

        modifier<T> for Box<T> {
            void printVal() { print(this.get()); }
        }

        int main() {
            Box<int> bi = Box<int>(7);
            Box<bool> bb = Box<bool>(true);
            bi.printVal();
            bb.printVal();
            return 0;
        }
        """)
        assert out == ["7", "true"]


# ---------------------------------------------------------------------------
# String modifier (primitive target)
# ---------------------------------------------------------------------------

class TestStringModifier:
    def test_string_modifier_literal(self):
        _, out = run_out("""
        modifier for string {
            int size() { return len(this); }
        }

        int main() {
            print("hello".size());
            return 0;
        }
        """)
        assert out == ["5"]

    def test_string_modifier_variable(self):
        _, out = run_out("""
        modifier for string {
            bool startsWith(char c) { return len(this) > 0 && this[0] == c; }
        }

        int main() {
            string s = "glang";
            print(s.startsWith('g'));
            print(s.startsWith('z'));
            return 0;
        }
        """)
        assert out == ["true", "false"]

    def test_string_modifier_foreach(self):
        _, out = run_out("""
        modifier for string {
            void each(fn(char) -> void action) {
                for (int i = 0; i < len(this); ++i) {
                    action(this[i]);
                }
            }
        }

        int main() {
            "ab".each((char c) -> void { print(c); });
            return 0;
        }
        """)
        assert out == ["a", "b"]


# ---------------------------------------------------------------------------
# Error cases
# ---------------------------------------------------------------------------

class TestModifierErrors:
    def test_unknown_modifier_method_raises(self):
        err("""
        class Foo { Foo() {} }

        modifier for Foo {
            int bar() { return 1; }
        }

        int main() {
            Foo f = Foo();
            f.baz();
            return 0;
        }
        """, "baz")

    def test_duplicate_modifier_method_raises(self):
        err("""
        class Foo { Foo() {} }

        modifier for Foo {
            int bar() { return 1; }
            int bar() { return 2; }
        }

        int main() { return 0; }
        """, "bar")

    def test_modifier_method_wrong_arg_count_raises(self):
        err("""
        class Foo {
            int v;
            Foo(int v) { this.v = v; }
        }

        modifier for Foo {
            int add(int x) { return this.v + x; }
        }

        int main() {
            Foo f = Foo(1);
            f.add(1, 2);
            return 0;
        }
        """, "argument")


# ---------------------------------------------------------------------------
# Modifier chaining
# ---------------------------------------------------------------------------

class TestModifierChaining:
    def test_modifier_result_chained_with_another_modifier(self):
        _, out = run_out("""
        import "std/linq.lang";

        int main() {
            List<int> nums = List<int>();
            for (int i = 1; i <= 6; ++i) { nums.add(i); }
            // where returns List<int> which also has the modifier methods
            int n = nums.where((int x) -> bool { return x % 2 == 0; })
                        .countWhere((int x) -> bool { return x > 3; });
            print(n);
            return 0;
        }
        """)
        assert out == ["2"]
