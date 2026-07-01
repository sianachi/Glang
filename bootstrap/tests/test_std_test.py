"""Behavioural test for std/test.lang, the in-language unit-test framework.

The all-passing path is covered by examples/test_demo.lang (interpreter == native
== golden). Here we check the *failing* path: a suite with a bad assertion must
print a FAIL line, the correct summary count, and report() must yield a nonzero
exit code on both backends.
"""

import os
import subprocess
import sys
import tempfile
from shutil import which

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

SRC = """
import "std/test.lang";

int main() {
    Test t = Test();
    t.eqInt(1 + 1, 2, "ok");
    t.eqInt(2 + 2, 5, "deliberately wrong");
    t.isTrue(false, "also wrong");
    return t.report();
}
"""

EXPECTED = (
    "  PASS  ok\n"
    "  FAIL  deliberately wrong (want 5, got 4)\n"
    "  FAIL  also wrong\n"
    "1/3 passed\n"
)


def _write_src(d):
    path = os.path.join(d, "failing.lang")
    with open(path, "w", encoding="utf-8") as f:
        f.write(SRC)
    return path


def test_failing_suite_interpreter():
    with tempfile.TemporaryDirectory() as d:
        src = _write_src(d)
        proc = subprocess.run(
            [sys.executable, "bootstrap/main.py", "run", src],
            cwd=_ROOT, capture_output=True, timeout=60,
        )
        assert proc.returncode == 1, proc.stderr.decode(errors="replace")
        assert proc.stdout.decode() == EXPECTED


@pytest.mark.skipif(which("gcc") is None, reason="native leg needs gcc")
def test_failing_suite_native():
    with tempfile.TemporaryDirectory() as d:
        src = _write_src(d)
        cfile = os.path.join(d, "p.c")
        binary = os.path.join(d, "p")
        subprocess.run(
            [sys.executable, "bootstrap/main.py", "compile", src, "-o", cfile],
            cwd=_ROOT, check=True, capture_output=True, timeout=180,
        )
        subprocess.run(
            ["gcc", "-w", cfile, "Toolchain/runtime/glang_runtime.c", "-o", binary],
            cwd=_ROOT, check=True, capture_output=True, timeout=60,
        )
        proc = subprocess.run([binary], cwd=_ROOT, capture_output=True, timeout=20)
        assert proc.returncode == 1, proc.stderr.decode(errors="replace")
        assert proc.stdout.decode() == EXPECTED
