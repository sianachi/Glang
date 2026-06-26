"""End-to-end tests for std/arena.lang (the typed bump allocator Arena<T>)."""

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


IMP = 'import "std/arena.lang";\n'


def test_alloc_one_writes_through_pointers():
    _, out = run_out(IMP + """
    int main() {
        Arena<int> a = Arena<int>(3);
        int* x = a.allocOne(); *x = 10;
        int* y = a.allocOne(); *y = 20;
        print(*x + *y);
        print(a.used());
        print(a.remaining());
        a.dispose();
        return 0;
    }
    """)
    assert out == ["30", "2", "1"]


def test_reset_reuses_block():
    _, out = run_out(IMP + """
    int main() {
        Arena<int> a = Arena<int>(2);
        int* p = a.allocOne(); *p = 1;
        a.allocOne();
        print(a.used());        // 2
        a.reset();
        print(a.used());        // 0
        int* q = a.allocOne(); *q = 5;
        print(*q);              // 5
        a.dispose();
        return 0;
    }
    """)
    assert out == ["2", "0", "5"]


def test_exhaustion_throws():
    code, out = run_out(IMP + """
    int main() {
        Arena<int> a = Arena<int>(1);
        a.allocOne();
        try { int* w = a.allocOne(); print(*w); }
        catch (Exception* e) { print(e->message); }
        a.dispose();
        return 0;
    }
    """)
    assert code == 0
    assert out == ["Arena.allocOne: arena exhausted"]
