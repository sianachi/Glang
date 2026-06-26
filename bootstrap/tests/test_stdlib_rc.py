"""End-to-end tests for std/rc.lang (the manual refcount Rc<T>)."""

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


IMP = 'import "std/rc.lang";\n'


def test_count_transitions_and_payload():
    _, out = run_out(IMP + """
    int main() {
        int* payload = alloc(int, 1);
        payload[0] = 42;
        Rc<int> r = Rc<int>(payload);
        print(r.count()); print(r.get()[0]); r.retain(); print(r.count()); r.release(); print(r.count());
        r.release();            // frees payload + cell
        return 0;
    }
    """)
    assert out == ["1", "42", "2", "1"]


def test_shared_cell_across_copies():
    # Two Rc handles sharing the same cell observe one shared count.
    _, out = run_out(IMP + """
    int main() {
        int* payload = alloc(int, 1);
        payload[0] = 7;
        Rc<int> a = Rc<int>(payload);
        a.retain();             // count 2 (a second logical owner)
        Rc<int> b = a;          // shares the same cell
        print(b.count());       // 2
        b.release();            // count 1
        print(a.count());       // 1  (a sees b's release through the shared cell)
        a.release();            // frees
        return 0;
    }
    """)
    assert out == ["2", "1"]
