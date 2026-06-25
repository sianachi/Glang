"""Differential test for the self-hosted module loader.

Resolves a root file's transitive imports with both the Python loader
(`glang_loader.loader.load`) and the Glang one (via `compiler/load_dump.lang`),
and compares the canonical merged-Program form. Declaration order (post-order:
imported files before importer, dedup on first include) must match exactly.

Also checks that a mutual-import cycle is rejected by BOTH implementations.
"""

import os
import subprocess
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from glang_loader.loader import load as py_load
from tests.glang_show import show_program

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Real example roots that pull in stdlib via `import "std/..."` — exercises the
# std/ resolution path plus transitive imports and include-guard dedup.
ROOTS = [
    "Toolchain/examples/generic_list.lang",   # std/list
    "Toolchain/examples/generic_map.lang",    # std/map, std/stack, std/queue
    "Toolchain/examples/mini_lexer.lang",     # std/list, map, set, string, stringbuilder
    "Toolchain/examples/linq_demo.lang",      # std/linq (deep transitive graph)
    "Toolchain/examples/file_io.lang",        # std/io
    "Toolchain/examples/stdlib_math.lang",    # std/math
    "Toolchain/examples/adt_json.lang",       # std/string
    "Toolchain/examples/memory_owner_demo.lang",  # std/memory
]


def py_prog(path: str) -> str:
    return show_program(py_load(path))


def glang_prog(stdin_path: str) -> tuple[int, str]:
    proc = subprocess.run(
        [sys.executable, os.path.join(_ROOT, "bootstrap", "main.py"), "run",
         os.path.join(_ROOT, "Toolchain", "compiler", "load_dump.lang")],
        input=stdin_path.encode("utf-8"), capture_output=True,
        cwd=os.path.join(_ROOT, "Toolchain"),  # so the driver's std/... loads resolve
    )
    return proc.returncode, proc.stdout.decode("utf-8").strip()


@pytest.mark.parametrize("root", ROOTS, ids=lambda p: os.path.basename(p))
def test_loader_matches_python(root):
    abspath = os.path.join(_ROOT, root)
    rc, glang_out = glang_prog(abspath)
    assert rc == 0, f"loader driver failed: {glang_out}"
    assert glang_out == py_prog(abspath)


def test_circular_import_rejected():
    with tempfile.TemporaryDirectory() as d:
        a = os.path.join(d, "a.lang")
        b = os.path.join(d, "b.lang")
        with open(a, "w") as f:
            f.write('import "b.lang";\nint fromA() { return 1; }\n')
        with open(b, "w") as f:
            f.write('import "a.lang";\nint fromB() { return 2; }\n')

        # Python implementation must raise.
        from errors.errors import ImportError as GImportError
        with pytest.raises(GImportError):
            py_load(a)

        # Glang implementation must print LOADERROR and exit non-zero.
        rc, out = glang_prog(a)
        assert rc != 0
        assert out.startswith("LOADERROR")
        assert "circular import" in out
