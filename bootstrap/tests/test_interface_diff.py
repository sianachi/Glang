"""Cross-backend differential test for interface-pointer method dispatch.

A value of an interface type is a pointer to an implementing object; calling a
method on it must dispatch to the concrete class. The Python reference
interpreter dispatches on the runtime object's class; the native backend
dispatches on a class-id header (`__cid`) via a generated switch. Both must agree.
"""

import os
import subprocess
import sys
import tempfile
from shutil import which

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_PROG = os.path.join("Toolchain", "examples", "interfaces.lang")

EXPECTED = ["circle", "12.56636", "square", "6.25", "18.81636"]


def _lines(text):
    return [ln for ln in text.split("\n") if ln]


def _run_py():
    proc = subprocess.run(
        [sys.executable, "bootstrap/main.py", "run", _PROG],
        cwd=_ROOT, capture_output=True, timeout=60,
    )
    assert proc.returncode == 0, proc.stderr.decode(errors="replace")
    return _lines(proc.stdout.decode())


def _run_native():
    with tempfile.TemporaryDirectory() as d:
        cfile = os.path.join(d, "p.c")
        binary = os.path.join(d, "p")
        subprocess.run(
            [sys.executable, "bootstrap/main.py", "compile", _PROG, "-o", cfile],
            cwd=_ROOT, check=True, capture_output=True, timeout=180,
        )
        subprocess.run(
            ["gcc", "-w", cfile, "Toolchain/runtime/glang_runtime.c", "-o", binary],
            cwd=_ROOT, check=True, capture_output=True, timeout=60,
        )
        proc = subprocess.run([binary], cwd=_ROOT, capture_output=True, timeout=20)
        assert proc.returncode == 0, proc.stderr.decode(errors="replace")
        return _lines(proc.stdout.decode())


def test_interface_dispatch_python_reference():
    assert _run_py() == EXPECTED


@pytest.mark.skipif(which("gcc") is None, reason="native leg needs gcc")
def test_interface_dispatch_native_matches_reference():
    native = _run_native()
    assert native == EXPECTED
    assert native == _run_py()
