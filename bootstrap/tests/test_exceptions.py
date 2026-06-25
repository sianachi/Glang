"""Tests for throw / try / catch with object-based exceptions."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from errors.errors import TypeError as GTE, ParseError

from tests.test_interpreter import run, run_out, main
from tests.test_analyser import ok, err


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

EXCEPTION_CLASSES = """
class IOException extends Exception {
    IOException(string msg) : super(msg) { }
}
class NetworkException extends IOException {
    NetworkException(string msg) : super(msg) { }
}
"""


# ---------------------------------------------------------------------------
# Type-checker / analyser tests
# ---------------------------------------------------------------------------

class TestThrowAnalyser:
    def test_throw_exception_ok(self):
        ok("""
int main() { throw new Exception("oops"); }
""")

    def test_throw_subclass_ok(self):
        ok(EXCEPTION_CLASSES + """
int main() { throw new IOException("not found"); }
""")

    def test_throw_non_exception_class_rejected(self):
        err("""
class Foo { Foo() { } }
int main() { throw new Foo(); return 0; }
""", "does not extend Exception")

    def test_throw_string_rejected(self):
        err('int main() { throw "oops"; return 0; }', "pointer to an Exception")

    def test_throw_int_rejected(self):
        err("int main() { throw 42; return 0; }", "pointer to an Exception")

    def test_throw_satisfies_return(self):
        ok('int foo() { throw new Exception("e"); }')

    def test_throw_in_branch_satisfies(self):
        ok("""
int foo(bool b) {
    if (b) { return 1; }
    throw new Exception("no");
}
int main() { return 0; }
""")


class TestTryCatchAnalyser:
    def test_try_catch_exception_ok(self):
        ok("""
int main() {
    try { } catch (Exception* e) { }
    return 0;
}
""")

    def test_catch_var_is_pointer(self):
        ok("""
int main() {
    try { throw new Exception("msg"); }
    catch (Exception* e) { print(e->message); }
    return 0;
}
""")

    def test_multiple_catch_clauses_ok(self):
        ok(EXCEPTION_CLASSES + """
int main() {
    try { throw new IOException("x"); }
    catch (IOException* e) { }
    catch (Exception* e) { }
    return 0;
}
""")

    def test_catch_non_exception_rejected(self):
        err("""
class Foo { Foo() { } }
int main() {
    try { } catch (Foo* e) { }
    return 0;
}
""", "does not extend Exception")

    def test_catch_non_pointer_rejected(self):
        err("""
int main() {
    try { } catch (int e) { }
    return 0;
}
""", "pointer to an Exception")

    def test_try_catch_both_return_satisfies(self):
        ok("""
int foo() {
    try { return 1; } catch (Exception* e) { return 2; }
}
int main() { return 0; }
""")

    def test_try_only_return_not_enough(self):
        err("""
int foo() {
    try { return 1; } catch (Exception* e) { }
}
int main() { return 0; }
""", "not all code paths")

    def test_catch_only_return_not_enough(self):
        err("""
int foo() {
    try { } catch (Exception* e) { return 2; }
}
int main() { return 0; }
""", "not all code paths")

    def test_no_catch_rejected(self):
        with pytest.raises(ParseError):
            from tests.test_analyser import analyse
            analyse("int main() { try { } return 0; }")


# ---------------------------------------------------------------------------
# Interpreter tests
# ---------------------------------------------------------------------------

class TestThrowInterpreter:
    def test_unhandled_throw_exits_1(self):
        src = 'int main() { throw new Exception("boom"); }'
        assert run(src) == 1

    def test_message_accessible_in_catch(self):
        src = """
int main() {
    try { throw new Exception("hello"); }
    catch (Exception* e) { print(e->message); }
    return 0;
}
"""
        code, out = run_out(src)
        assert code == 0
        assert out == ["hello"]

    def test_throw_propagates_through_function(self):
        src = """
void inner() { throw new Exception("from inner"); }
int main() {
    try { inner(); }
    catch (Exception* e) { print(e->message); }
    return 0;
}
"""
        code, out = run_out(src)
        assert code == 0
        assert out == ["from inner"]

    def test_throw_propagates_past_loop(self):
        src = """
void loopy() {
    int i = 0;
    while (i < 10) {
        i = i + 1;
        if (i == 5) { throw new Exception("stop"); }
    }
}
int main() {
    try { loopy(); }
    catch (Exception* e) { print(e->message); }
    return 0;
}
"""
        code, out = run_out(src)
        assert code == 0
        assert out == ["stop"]


class TestTryCatchInterpreter:
    def test_no_throw_catch_not_entered(self):
        src = main("""
try { print("ok"); }
catch (Exception* e) { print("bad"); }
return 0;
""")
        code, out = run_out(src)
        assert code == 0
        assert out == ["ok"]

    def test_execution_continues_after_catch(self):
        src = main("""
try { throw new Exception("x"); }
catch (Exception* e) { }
print("after");
return 0;
""")
        code, out = run_out(src)
        assert code == 0
        assert out == ["after"]

    def test_nested_try_catches_inner(self):
        src = main("""
try {
    try { throw new Exception("inner"); }
    catch (Exception* e) { print(e->message); }
} catch (Exception* e) {
    print("outer");
}
return 0;
""")
        code, out = run_out(src)
        assert code == 0
        assert out == ["inner"]

    def test_rethrow_reaches_outer_catch(self):
        src = main("""
try {
    try { throw new Exception("msg"); }
    catch (Exception* e) { throw e; }
} catch (Exception* e) {
    print(e->message);
}
return 0;
""")
        code, out = run_out(src)
        assert code == 0
        assert out == ["msg"]

    def test_subclass_caught_by_superclass_handler(self):
        src = EXCEPTION_CLASSES + """
int main() {
    try { throw new IOException("io error"); }
    catch (Exception* e) { print(e->message); }
    return 0;
}
"""
        code, out = run_out(src)
        assert code == 0
        assert out == ["io error"]

    def test_subclass_caught_by_exact_handler(self):
        src = EXCEPTION_CLASSES + """
int main() {
    try { throw new IOException("io"); }
    catch (IOException* e) { print(e->message); }
    catch (Exception* e) { print("wrong"); }
    return 0;
}
"""
        code, out = run_out(src)
        assert code == 0
        assert out == ["io"]

    def test_superclass_not_caught_by_subclass_handler(self):
        src = EXCEPTION_CLASSES + """
int main() {
    try {
        try { throw new Exception("base"); }
        catch (IOException* e) { print("io"); }
    } catch (Exception* e) {
        print(e->message);
    }
    return 0;
}
"""
        code, out = run_out(src)
        assert code == 0
        assert out == ["base"]

    def test_multiple_catches_first_match_wins(self):
        src = EXCEPTION_CLASSES + """
int main() {
    try { throw new IOException("x"); }
    catch (IOException* e) { print("io"); }
    catch (Exception* e) { print("base"); }
    return 0;
}
"""
        code, out = run_out(src)
        assert code == 0
        assert out == ["io"]

    def test_deep_subclass_caught_by_grandparent(self):
        src = EXCEPTION_CLASSES + """
int main() {
    try { throw new NetworkException("net"); }
    catch (Exception* e) { print(e->message); }
    return 0;
}
"""
        code, out = run_out(src)
        assert code == 0
        assert out == ["net"]

    def test_try_without_throw_returns_normally(self):
        src = """
int safe() {
    try { return 42; } catch (Exception* e) { return -1; }
}
int main() { print(safe()); return 0; }
"""
        code, out = run_out(src)
        assert code == 0
        assert out == ["42"]

    def test_catch_after_throw_in_function(self):
        src = """
int riskyOp(bool fail) {
    if (fail) { throw new Exception("failed"); }
    return 1;
}
int main() {
    int result = 0;
    try { result = riskyOp(true); }
    catch (Exception* e) { result = -1; }
    print(result);
    return 0;
}
"""
        code, out = run_out(src)
        assert code == 0
        assert out == ["-1"]
