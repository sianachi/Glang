"""Tests for Set<T> (std/set.lang)."""
import sys, os, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from loader.loader import Loader
from analyser.analyser import Analyser
from interpreter.interpreter import Interpreter

_PRE = 'import "std/set.lang";'


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


def main(body: str) -> str:
    return f"{_PRE}\nint main() {{\n{body}\nreturn 0;\n}}"


class TestSetBasic:
    def test_empty_set(self):
        _, out = run_out(main("""\
Set<int> s = Set<int>();
print(s.size());
print(s.isEmpty());
"""))
        assert out == ["0", "true"]

    def test_add_contains(self):
        _, out = run_out(main("""\
Set<int> s = Set<int>();
s.add(1);
s.add(2);
s.add(3);
print(s.contains(2));
print(s.contains(99));
"""))
        assert out == ["true", "false"]

    def test_add_dedup(self):
        _, out = run_out(main("""\
Set<int> s = Set<int>();
s.add(5);
s.add(5);
s.add(5);
print(s.size());
"""))
        assert out == ["1"]

    def test_remove(self):
        _, out = run_out(main("""\
Set<int> s = Set<int>();
s.add(10);
s.add(20);
s.remove(10);
print(s.size());
print(s.contains(10));
print(s.contains(20));
"""))
        assert out == ["1", "false", "true"]

    def test_remove_absent(self):
        _, out = run_out(main("""\
Set<int> s = Set<int>();
s.add(1);
s.remove(999);
print(s.size());
"""))
        assert out == ["1"]

    def test_clear(self):
        _, out = run_out(main("""\
Set<int> s = Set<int>();
s.add(1);
s.add(2);
s.clear();
print(s.size());
print(s.isEmpty());
"""))
        assert out == ["0", "true"]

    def test_to_list(self):
        _, out = run_out(main("""\
Set<int> s = Set<int>();
s.add(3);
s.add(1);
s.add(2);
List<int> l = s.toList();
print(l.length());
"""))
        assert out == ["3"]


class TestSetOperations:
    def test_union(self):
        _, out = run_out(main("""\
Set<int> a = Set<int>();
a.add(1); a.add(2); a.add(3);
Set<int> b = Set<int>();
b.add(3); b.add(4); b.add(5);
Set<int> u = a.union(b);
print(u.size());
print(u.contains(1));
print(u.contains(4));
print(u.contains(3));
"""))
        assert out == ["5", "true", "true", "true"]

    def test_intersection(self):
        _, out = run_out(main("""\
Set<int> a = Set<int>();
a.add(1); a.add(2); a.add(3);
Set<int> b = Set<int>();
b.add(2); b.add(3); b.add(4);
Set<int> inter = a.intersection(b);
print(inter.size());
print(inter.contains(2));
print(inter.contains(3));
print(inter.contains(1));
"""))
        assert out == ["2", "true", "true", "false"]

    def test_difference(self):
        _, out = run_out(main("""\
Set<int> a = Set<int>();
a.add(1); a.add(2); a.add(3);
Set<int> b = Set<int>();
b.add(2); b.add(3);
Set<int> diff = a.difference(b);
print(diff.size());
print(diff.contains(1));
print(diff.contains(2));
"""))
        assert out == ["1", "true", "false"]

    def test_string_set(self):
        _, out = run_out(main("""\
Set<string> s = Set<string>();
s.add("hello");
s.add("world");
s.add("hello");
print(s.size());
print(s.contains("world"));
"""))
        assert out == ["2", "true"]
