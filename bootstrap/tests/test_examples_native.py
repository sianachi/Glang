"""Native-backend differential coverage for selected examples.

For each listed example, compile it with the self-hosted compiler, run the
binary, and assert its stdout matches the golden file (the same golden the
interpreter is checked against in test_examples.py). This gives interpreter ==
native == golden for language features whose behaviour must be identical on both
backends. Add an example's stem to NATIVE_EXAMPLES when it needs native coverage.
"""

import os
import subprocess
import sys
import tempfile
from shutil import which

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_EXAMPLES = os.path.join("Toolchain", "examples")
_EXPECTED = os.path.join(_ROOT, "Toolchain", "examples", "expected")

# Examples whose compiled output must match their golden byte-for-byte.
NATIVE_EXAMPLES = [
    "interfaces",
    "ternary",
    "exceptions_basic",
    "format_demo",
    "hashmap_demo",
]


def _golden(stem):
    with open(os.path.join(_EXPECTED, stem + ".expected"), "r", encoding="utf-8") as f:
        return f.read()


def _compile_and_run(stem):
    src = os.path.join(_EXAMPLES, stem + ".lang")
    with tempfile.TemporaryDirectory() as d:
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
        assert proc.returncode == 0, proc.stderr.decode(errors="replace")
        return proc.stdout.decode()


@pytest.mark.skipif(which("gcc") is None, reason="native leg needs gcc")
@pytest.mark.parametrize("stem", NATIVE_EXAMPLES)
def test_native_matches_golden(stem):
    assert _compile_and_run(stem) == _golden(stem)
