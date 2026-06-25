"""End-to-end tests for LINQ-style operations via the modifier system.

Covers:
  - List<T> modifier methods: where, any, all, countWhere, first, forEach, reduce
  - Standalone generic: select<T,U>
  - Span<T> modifier methods: where, any, all, countWhere, first, forEach, reduce
  - Span cross-type free function: spanSelect<T,U>
  - string modifier methods: any, all, countWhere, first, forEach, where
  - string free function: strReduce<T>
  - List.span() bridge method
  - Method chaining
"""

import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from loader.loader import Loader
from analyser.analyser import Analyser
from interpreter.interpreter import Interpreter
from interpreter.interpreter import GlangExitException
from errors.errors import RuntimeError as GRE


LINQ = 'import "std/linq.lang";\n'


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


# ---------------------------------------------------------------------------
# where
# ---------------------------------------------------------------------------

class TestWhere:
    def test_filters_matching_elements(self):
        _, out = run_out(LINQ + """
        int main() {
            List<int> nums = List<int>();
            nums.add(1); nums.add(2); nums.add(3); nums.add(4); nums.add(5);
            List<int> evens = nums.where((int x) -> bool { return x % 2 == 0; });
            print(evens.length());
            print(evens.get(0));
            print(evens.get(1));
            return 0;
        }
        """)
        assert out == ["2", "2", "4"]

    def test_where_all_match(self):
        _, out = run_out(LINQ + """
        int main() {
            List<int> nums = List<int>();
            nums.add(2); nums.add(4); nums.add(6);
            List<int> evens = nums.where((int x) -> bool { return x % 2 == 0; });
            print(evens.length());
            return 0;
        }
        """)
        assert out == ["3"]

    def test_where_none_match(self):
        _, out = run_out(LINQ + """
        int main() {
            List<int> nums = List<int>();
            nums.add(1); nums.add(3); nums.add(5);
            List<int> evens = nums.where((int x) -> bool { return x % 2 == 0; });
            print(evens.length());
            return 0;
        }
        """)
        assert out == ["0"]

    def test_where_on_empty_list(self):
        _, out = run_out(LINQ + """
        int main() {
            List<int> nums = List<int>();
            List<int> result = nums.where((int x) -> bool { return x > 0; });
            print(result.length());
            return 0;
        }
        """)
        assert out == ["0"]

    def test_where_preserves_order(self):
        _, out = run_out(LINQ + """
        int main() {
            List<int> nums = List<int>();
            nums.add(10); nums.add(3); nums.add(8); nums.add(1); nums.add(6);
            List<int> big = nums.where((int x) -> bool { return x > 5; });
            print(big.get(0));
            print(big.get(1));
            print(big.get(2));
            return 0;
        }
        """)
        assert out == ["10", "8", "6"]


# ---------------------------------------------------------------------------
# any
# ---------------------------------------------------------------------------

class TestAny:
    def test_any_true(self):
        _, out = run_out(LINQ + """
        int main() {
            List<int> nums = List<int>();
            nums.add(1); nums.add(2); nums.add(3);
            bool result = nums.any((int x) -> bool { return x > 2; });
            print(result);
            return 0;
        }
        """)
        assert out == ["true"]

    def test_any_false(self):
        _, out = run_out(LINQ + """
        int main() {
            List<int> nums = List<int>();
            nums.add(1); nums.add(2); nums.add(3);
            bool result = nums.any((int x) -> bool { return x > 10; });
            print(result);
            return 0;
        }
        """)
        assert out == ["false"]

    def test_any_on_empty_list_is_false(self):
        _, out = run_out(LINQ + """
        int main() {
            List<int> nums = List<int>();
            bool result = nums.any((int x) -> bool { return true; });
            print(result);
            return 0;
        }
        """)
        assert out == ["false"]

    def test_any_short_circuits(self):
        _, out = run_out(LINQ + """
        int main() {
            List<int> nums = List<int>();
            nums.add(5); nums.add(3); nums.add(1);
            bool result = nums.any((int x) -> bool { return x == 5; });
            print(result);
            return 0;
        }
        """)
        assert out == ["true"]


# ---------------------------------------------------------------------------
# all
# ---------------------------------------------------------------------------

class TestAll:
    def test_all_true(self):
        _, out = run_out(LINQ + """
        int main() {
            List<int> nums = List<int>();
            nums.add(2); nums.add(4); nums.add(6);
            bool result = nums.all((int x) -> bool { return x % 2 == 0; });
            print(result);
            return 0;
        }
        """)
        assert out == ["true"]

    def test_all_false(self):
        _, out = run_out(LINQ + """
        int main() {
            List<int> nums = List<int>();
            nums.add(2); nums.add(3); nums.add(6);
            bool result = nums.all((int x) -> bool { return x % 2 == 0; });
            print(result);
            return 0;
        }
        """)
        assert out == ["false"]

    def test_all_on_empty_list_is_true(self):
        _, out = run_out(LINQ + """
        int main() {
            List<int> nums = List<int>();
            bool result = nums.all((int x) -> bool { return false; });
            print(result);
            return 0;
        }
        """)
        assert out == ["true"]


# ---------------------------------------------------------------------------
# countWhere
# ---------------------------------------------------------------------------

class TestCountWhere:
    def test_count_some(self):
        _, out = run_out(LINQ + """
        int main() {
            List<int> nums = List<int>();
            nums.add(1); nums.add(2); nums.add(3); nums.add(4); nums.add(5);
            int n = nums.countWhere((int x) -> bool { return x % 2 == 0; });
            print(n);
            return 0;
        }
        """)
        assert out == ["2"]

    def test_count_none(self):
        _, out = run_out(LINQ + """
        int main() {
            List<int> nums = List<int>();
            nums.add(1); nums.add(3); nums.add(5);
            int n = nums.countWhere((int x) -> bool { return x % 2 == 0; });
            print(n);
            return 0;
        }
        """)
        assert out == ["0"]

    def test_count_all(self):
        _, out = run_out(LINQ + """
        int main() {
            List<int> nums = List<int>();
            nums.add(10); nums.add(20); nums.add(30);
            int n = nums.countWhere((int x) -> bool { return x > 5; });
            print(n);
            return 0;
        }
        """)
        assert out == ["3"]

    def test_count_empty_list(self):
        _, out = run_out(LINQ + """
        int main() {
            List<int> nums = List<int>();
            int n = nums.countWhere((int x) -> bool { return true; });
            print(n);
            return 0;
        }
        """)
        assert out == ["0"]


# ---------------------------------------------------------------------------
# first
# ---------------------------------------------------------------------------

class TestFirst:
    def test_first_returns_matching_element(self):
        _, out = run_out(LINQ + """
        int main() {
            List<int> nums = List<int>();
            nums.add(1); nums.add(2); nums.add(3); nums.add(4);
            int val = nums.first((int x) -> bool { return x > 2; });
            print(val);
            return 0;
        }
        """)
        assert out == ["3"]

    def test_first_returns_earliest_match(self):
        _, out = run_out(LINQ + """
        int main() {
            List<int> nums = List<int>();
            nums.add(5); nums.add(3); nums.add(8);
            int val = nums.first((int x) -> bool { return x > 4; });
            print(val);
            return 0;
        }
        """)
        assert out == ["5"]

    def test_first_exits_when_no_match(self):
        code = run(LINQ + """
        int main() {
            List<int> nums = List<int>();
            nums.add(1); nums.add(2); nums.add(3);
            int val = nums.first((int x) -> bool { return x > 100; });
            return 0;
        }
        """)
        assert code == 1

    def test_first_exits_on_empty_list(self):
        code = run(LINQ + """
        int main() {
            List<int> nums = List<int>();
            int val = nums.first((int x) -> bool { return true; });
            return 0;
        }
        """)
        assert code == 1


# ---------------------------------------------------------------------------
# forEach
# ---------------------------------------------------------------------------

class TestForEach:
    def test_foreach_applies_action_to_all(self):
        _, out = run_out(LINQ + """
        int main() {
            List<int> nums = List<int>();
            nums.add(10); nums.add(20); nums.add(30);
            nums.forEach((int x) -> void { print(x); });
            return 0;
        }
        """)
        assert out == ["10", "20", "30"]

    def test_foreach_on_empty_list_does_nothing(self):
        _, out = run_out(LINQ + """
        int main() {
            List<int> nums = List<int>();
            nums.forEach((int x) -> void { print(x); });
            print(99);
            return 0;
        }
        """)
        assert out == ["99"]

    def test_foreach_with_closure_capture(self):
        _, out = run_out(LINQ + """
        int main() {
            List<int> nums = List<int>();
            nums.add(1); nums.add(2); nums.add(3);
            int factor = 3;
            nums.forEach((int x) -> void { print(x * factor); });
            return 0;
        }
        """)
        assert out == ["3", "6", "9"]


# ---------------------------------------------------------------------------
# reduce
# ---------------------------------------------------------------------------

class TestReduce:
    def test_reduce_sum(self):
        _, out = run_out(LINQ + """
        int main() {
            List<int> nums = List<int>();
            nums.add(1); nums.add(2); nums.add(3); nums.add(4);
            int total = nums.reduce((int acc, int x) -> int { return acc + x; }, 0);
            print(total);
            return 0;
        }
        """)
        assert out == ["10"]

    def test_reduce_product(self):
        _, out = run_out(LINQ + """
        int main() {
            List<int> nums = List<int>();
            nums.add(2); nums.add(3); nums.add(4);
            int product = nums.reduce((int acc, int x) -> int { return acc * x; }, 1);
            print(product);
            return 0;
        }
        """)
        assert out == ["24"]

    def test_reduce_empty_returns_initial(self):
        _, out = run_out(LINQ + """
        int main() {
            List<int> nums = List<int>();
            int result = nums.reduce((int acc, int x) -> int { return acc + x; }, 42);
            print(result);
            return 0;
        }
        """)
        assert out == ["42"]

    def test_reduce_max(self):
        _, out = run_out(LINQ + """
        int main() {
            List<int> nums = List<int>();
            nums.add(3); nums.add(7); nums.add(1); nums.add(5);
            int m = nums.reduce((int acc, int x) -> int {
                if (x > acc) { return x; }
                return acc;
            }, 0);
            print(m);
            return 0;
        }
        """)
        assert out == ["7"]


# ---------------------------------------------------------------------------
# select (standalone generic function)
# ---------------------------------------------------------------------------

class TestSelect:
    def test_select_int_to_bool(self):
        _, out = run_out(LINQ + """
        int main() {
            List<int> nums = List<int>();
            nums.add(1); nums.add(2); nums.add(3);
            List<bool> flags = select<int, bool>(nums, (int x) -> bool { return x % 2 == 0; });
            print(flags.length());
            print(flags.get(0));
            print(flags.get(1));
            print(flags.get(2));
            return 0;
        }
        """)
        assert out == ["3", "false", "true", "false"]

    def test_select_doubles_each(self):
        _, out = run_out(LINQ + """
        int main() {
            List<int> nums = List<int>();
            nums.add(5); nums.add(10); nums.add(15);
            List<int> doubled = select<int, int>(nums, (int x) -> int { return x * 2; });
            print(doubled.get(0));
            print(doubled.get(1));
            print(doubled.get(2));
            return 0;
        }
        """)
        assert out == ["10", "20", "30"]

    def test_select_empty_list(self):
        _, out = run_out(LINQ + """
        int main() {
            List<int> nums = List<int>();
            List<bool> flags = select<int, bool>(nums, (int x) -> bool { return true; });
            print(flags.length());
            return 0;
        }
        """)
        assert out == ["0"]


# ---------------------------------------------------------------------------
# Method chaining
# ---------------------------------------------------------------------------

class TestChaining:
    def test_where_then_countWhere(self):
        _, out = run_out(LINQ + """
        int main() {
            List<int> nums = List<int>();
            for (int i = 1; i <= 10; ++i) { nums.add(i); }
            int n = nums.where((int x) -> bool { return x % 2 == 0; })
                        .countWhere((int x) -> bool { return x > 4; });
            print(n);
            return 0;
        }
        """)
        assert out == ["3"]

    def test_where_then_any(self):
        _, out = run_out(LINQ + """
        int main() {
            List<int> nums = List<int>();
            nums.add(1); nums.add(2); nums.add(3); nums.add(4);
            bool result = nums.where((int x) -> bool { return x % 2 == 0; })
                             .any((int x) -> bool { return x > 3; });
            print(result);
            return 0;
        }
        """)
        assert out == ["true"]

    def test_where_then_reduce(self):
        _, out = run_out(LINQ + """
        int main() {
            List<int> nums = List<int>();
            for (int i = 1; i <= 5; ++i) { nums.add(i); }
            int sum = nums.where((int x) -> bool { return x % 2 != 0; })
                          .reduce((int acc, int x) -> int { return acc + x; }, 0);
            print(sum);
            return 0;
        }
        """)
        assert out == ["9"]

    def test_where_then_forEach(self):
        _, out = run_out(LINQ + """
        int main() {
            List<int> nums = List<int>();
            for (int i = 1; i <= 6; ++i) { nums.add(i); }
            nums.where((int x) -> bool { return x % 3 == 0; })
                .forEach((int x) -> void { print(x); });
            return 0;
        }
        """)
        assert out == ["3", "6"]


# ---------------------------------------------------------------------------
# List.span() bridge
# ---------------------------------------------------------------------------

class TestListSpan:
    def test_span_length_matches_list(self):
        _, out = run_out(LINQ + """
        int main() {
            List<int> nums = List<int>();
            nums.add(10); nums.add(20); nums.add(30);
            Span<int> sp = nums.span();
            print(sp.length());
            return 0;
        }
        """)
        assert out == ["3"]

    def test_span_get_matches_list_get(self):
        _, out = run_out(LINQ + """
        int main() {
            List<int> nums = List<int>();
            nums.add(7); nums.add(14); nums.add(21);
            Span<int> sp = nums.span();
            print(sp.get(0));
            print(sp.get(2));
            return 0;
        }
        """)
        assert out == ["7", "21"]

    def test_span_on_empty_list(self):
        _, out = run_out(LINQ + """
        int main() {
            List<int> nums = List<int>();
            Span<int> sp = nums.span();
            print(sp.length());
            print(sp.isEmpty());
            return 0;
        }
        """)
        assert out == ["0", "true"]


# ---------------------------------------------------------------------------
# Span.where (modifier method)
# ---------------------------------------------------------------------------

class TestSpanWhere:
    def test_filters_via_list_span(self):
        _, out = run_out(LINQ + """
        int main() {
            List<int> nums = List<int>();
            for (int i = 1; i <= 6; ++i) { nums.add(i); }
            List<int> evens = nums.span().where((int x) -> bool { return x % 2 == 0; });
            print(evens.length());
            print(evens.get(0));
            print(evens.get(1));
            print(evens.get(2));
            return 0;
        }
        """)
        assert out == ["3", "2", "4", "6"]

    def test_span_where_empty(self):
        _, out = run_out(LINQ + """
        int main() {
            List<int> nums = List<int>();
            Span<int> sp = nums.span();
            List<int> result = sp.where((int x) -> bool { return true; });
            print(result.length());
            return 0;
        }
        """)
        assert out == ["0"]

    def test_span_where_from_raw_pointer(self):
        _, out = run_out(LINQ + """
        int main() {
            int* arr = alloc(int, 5);
            arr[0] = 10; arr[1] = 3; arr[2] = 8; arr[3] = 1; arr[4] = 6;
            Span<int> sp = Span<int>(arr, 0, 5);
            List<int> big = sp.where((int x) -> bool { return x > 5; });
            print(big.length());
            free(arr);
            return 0;
        }
        """)
        assert out == ["3"]


# ---------------------------------------------------------------------------
# Span.any / Span.all / Span.countWhere (modifier methods)
# ---------------------------------------------------------------------------

class TestSpanQueryOps:
    def test_span_any_true(self):
        _, out = run_out(LINQ + """
        int main() {
            List<int> nums = List<int>();
            nums.add(1); nums.add(2); nums.add(3);
            bool result = nums.span().any((int x) -> bool { return x > 2; });
            print(result);
            return 0;
        }
        """)
        assert out == ["true"]

    def test_span_any_false(self):
        _, out = run_out(LINQ + """
        int main() {
            List<int> nums = List<int>();
            nums.add(1); nums.add(2);
            bool result = nums.span().any((int x) -> bool { return x > 10; });
            print(result);
            return 0;
        }
        """)
        assert out == ["false"]

    def test_span_all_true(self):
        _, out = run_out(LINQ + """
        int main() {
            List<int> nums = List<int>();
            nums.add(2); nums.add(4); nums.add(6);
            bool result = nums.span().all((int x) -> bool { return x % 2 == 0; });
            print(result);
            return 0;
        }
        """)
        assert out == ["true"]

    def test_span_all_empty_is_true(self):
        _, out = run_out(LINQ + """
        int main() {
            List<int> nums = List<int>();
            bool result = nums.span().all((int x) -> bool { return false; });
            print(result);
            return 0;
        }
        """)
        assert out == ["true"]

    def test_span_countWhere(self):
        _, out = run_out(LINQ + """
        int main() {
            List<int> nums = List<int>();
            for (int i = 1; i <= 5; ++i) { nums.add(i); }
            int n = nums.span().countWhere((int x) -> bool { return x % 2 != 0; });
            print(n);
            return 0;
        }
        """)
        assert out == ["3"]


# ---------------------------------------------------------------------------
# Span.first / Span.forEach / Span.reduce (modifier methods)
# ---------------------------------------------------------------------------

class TestSpanIterOps:
    def test_span_first(self):
        _, out = run_out(LINQ + """
        int main() {
            List<int> nums = List<int>();
            nums.add(1); nums.add(4); nums.add(7);
            int val = nums.span().first((int x) -> bool { return x > 3; });
            print(val);
            return 0;
        }
        """)
        assert out == ["4"]

    def test_span_first_not_found_exits(self):
        code = run(LINQ + """
        int main() {
            List<int> nums = List<int>();
            nums.add(1);
            int val = nums.span().first((int x) -> bool { return x > 100; });
            return 0;
        }
        """)
        assert code == 1

    def test_span_forEach(self):
        _, out = run_out(LINQ + """
        int main() {
            List<int> nums = List<int>();
            nums.add(5); nums.add(10);
            nums.span().forEach((int x) -> void { print(x * 2); });
            return 0;
        }
        """)
        assert out == ["10", "20"]

    def test_span_reduce_sum(self):
        _, out = run_out(LINQ + """
        int main() {
            List<int> nums = List<int>();
            nums.add(3); nums.add(4); nums.add(5);
            int s = nums.span().reduce((int acc, int x) -> int { return acc + x; }, 0);
            print(s);
            return 0;
        }
        """)
        assert out == ["12"]

    def test_span_reduce_empty(self):
        _, out = run_out(LINQ + """
        int main() {
            List<int> nums = List<int>();
            int s = nums.span().reduce((int acc, int x) -> int { return acc + x; }, 99);
            print(s);
            return 0;
        }
        """)
        assert out == ["99"]


# ---------------------------------------------------------------------------
# spanSelect<T,U> (free function)
# ---------------------------------------------------------------------------

class TestSpanSelect:
    def test_span_select_int_to_bool(self):
        _, out = run_out(LINQ + """
        int main() {
            List<int> nums = List<int>();
            nums.add(1); nums.add(2); nums.add(3);
            List<bool> flags = spanSelect<int, bool>(nums.span(), (int x) -> bool { return x % 2 == 0; });
            print(flags.length());
            print(flags.get(0));
            print(flags.get(1));
            print(flags.get(2));
            return 0;
        }
        """)
        assert out == ["3", "false", "true", "false"]

    def test_span_select_double(self):
        _, out = run_out(LINQ + """
        int main() {
            List<int> nums = List<int>();
            nums.add(4); nums.add(5);
            List<int> doubled = spanSelect<int, int>(nums.span(), (int x) -> int { return x * 2; });
            print(doubled.get(0));
            print(doubled.get(1));
            return 0;
        }
        """)
        assert out == ["8", "10"]


# ---------------------------------------------------------------------------
# string modifier methods
# ---------------------------------------------------------------------------

class TestStringLinq:
    def test_str_any_true(self):
        _, out = run_out(LINQ + """
        int main() {
            bool result = "hello".any((char c) -> bool { return c == 'e'; });
            print(result);
            return 0;
        }
        """)
        assert out == ["true"]

    def test_str_any_false(self):
        _, out = run_out(LINQ + """
        int main() {
            bool result = "hello".any((char c) -> bool { return c == 'z'; });
            print(result);
            return 0;
        }
        """)
        assert out == ["false"]

    def test_str_any_empty_string(self):
        _, out = run_out(LINQ + """
        int main() {
            bool result = "".any((char c) -> bool { return true; });
            print(result);
            return 0;
        }
        """)
        assert out == ["false"]

    def test_str_all_true(self):
        _, out = run_out(LINQ + """
        int main() {
            bool result = "aaa".all((char c) -> bool { return c == 'a'; });
            print(result);
            return 0;
        }
        """)
        assert out == ["true"]

    def test_str_all_false(self):
        _, out = run_out(LINQ + """
        int main() {
            bool result = "abc".all((char c) -> bool { return c == 'a'; });
            print(result);
            return 0;
        }
        """)
        assert out == ["false"]

    def test_str_all_empty_is_true(self):
        _, out = run_out(LINQ + """
        int main() {
            bool result = "".all((char c) -> bool { return false; });
            print(result);
            return 0;
        }
        """)
        assert out == ["true"]

    def test_str_count_where(self):
        _, out = run_out(LINQ + """
        int main() {
            int n = "banana".countWhere((char c) -> bool { return c == 'a'; });
            print(n);
            return 0;
        }
        """)
        assert out == ["3"]

    def test_str_count_where_none(self):
        _, out = run_out(LINQ + """
        int main() {
            int n = "hello".countWhere((char c) -> bool { return c == 'z'; });
            print(n);
            return 0;
        }
        """)
        assert out == ["0"]

    def test_str_first(self):
        _, out = run_out(LINQ + """
        int main() {
            char c = "hello world".first((char x) -> bool { return x == 'o'; });
            print(c);
            return 0;
        }
        """)
        assert out == ["o"]

    def test_str_first_not_found_exits(self):
        code = run(LINQ + """
        int main() {
            char c = "hello".first((char x) -> bool { return x == 'z'; });
            return 0;
        }
        """)
        assert code == 1

    def test_str_for_each(self):
        _, out = run_out(LINQ + """
        int main() {
            "abc".forEach((char c) -> void { print(c); });
            return 0;
        }
        """)
        assert out == ["a", "b", "c"]

    def test_str_where_returns_list_of_matching_chars(self):
        _, out = run_out(LINQ + """
        int main() {
            List<char> vowels = "glang".where((char c) -> bool {
                return c == 'a' || c == 'e' || c == 'i' || c == 'o' || c == 'u';
            });
            print(vowels.length());
            print(vowels.get(0));
            return 0;
        }
        """)
        assert out == ["1", "a"]

    def test_str_reduce_count_chars(self):
        _, out = run_out(LINQ + """
        int main() {
            int n = strReduce<int>("hello", (int acc, char c) -> int { return acc + 1; }, 0);
            print(n);
            return 0;
        }
        """)
        assert out == ["5"]

    def test_str_reduce_sum_digit_values(self):
        _, out = run_out(LINQ + """
        int main() {
            // Count occurrences of 'l'
            int n = strReduce<int>("hello world", (int acc, char c) -> int {
                if (c == 'l') { return acc + 1; }
                return acc;
            }, 0);
            print(n);
            return 0;
        }
        """)
        assert out == ["3"]

    def test_str_variable_any(self):
        _, out = run_out(LINQ + """
        int main() {
            string s = "world";
            bool result = s.any((char c) -> bool { return c == 'r'; });
            print(result);
            return 0;
        }
        """)
        assert out == ["true"]
