"""Native tests for the GLANG_DEBUG_ALLOC debug allocator.

Compiles small programs with the self-hosted glangc, links the runtime, and runs
the binary with/without GLANG_DEBUG_ALLOC to check leak and double/invalid-free
reporting on stderr. The debug allocator is a compiled-path diagnostic; the
interpreters already reject double-free/use-after-free at runtime.
"""

import os
import subprocess
import sys
import tempfile

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _run(src: str, debug: bool):
    """Compile + link + run `src`; return (stdout, stderr)."""
    if not _have_gcc():
        pytest.skip("gcc not available")
    with tempfile.TemporaryDirectory() as d:
        lang = os.path.join(d, "p.lang")
        cfile = os.path.join(d, "p.c")
        binary = os.path.join(d, "p")
        with open(lang, "w", encoding="utf-8") as f:
            f.write(src)
        subprocess.run(
            [sys.executable, "bootstrap/main.py", "compile", lang, "-o", cfile],
            cwd=_ROOT, check=True, capture_output=True,
        )
        subprocess.run(
            ["gcc", "-w", cfile, "Toolchain/runtime/glang_runtime.c", "-o", binary],
            cwd=_ROOT, check=True, capture_output=True,
        )
        env = dict(os.environ)
        if debug:
            env["GLANG_DEBUG_ALLOC"] = "1"
        else:
            env.pop("GLANG_DEBUG_ALLOC", None)
        proc = subprocess.run([binary], cwd=_ROOT, capture_output=True, text=True, env=env)
        return proc.stdout, proc.stderr


def _have_gcc() -> bool:
    from shutil import which
    return which("gcc") is not None


LEAK = "int main() { int* a = alloc(int, 4); int* b = alloc(int, 8); free(a); print(1); return 0; }"
CLEAN = "int main() { int* a = alloc(int, 4); free(a); print(2); return 0; }"
DOUBLE = "int main() { int* a = alloc(int, 4); free(a); free(a); print(3); return 0; }"


def test_leak_reported_when_enabled():
    out, err = _run(LEAK, debug=True)
    assert out.strip() == "1"
    assert "1 leaked allocation(s)" in err


def test_leak_silent_when_disabled():
    out, err = _run(LEAK, debug=False)
    assert out.strip() == "1"
    assert "leaked" not in err


def test_clean_program_no_report():
    out, err = _run(CLEAN, debug=True)
    assert out.strip() == "2"
    assert "leaked" not in err
    assert "invalid" not in err


def test_double_free_reported():
    out, err = _run(DOUBLE, debug=True)
    assert out.strip() == "3"
    assert "invalid or double free" in err
