"""Cross-backend differential test for the textstats real-world app.

Runs the analyzer over a fixed text through the Python interpreter and the native
compiled binary and asserts identical output — covering the uint FNV checksum,
HashMap word counting, string-interpolated report, and default-argument bars.
"""

import os
import subprocess
import sys
import tempfile
from shutil import which

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_APP = os.path.join(_ROOT, "real-world-applications", "textstats.lang")

TEXT = "the quick brown fox\nthe lazy dog\nthe fox runs\nquick quick fox\n"

EXPECTED = (
    "lines:     4\n"
    "words:     13\n"
    "unique:    7\n"
    "chars:     62\n"
    "checksum:  7229080912169404640\n"
)


def _interp(target):
    proc = subprocess.run(
        [sys.executable, "bootstrap/main.py", "run", _APP, target],
        cwd=_ROOT, capture_output=True, timeout=60,
    )
    assert proc.returncode == 0, proc.stderr.decode(errors="replace")
    return proc.stdout.decode()


def _native(build_dir, target):
    cfile = os.path.join(build_dir, "p.c")
    binary = os.path.join(build_dir, "p")
    subprocess.run(
        [sys.executable, "bootstrap/main.py", "compile", _APP, "-o", cfile],
        cwd=_ROOT, check=True, capture_output=True, timeout=180,
    )
    subprocess.run(
        ["gcc", "-w", cfile, "Toolchain/runtime/glang_runtime.c", "-o", binary],
        cwd=_ROOT, check=True, capture_output=True, timeout=60,
    )
    proc = subprocess.run([binary, target], cwd=_ROOT, capture_output=True, timeout=20)
    assert proc.returncode == 0, proc.stderr.decode(errors="replace")
    return proc.stdout.decode()


def test_textstats_interpreter():
    with tempfile.TemporaryDirectory() as d:
        f = os.path.join(d, "notes.txt")
        with open(f, "w", encoding="utf-8") as fh:
            fh.write(TEXT)
        out = _interp(f)
    # Stable lines regardless of the temp path (skip the file: line).
    for line in EXPECTED.splitlines():
        assert line in out


@pytest.mark.skipif(which("gcc") is None, reason="native leg needs gcc")
def test_textstats_native_matches_interpreter():
    with tempfile.TemporaryDirectory() as d:
        f = os.path.join(d, "notes.txt")
        with open(f, "w", encoding="utf-8") as fh:
            fh.write(TEXT)
        assert _native(d, f) == _interp(f)
