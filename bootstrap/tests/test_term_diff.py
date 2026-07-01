"""Cross-backend differential test for the terminal-control builtins.

The ``term*`` builtins (termRawOn/termRawOff/termWidth/termHeight/
readByteTimeout/termResized/termInterrupted) are backed two ways that must agree
byte-for-byte:

  * the Python reference interpreter  -> real termios/ioctl/select via `main.py run`
  * the native compiled binary         -> the C runtime (glang_runtime.c)

Both legs run as subprocesses with a *pipe* on stdin (never a tty) and a pipe on
stdout, so the environment is deterministic regardless of where the suite runs:
raw mode and window-size queries fail the same way on both (`-1`), and the timed
read observes the exact bytes we feed. The self-hosted interpreter leg shares the
Python interpreter's implementation and is exercised elsewhere; it is verified
manually against this same program.
"""

import os
import subprocess
import sys
import tempfile
from shutil import which

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Non-tty contract: not a terminal, so raw mode and size queries report -1, the
# signal flags start clear, and a timed read of closed/empty stdin hits EOF.
PROBE = """
int main() {
    print(termRawOn());        // -1: stdin is a pipe, not a tty
    print(termRawOff());       // 0:  no-op when raw was never entered
    print(termWidth());        // -1: no window size on a pipe
    print(termHeight());       // -1
    print(termResized());      // false
    print(termInterrupted());  // false
    print(readByteTimeout(0)); // -1: immediate EOF on empty stdin
    return 0;
}
"""
PROBE_EXPECTED = ["-1", "0", "-1", "-1", "false", "false", "-1"]

# Timed read observes each fed byte in order, then EOF.
READ = """
int main() {
    print(readByteTimeout(1000));  // 65 'A'
    print(readByteTimeout(1000));  // 66 'B'
    print(readByteTimeout(1000));  // -1 EOF
    return 0;
}
"""
READ_STDIN = b"AB"
READ_EXPECTED = ["65", "66", "-1"]


def _lines(text: str) -> "list[str]":
    return [ln for ln in text.split("\n") if ln]


def _run_py(src: str, stdin_bytes: bytes) -> "list[str]":
    with tempfile.TemporaryDirectory() as d:
        lang = os.path.join(d, "p.lang")
        with open(lang, "w", encoding="utf-8") as f:
            f.write(src)
        proc = subprocess.run(
            [sys.executable, "bootstrap/main.py", "run", lang],
            cwd=_ROOT, input=stdin_bytes, capture_output=True, timeout=30,
        )
        assert proc.returncode == 0, proc.stderr.decode(errors="replace")
        return _lines(proc.stdout.decode())


def _run_native(src: str, stdin_bytes: bytes) -> "list[str]":
    with tempfile.TemporaryDirectory() as d:
        lang = os.path.join(d, "p.lang")
        cfile = os.path.join(d, "p.c")
        binary = os.path.join(d, "p")
        with open(lang, "w", encoding="utf-8") as f:
            f.write(src)
        subprocess.run(
            [sys.executable, "bootstrap/main.py", "compile", lang, "-o", cfile],
            cwd=_ROOT, check=True, capture_output=True, timeout=120,
        )
        subprocess.run(
            ["gcc", "-w", cfile, "Toolchain/runtime/glang_runtime.c", "-o", binary],
            cwd=_ROOT, check=True, capture_output=True, timeout=60,
        )
        proc = subprocess.run(
            [binary], cwd=_ROOT, input=stdin_bytes, capture_output=True, timeout=20
        )
        assert proc.returncode == 0, proc.stderr.decode(errors="replace")
        return _lines(proc.stdout.decode())


_NEEDS_GCC = pytest.mark.skipif(
    which("gcc") is None, reason="native leg needs gcc"
)


def test_probe_python_reference():
    assert _run_py(PROBE, b"") == PROBE_EXPECTED


def test_read_python_reference():
    assert _run_py(READ, READ_STDIN) == READ_EXPECTED


@_NEEDS_GCC
def test_probe_native_matches_reference():
    native = _run_native(PROBE, b"")
    assert native == PROBE_EXPECTED
    assert native == _run_py(PROBE, b"")


@_NEEDS_GCC
def test_read_native_matches_reference():
    native = _run_native(READ, READ_STDIN)
    assert native == READ_EXPECTED
    assert native == _run_py(READ, READ_STDIN)
