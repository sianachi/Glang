"""Format-A differential test for the self-hosted monomorphizer.

Each input is written to a temp .lang file; both paths LOAD it (resolving
transitive imports), monomorphize, and serialize:

  Python ref:  glang_loader.load(path) -> Monomorphizer().run(prog)
               -> tests.glang_show.show_program(prog)
  Glang:       compiler/mono_dump.lang reads the PATH from stdin, calls
               load() + monomorphize() + showProgram().

The mangled instance names must match byte-for-byte.
"""

import glob
import os
import subprocess
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from glang_loader.loader import load
from analyser.monomorphize import Monomorphizer
from errors.errors import TypeError as GTypeError
from tests.glang_show import show_program

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# A generic Box used across several snippets (mirrors tests/test_generics.py).
BOX = """
class Box<T> {
    T value;
    Box(T v) { this.value = v; }
    T get() { return this.value; }
    void set(T v) { this.value = v; }
}
"""

# Hand-written snippets exercising the trickiest monomorphizer paths.
SNIPPETS = [
    # No generics at all.
    "int main() { return 0; }",
    # Distinct instantiations -> distinct mangled classes.
    BOX + "int main() { Box<int> a = Box<int>(1); Box<string> b = Box<string>(\"x\"); return 0; }",
    # Unused template is dropped.
    BOX + "int main() { return 0; }",
    # Constructor type-arg inference.
    BOX + "int main() { Box<int> b = Box(9); return b.get(); }",
    # var infers generic class construction.
    BOX + "int main() { var b = Box(7); return b.get(); }",
    # Generic function, explicit args.
    "T identity<T>(T x) { return x; }\nint main() { print(identity<int>(42)); return 0; }",
    # Generic function, inferred args.
    "T identity<T>(T x) { return x; }\nint main() { print(identity(42)); return 0; }",
    # var local from generic function call.
    "T identity<T>(T x) { return x; }\nint main() { var x = identity(42); print(x); return x; }",
    # Nested generic inference: unwrap<T>(Box<T>).
    BOX + "T unwrap<T>(Box<T> box) { return box.get(); }\n"
        + "int main() { Box<int> b = Box<int>(11); return unwrap(b); }",
    # Nested generic instantiation Box<Box<int>>.
    BOX + "int main() { Box<Box<int>> bb = Box<Box<int>>(Box<int>(42)); "
        + "Box<int> inner = bb.get(); print(inner.get()); return 0; }",
    # Generic bound satisfied by interface implementation (function).
    """
    interface Named { string name(); }
    class Person implements Named { Person() {} string name() { return "Ada"; } }
    T keep<T extends Named>(T x) { return x; }
    int main() { Person p = Person(); var q = keep(p); print(q.name()); return 0; }
    """,
    # Generic bound satisfied by interface implementation (class).
    """
    interface Named { string name(); }
    class Person implements Named { Person() {} string name() { return "Ada"; } }
    class Box<T extends Named> { T value; Box(T v) { this.value = v; } T get() { return this.value; } }
    int main() { var box = Box(Person()); print(box.get().name()); return 0; }
    """,
    # Growable generic list (alloc(T,...) substitution, foreach-free).
    """
    class List<T> {
        T* data; int cap; int size;
        List() { this.cap = 2; this.size = 0; this.data = alloc(T, 2); }
        void add(T x) { this.data[this.size] = x; this.size = this.size + 1; }
        T get(int i) { return this.data[i]; }
        int length() { return this.size; }
    }
    int main() {
        List<int> xs = List<int>();
        for (int i = 0; i < 5; ++i) { xs.add(i); }
        int total = 0;
        for (int i = 0; i < xs.length(); ++i) { total = total + xs.get(i); }
        print(xs.length());
        return total;
    }
    """,
    # Generic union (Opt<T>).
    "union Opt<T> { Some { T value; } None { } }\n"
        + "int main() { return 0; }",
]

# Error snippets: (source, expected fragment in the AnalyzeError message).
ERROR_SNIPPETS = [
    ("int main() { Foo<int> x = Foo<int>(); return 0; }", "is not a generic"),
    ("class P<A, B> { A a; P() {} }\nint main() { P<int> p = P<int>(); return 0; }",
     "expects 2 type argument(s)"),
    ('T choose<T>(T a, T b) { return a; } int main() { choose(1, "x"); return 0; }',
     "cannot infer type argument 'T'"),
    ("T make<T>() { return T(); } int main() { make(); return 0; }",
     "cannot infer type argument 'T'"),
    ("""
     interface Named { string name(); }
     class Rock { Rock() {} }
     T keep<T extends Named>(T x) { return x; }
     int main() { Rock r = Rock(); keep(r); return 0; }
     """, "does not satisfy bound"),
]

# Generic stdlib modules wrapped in a tiny instantiating program.
STDLIB_WRAPPERS = [
    'import "std/list.lang";\nint main() { List<int> x = List<int>(); x.add(1); return x.get(0); }',
    'import "std/map.lang";\nint main() { Map<string,int> m = Map<string,int>(); m.set("a", 1); return m.getOr("a", 0); }',
    'import "std/set.lang";\nint main() { Set<int> s = Set<int>(); s.add(1); return 0; }',
    'import "std/stack.lang";\nint main() { Stack<int> s = Stack<int>(); s.push(1); return s.pop(); }',
    'import "std/queue.lang";\nint main() { Queue<int> q = Queue<int>(); q.enqueue(1); return q.dequeue(); }',
    'import "std/span.lang";\nint main() { return 0; }',
]

# Generic example programs.
EXAMPLE_FILES = sorted(glob.glob(os.path.join(_ROOT, "Toolchain", "examples", "generic_*.lang")))


def _py_mono(path: str) -> str:
    prog = load(path)
    Monomorphizer().run(prog)
    return show_program(prog)


def _py_mono_err(path: str):
    """Return the AnalyzeError message, or None if no error raised."""
    try:
        prog = load(path)
        Monomorphizer().run(prog)
        return None
    except GTypeError as e:
        return e.msg


def _glang_mono(path: str) -> str:
    proc = subprocess.run(
        [sys.executable, "bootstrap/main.py", "run", "Toolchain/compiler/mono_dump.lang"],
        input=path.encode("utf-8"), capture_output=True, cwd=_ROOT,
    )
    return proc.stdout.decode("utf-8").strip()


def _write_tmp(src: str) -> str:
    fd, path = tempfile.mkstemp(suffix=".lang")
    with os.fdopen(fd, "w") as f:
        f.write(src)
    return path


@pytest.mark.parametrize("src", SNIPPETS)
def test_snippets(src):
    path = _write_tmp(src)
    try:
        assert _glang_mono(path) == _py_mono(path)
    finally:
        os.unlink(path)


@pytest.mark.parametrize("src,fragment", ERROR_SNIPPETS, ids=lambda v: str(v)[:30])
def test_error_snippets(src, fragment):
    path = _write_tmp(src)
    try:
        py_msg = _py_mono_err(path)
        assert py_msg is not None, "expected Python to raise"
        assert fragment in py_msg
        glang_out = _glang_mono(path)
        assert glang_out.startswith("ERROR ")
        assert fragment in glang_out
    finally:
        os.unlink(path)


@pytest.mark.parametrize("src", STDLIB_WRAPPERS, ids=lambda s: s.split('"')[1])
def test_stdlib_wrappers(src):
    path = _write_tmp(src)
    try:
        assert _glang_mono(path) == _py_mono(path)
    finally:
        os.unlink(path)


@pytest.mark.parametrize("path", EXAMPLE_FILES, ids=lambda p: os.path.basename(p))
def test_example_files(path):
    assert _glang_mono(path) == _py_mono(path)
