"""Tests for nullable types (T?) and the null-coalescing operator (??)."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from errors.errors import TypeError as GTE, ParseError

from tests.test_interpreter import run, run_out, main
from tests.test_analyser import ok, err, analyse


# ---------------------------------------------------------------------------
# Type-checker / analyser tests
# ---------------------------------------------------------------------------

class TestNullableDecl:
    def test_nullable_int_null_ok(self):
        ok("int main() { int? x = null; return 0; }")

    def test_nullable_string_null_ok(self):
        ok("int main() { string? s = null; return 0; }")

    def test_nullable_bool_null_ok(self):
        ok("int main() { bool? b = null; return 0; }")

    def test_nullable_int_value_ok(self):
        ok("int main() { int? x = 42; return 0; }")

    def test_plain_null_rejected(self):
        err("int main() { int x = null; return 0; }", "cannot initialise")

    def test_nullable_to_non_nullable_rejected(self):
        err("""
int main() {
    int? x = 42;
    int y = x;
    return 0;
}
""", "cannot initialise")

    def test_nullable_to_nullable_ok(self):
        ok("""
int main() {
    int? x = 42;
    int? y = x;
    return 0;
}
""")

    def test_nullable_pointer_rejected(self):
        with pytest.raises(ParseError):
            analyse("int main() { int*? p = null; return 0; }")

    def test_var_infers_nullable_from_null_rejected(self):
        err("int main() { var x = null; return 0; }", "cannot infer")


class TestNullCoalescing:
    def test_null_coalescing_returns_fallback_when_null(self):
        src = main("int? x = null; int y = x ?? 99; print(y); return 0;")
        code, out = run_out(src)
        assert code == 0
        assert out == ["99"]

    def test_null_coalescing_returns_value_when_non_null(self):
        src = main("int? x = 42; int y = x ?? 99; print(y); return 0;")
        code, out = run_out(src)
        assert code == 0
        assert out == ["42"]

    def test_null_coalescing_string(self):
        src = main('string? s = null; string t = s ?? "default"; print(t); return 0;')
        code, out = run_out(src)
        assert code == 0
        assert out == ["default"]

    def test_null_coalescing_non_null_string(self):
        src = main('string? s = "hello"; string t = s ?? "default"; print(t); return 0;')
        code, out = run_out(src)
        assert code == 0
        assert out == ["hello"]

    def test_null_coalescing_bool(self):
        src = main("bool? b = null; bool result = b ?? false; print(result); return 0;")
        code, out = run_out(src)
        assert code == 0
        assert out == ["false"]

    def test_coalescing_wrong_right_type_rejected(self):
        err('int main() { int? x = null; int y = x ?? "hi"; return 0; }',
            "right operand must be")

    def test_coalescing_non_nullable_left_rejected(self):
        err("int main() { int x = 5; int y = x ?? 3; return 0; }", "nullable")


class TestNullableZeroValue:
    def test_zero_value_is_null(self):
        src = """
class Box {
    int? val;
    Box() { }
}
int main() {
    Box* b = new Box();
    int result = b->val ?? -1;
    print(result);
    return 0;
}
"""
        code, out = run_out(src)
        assert code == 0
        assert out == ["-1"]


class TestNullableAssignability:
    def test_return_nullable_ok(self):
        ok("""
int? maybeInt(bool flag) {
    if (flag) { return 42; }
    return null;
}
int main() { return 0; }
""")

    def test_nullable_param_ok(self):
        ok("""
void acceptNullable(int? x) { }
int main() { acceptNullable(null); return 0; }
""")

    def test_nullable_param_with_value_ok(self):
        ok("""
void acceptNullable(int? x) { }
int main() { acceptNullable(10); return 0; }
""")
