"""End-to-end tests for std/slice.lang (the bounds-checked Slice<T> view)."""

import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from loader.loader import Loader
from analyser.analyser import Analyser
from interpreter.interpreter import Interpreter


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


IMP = 'import "std/slice.lang";\n'


def test_get_set_through_backing():
    _, out = run_out(IMP + """
    int main() {
        int* blk = alloc(int, 4);
        for (int i = 0; i < 4; ++i) { blk[i] = i; }
        Slice<int> s = Slice<int>(blk, 0, 4);
        print(s.length());
        print(s.get(3));
        s.set(3, 42);
        print(blk[3]);          // writes through
        free(blk);
        return 0;
    }
    """)
    assert out == ["4", "3", "42"]


def test_subslice_aliases_backing():
    _, out = run_out(IMP + """
    int main() {
        int* blk = alloc(int, 5);
        for (int i = 0; i < 5; ++i) { blk[i] = i * 10; }
        Slice<int> s = Slice<int>(blk, 0, 5);
        Slice<int> sub = s.slice(1, 4);
        print(sub.length());    // 3
        print(sub.get(0));      // 10
        sub.set(0, 777);
        print(blk[1]);          // 777  (shared storage)
        free(blk);
        return 0;
    }
    """)
    assert out == ["3", "10", "777"]


def test_get_out_of_range_throws():
    code, out = run_out(IMP + """
    int main() {
        int* blk = alloc(int, 2);
        Slice<int> s = Slice<int>(blk, 0, 2);
        try { int y = s.get(9); print(y); }
        catch (Exception* e) { print(e->message); }
        free(blk);
        return 0;
    }
    """)
    assert code == 0
    assert out == ["Slice.get: index out of range"]


def test_bad_slice_bounds_throws():
    code, out = run_out(IMP + """
    int main() {
        int* blk = alloc(int, 3);
        Slice<int> s = Slice<int>(blk, 0, 3);
        try { Slice<int> bad = s.slice(1, 9); print(bad.length()); }
        catch (Exception* e) { print(e->message); }
        free(blk);
        return 0;
    }
    """)
    assert code == 0
    assert out == ["Slice.slice: bounds out of range"]
