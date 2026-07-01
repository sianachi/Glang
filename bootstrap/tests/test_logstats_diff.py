"""Cross-backend differential test for the logstats real-world app.

Runs the frequency counter over a fixed input through the Python interpreter and
the native compiled binary and asserts identical output, covering both the file
argument path and stdin ("-"). Exercises HashMap counting, the ternary operator,
and format.lang output together.
"""

import os
import subprocess
import sys
import tempfile
from shutil import which

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_APP = os.path.join(_ROOT, "real-world-applications", "logstats.lang")

LOG = "GET /a 200\nGET /b 404\nPOST /a 200\nGET /a 500\nGET /b 200\n"

EXPECTED = (
    "      3   60%  200\n"
    "      1   20%  404\n"
    "      1   20%  500\n"
    "      5         3 distinct\n"
)


def _interp(args, stdin_bytes):
    cmd = [sys.executable, "bootstrap/main.py", "run", _APP] + args
    proc = subprocess.run(cmd, cwd=_ROOT, input=stdin_bytes, capture_output=True, timeout=60)
    assert proc.returncode == 0, proc.stderr.decode(errors="replace")
    return proc.stdout.decode()


def _build_native(d):
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


def test_logstats_interpreter_file():
    with tempfile.TemporaryDirectory() as d:
        log = os.path.join(d, "access.log")
        with open(log, "w", encoding="utf-8") as f:
            f.write(LOG)
        assert _interp([log, "2"], b"") == EXPECTED


@pytest.mark.skipif(which("gcc") is None, reason="native leg needs gcc")
def test_logstats_native_matches_interpreter():
    with tempfile.TemporaryDirectory() as d:
        log = os.path.join(d, "access.log")
        with open(log, "w", encoding="utf-8") as f:
            f.write(LOG)
        binary = _build_native(d)

        # file argument
        native = subprocess.run([binary, log, "2"], cwd=_ROOT, capture_output=True, timeout=20)
        assert native.returncode == 0, native.stderr.decode(errors="replace")
        assert native.stdout.decode() == EXPECTED == _interp([log, "2"], b"")

        # stdin path
        n2 = subprocess.run([binary, "-", "0"], cwd=_ROOT, input=b"x\ny\nx\n",
                            capture_output=True, timeout=20)
        assert n2.stdout.decode() == _interp(["-", "0"], b"x\ny\nx\n")
