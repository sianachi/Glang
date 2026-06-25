"""Tests for List::indexOf, Map::getOrDefault, and Option::unwrapOr/filter."""
import sys, os, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from loader.loader import Loader
from analyser.analyser import Analyser
from interpreter.interpreter import Interpreter


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


def main(body: str, preamble: str) -> str:
    return f"{preamble}\nint main() {{\n{body}\nreturn 0;\n}}"


# ---------------------------------------------------------------------------
# List<T>::indexOf
# ---------------------------------------------------------------------------

LIST_PRE = 'import "std/list.lang";'


class TestListIndexOf:
    def test_found_int(self):
        _, out = run_out(main("""\
List<int> l = List<int>();
l.add(10); l.add(20); l.add(30);
print(l.indexOf(20));
""", LIST_PRE))
        assert out == ["1"]

    def test_not_found(self):
        _, out = run_out(main("""\
List<int> l = List<int>();
l.add(1); l.add(2);
print(l.indexOf(99));
""", LIST_PRE))
        assert out == ["-1"]

    def test_first_occurrence(self):
        _, out = run_out(main("""\
List<int> l = List<int>();
l.add(5); l.add(3); l.add(5);
print(l.indexOf(5));
""", LIST_PRE))
        assert out == ["0"]

    def test_empty_list(self):
        _, out = run_out(main("""\
List<int> l = List<int>();
print(l.indexOf(1));
""", LIST_PRE))
        assert out == ["-1"]

    def test_string_list(self):
        _, out = run_out(main("""\
List<string> l = List<string>();
l.add("a"); l.add("b"); l.add("c");
print(l.indexOf("b"));
""", LIST_PRE))
        assert out == ["1"]


# ---------------------------------------------------------------------------
# Map<K,V>::getOrDefault
# ---------------------------------------------------------------------------

MAP_PRE = 'import "std/map.lang";'


class TestMapGetOrDefault:
    def test_key_present(self):
        _, out = run_out(main("""\
Map<string, int> m = Map<string, int>();
m.set("a", 1);
print(m.getOrDefault("a", -1));
""", MAP_PRE))
        assert out == ["1"]

    def test_key_absent(self):
        _, out = run_out(main("""\
Map<string, int> m = Map<string, int>();
m.set("a", 1);
print(m.getOrDefault("z", 42));
""", MAP_PRE))
        assert out == ["42"]

    def test_consistent_with_getOr(self):
        _, out = run_out(main("""\
Map<int, string> m = Map<int, string>();
m.set(1, "one");
print(m.getOr(2, "missing"));
print(m.getOrDefault(2, "missing"));
""", MAP_PRE))
        assert out == ["missing", "missing"]


# ---------------------------------------------------------------------------
# Option<T>::unwrapOr and filter
# ---------------------------------------------------------------------------

OPT_PRE = 'import "std/option.lang";'


class TestOptionUnwrapOr:
    def test_some(self):
        _, out = run_out(main("""\
Option<int> o = Option<int>();
o.setSome(7);
print(o.unwrapOr(0));
""", OPT_PRE))
        assert out == ["7"]

    def test_none(self):
        _, out = run_out(main("""\
Option<int> o = Option<int>();
print(o.unwrapOr(99));
""", OPT_PRE))
        assert out == ["99"]

    def test_equivalent_to_getOr(self):
        _, out = run_out(main("""\
Option<string> o = Option<string>();
o.setSome("hello");
print(o.getOr("default"));
print(o.unwrapOr("default"));
""", OPT_PRE))
        assert out == ["hello", "hello"]


class TestOptionFilter:
    def test_satisfies_pred(self):
        _, out = run_out(main("""\
Option<int> o = Option<int>();
o.setSome(10);
fn(int) -> bool isPos = (int x) -> bool { return x > 0; };
Option<int> r = o.filter(isPos);
print(r.isSome());
print(r.get());
""", OPT_PRE))
        assert out == ["true", "10"]

    def test_fails_pred(self):
        _, out = run_out(main("""\
Option<int> o = Option<int>();
o.setSome(-5);
fn(int) -> bool isPos = (int x) -> bool { return x > 0; };
Option<int> r = o.filter(isPos);
print(r.isNone());
""", OPT_PRE))
        assert out == ["true"]

    def test_none_stays_none(self):
        _, out = run_out(main("""\
Option<int> o = Option<int>();
fn(int) -> bool alwaysTrue = (int x) -> bool { return true; };
Option<int> r = o.filter(alwaysTrue);
print(r.isNone());
""", OPT_PRE))
        assert out == ["true"]
