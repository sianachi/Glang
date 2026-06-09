"""End-to-end tests for the stdlib Span<T> and MemoryOwner<T> types.

These import the real ``std/span.lang`` / ``std/memory.lang`` through the
Loader, so the programs exercise the shipped stdlib rather than inlined copies.
"""

import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from loader.loader import Loader
from analyser.analyser import Analyser
from interpreter.interpreter import Interpreter
from errors.errors import RuntimeError as GRE


def run_out(src: str):
    """Write `src` to a temp .lang file, load (resolving std/ imports),
    analyse, interpret; return (exit_code, output_lines)."""
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "prog.lang")
        with open(path, "w", encoding="utf-8") as f:
            f.write(src)
        program = Loader().load(path)
        env = Analyser().analyse(program)
        interp = Interpreter(env)
        code = interp.run(program)
        return code, interp.output


MEM = 'import "std/memory.lang";\n'


class TestMemoryOwner:
    def test_length_and_get_set(self):
        _, out = run_out(MEM + """
        int main() {
            MemoryOwner<int> o = MemoryOwner<int>(8);
            for (int i = 0; i < 8; ++i) { o.set(i, i * 10); }
            print(o.length());
            print(o.get(3));
            o.dispose();
            return 0;
        }
        """)
        assert out == ["8", "30"]

    def test_get_out_of_range_raises(self):
        with pytest.raises(GRE):
            run_out(MEM + """
            int main() {
                MemoryOwner<int> o = MemoryOwner<int>(4);
                print(o.get(10));
                o.dispose();
                return 0;
            }
            """)

    def test_heap_new_delete_runs_destructor(self):
        # delete frees the backing block via ~MemoryOwner; no double free.
        _, out = run_out(MEM + """
        int main() {
            MemoryOwner<byte>* o = new MemoryOwner<byte>(4);
            o->set(0, 0xAB);
            byte b = o->get(0);
            print((int) b);
            delete o;
            print(1);
            return 0;
        }
        """)
        assert out == ["171", "1"]


class TestSpan:
    def test_view_shares_backing(self):
        _, out = run_out(MEM + """
        int main() {
            MemoryOwner<int> o = MemoryOwner<int>(8);
            for (int i = 0; i < 8; ++i) { o.set(i, i * 10); }
            Span<int> v = o.span();
            print(v.length());
            print(v.get(5));
            o.dispose();
            return 0;
        }
        """)
        assert out == ["8", "50"]

    def test_slice_is_subview_and_aliases(self):
        _, out = run_out(MEM + """
        int main() {
            MemoryOwner<int> o = MemoryOwner<int>(8);
            for (int i = 0; i < 8; ++i) { o.set(i, i * 10); }
            Span<int> v = o.span();
            Span<int> mid = v.slice(2, 6);
            print(mid.length());
            print(mid.get(0));
            mid.set(0, 999);
            print(o.get(2));
            o.dispose();
            return 0;
        }
        """)
        # length 4; mid.get(0) == o[2] == 20; writing mid[0] aliases o[2].
        assert out == ["4", "20", "999"]

    def test_slice_get_past_view_length_raises(self):
        with pytest.raises(GRE):
            run_out(MEM + """
            int main() {
                MemoryOwner<int> o = MemoryOwner<int>(8);
                Span<int> v = o.span();
                Span<int> mid = v.slice(1, 3);
                print(mid.get(5));
                o.dispose();
                return 0;
            }
            """)

    def test_invalid_slice_bounds_raises(self):
        with pytest.raises(GRE):
            run_out(MEM + """
            int main() {
                MemoryOwner<int> o = MemoryOwner<int>(4);
                Span<int> v = o.span();
                Span<int> bad = v.slice(0, 10);
                print(bad.length());
                o.dispose();
                return 0;
            }
            """)
