"""Cross-backend differential test for the todo real-world app.

Runs a fixed sequence of subcommands (which exercise interface-pointer dispatch,
finally-based persistence, and the ternary operator) through the Python
interpreter and the native compiled binary, each in its own fresh working
directory, and asserts identical stdout and identical final data file.
"""

import os
import subprocess
import sys
import tempfile
from shutil import which

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_APP = os.path.join(_ROOT, "real-world-applications", "todo.lang")

SEQUENCE = [
    ["add", "buy milk"],
    ["add", "write code"],
    ["add", "ship it"],
    ["done", "2"],
    ["rm", "1"],
    ["list"],
]


def _run_sequence(run_cmd, workdir):
    """run_cmd(args) -> argv prefix; execute the sequence, return (output, data)."""
    out = []
    for args in SEQUENCE:
        proc = subprocess.run(
            run_cmd + args, cwd=workdir, capture_output=True, timeout=30
        )
        assert proc.returncode == 0, proc.stderr.decode(errors="replace")
        out.append(proc.stdout.decode())
    data_path = os.path.join(workdir, "todo.data")
    data = ""
    if os.path.exists(data_path):
        with open(data_path, "r", encoding="utf-8") as f:
            data = f.read()
    return "".join(out), data


def _interpreter_result():
    with tempfile.TemporaryDirectory() as d:
        cmd = [sys.executable, os.path.join(_ROOT, "bootstrap", "main.py"), "run", _APP]
        return _run_sequence(cmd, d)


def _native_result():
    with tempfile.TemporaryDirectory() as build:
        cfile = os.path.join(build, "todo.c")
        binary = os.path.join(build, "todo")
        subprocess.run(
            [sys.executable, "bootstrap/main.py", "compile", _APP, "-o", cfile],
            cwd=_ROOT, check=True, capture_output=True, timeout=180,
        )
        subprocess.run(
            ["gcc", "-w", cfile, "Toolchain/runtime/glang_runtime.c", "-o", binary],
            cwd=_ROOT, check=True, capture_output=True, timeout=60,
        )
        with tempfile.TemporaryDirectory() as run_dir:
            return _run_sequence([binary], run_dir)


EXPECTED_LIST_TAIL = "[ ] 3 ship it\n"   # after done 2 + rm 1, only #2(done) and #3 remain


def test_todo_interpreter():
    out, data = _interpreter_result()
    # #2 marked done, #1 removed -> #2 and #3 remain
    assert "[x] 2 write code" in out
    assert "[ ] 3 ship it" in out
    assert "1 open, 2 total" in out
    assert data == "2\t1\twrite code\n3\t0\tship it\n"


@pytest.mark.skipif(which("gcc") is None, reason="native leg needs gcc")
def test_todo_native_matches_interpreter():
    iout, idata = _interpreter_result()
    nout, ndata = _native_result()
    assert nout == iout
    assert ndata == idata
