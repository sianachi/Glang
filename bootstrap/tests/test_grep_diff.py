"""Cross-backend differential test for the grep real-world app.

Runs the regex line-matcher over a fixed input through the Python interpreter and
the native compiled binary and asserts identical output, covering both the file
argument and stdin ("-") paths.
"""

import os
import subprocess
import sys
import tempfile
from shutil import which

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_APP = os.path.join(_ROOT, "real-world-applications", "grep.lang")

LOG = "error: disk full\nINFO all good\nWARN low memory\nerror: timeout 504\ndebug trace\n"

EXPECTED = (
    "1: error: disk full\n"
    "4: error: timeout 504\n"
    "-- 2 match(es) for /error/ in 5 line(s)\n"
)


def _interp(args, stdin_bytes):
    proc = subprocess.run(
        [sys.executable, "bootstrap/main.py", "run", _APP] + args,
        cwd=_ROOT, input=stdin_bytes, capture_output=True, timeout=60,
    )
    assert proc.returncode == 0, proc.stderr.decode(errors="replace")
    return proc.stdout.decode()


def _build(d):
    cfile = os.path.join(d, "p.c")
    binary = os.path.join(d, "p")
    subprocess.run(
        [sys.executable, "bootstrap/main.py", "compile", _APP, "-o", cfile],
        cwd=_ROOT, check=True, capture_output=True, timeout=180,
    )
    subprocess.run(
        ["gcc", "-w", cfile, "Toolchain/runtime/glang_runtime.c", "-o", binary],
        cwd=_ROOT, check=True, capture_output=True, timeout=60,
    )
    return binary


def test_grep_interpreter_file():
    with tempfile.TemporaryDirectory() as d:
        log = os.path.join(d, "log.txt")
        with open(log, "w", encoding="utf-8") as f:
            f.write(LOG)
        assert _interp(["error", log], b"") == EXPECTED


@pytest.mark.skipif(which("gcc") is None, reason="native leg needs gcc")
def test_grep_native_matches_interpreter():
    with tempfile.TemporaryDirectory() as d:
        log = os.path.join(d, "log.txt")
        with open(log, "w", encoding="utf-8") as f:
            f.write(LOG)
        binary = _build(d)

        nat = subprocess.run([binary, "error", log], cwd=_ROOT,
                             capture_output=True, timeout=20)
        assert nat.returncode == 0, nat.stderr.decode(errors="replace")
        assert nat.stdout.decode() == EXPECTED == _interp(["error", log], b"")

        # stdin path with an alternation pattern
        n2 = subprocess.run([binary, "WARN|INFO", "-"], cwd=_ROOT,
                            input=LOG.encode(), capture_output=True, timeout=20)
        assert n2.stdout.decode() == _interp(["WARN|INFO", "-"], LOG.encode())
