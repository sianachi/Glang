"""Cross-backend differential test for the calc real-world app.

Evaluates a battery of expressions — precedence, parentheses, unary minus,
integer division/modulo, and the error paths (bad char, division by zero,
unbalanced parens) — through the Python interpreter and the native compiled
binary, asserting identical output. Also covers the stdin path.
"""

import os
import subprocess
import sys
import tempfile
from shutil import which

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_APP = os.path.join(_ROOT, "real-world-applications", "calc.lang")

CASES = [
    "2 + 3 * (4 - 1)",
    "-(5 + 2) * 3",
    "100 / 7",
    "10 % 3",
    "((1 + 2) * (3 + 4)) - 5",
    "7 - 3 - 2",          # left-associative subtraction
    "2 + ",               # parse error
    "1 / 0",              # division by zero
    "(1 + 2",             # unbalanced
    "3 @ 4",              # bad character
]


def _interp(arg, stdin_bytes=b""):
    proc = subprocess.run(
        [sys.executable, "bootstrap/main.py", "run", _APP] + ([arg] if arg is not None else []),
        cwd=_ROOT, input=stdin_bytes, capture_output=True, timeout=60,
    )
    return proc.returncode, proc.stdout.decode()


def _build(d):
    cfile = os.path.join(d, "c.c")
    binary = os.path.join(d, "c")
    subprocess.run(
        [sys.executable, "bootstrap/main.py", "compile", _APP, "-o", cfile],
        cwd=_ROOT, check=True, capture_output=True, timeout=180,
    )
    subprocess.run(
        ["gcc", "-w", cfile, "Toolchain/runtime/glang_runtime.c", "-o", binary],
        cwd=_ROOT, check=True, capture_output=True, timeout=60,
    )
    return binary


@pytest.mark.parametrize("expr", CASES)
def test_calc_interpreter_expected(expr):
    # A couple of anchored expectations so the interpreter isn't only checked
    # against itself.
    code, out = _interp(expr)
    if expr == "2 + 3 * (4 - 1)":
        assert (code, out) == (0, "11\n")
    if expr == "1 / 0":
        assert (code, out) == (1, "error: division by zero\n")


@pytest.mark.skipif(which("gcc") is None, reason="native leg needs gcc")
def test_calc_native_matches_interpreter():
    with tempfile.TemporaryDirectory() as d:
        binary = _build(d)
        for expr in CASES:
            nat = subprocess.run([binary, expr], cwd=_ROOT, capture_output=True, timeout=20)
            assert (nat.returncode, nat.stdout.decode()) == _interp(expr), expr

        # stdin path (no argument): expression comes from standard input.
        nat = subprocess.run([binary], cwd=_ROOT, input=b"6 * 7\n",
                             capture_output=True, timeout=20)
        assert (nat.returncode, nat.stdout.decode()) == _interp(None, b"6 * 7\n")
