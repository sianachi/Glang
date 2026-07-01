"""Cross-backend differential test for the vim-clone example editor.

Drives examples/tui/vim.lang with a scripted keystroke stream (fed on stdin,
which the raw-mode reader consumes byte by byte) against a known input file, and
checks the *saved* file content. The Python reference interpreter and the native
compiled binary must produce byte-identical results.

This exercises the whole TUI input path end to end: readByteTimeout, the CSI/ESC
decoder, modal editing (normal/insert/command), and file save via writeFile.
"""

import os
import subprocess
import sys
import tempfile
from shutil import which

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_VIM = os.path.join("real-world-applications", "vim.lang")

INPUT = "0123456789\nDELETE ME\nkeep\n"
# lll -> col3, x deletes '3'; j down; dd deletes line 2; i insert "->" at start
# of "keep"; ESC; :wq writes and quits.
KEYS = b"lllxjddi->\x1b:wq\x0d"
EXPECTED = "012456789\n->keep\n"

# Visual mode: v enters charwise select, llll extends over "hello", d deletes it,
# then :wq. Also exercises the yank register fill on delete.
VIS_INPUT = "hello world\nsecond\n"
VIS_KEYS = b"vlllld:wq\x0d"
VIS_EXPECTED = " world\nsecond\n"


def _run(cmd, infile_content, keys, cwd):
    with tempfile.TemporaryDirectory() as d:
        target = os.path.join(d, "buf.txt")
        with open(target, "w", encoding="utf-8") as f:
            f.write(infile_content)
        full = cmd + [target]
        proc = subprocess.run(
            full, cwd=cwd, input=keys, capture_output=True, timeout=60
        )
        assert proc.returncode == 0, proc.stderr.decode(errors="replace")
        with open(target, "r", encoding="utf-8") as f:
            return f.read()


def test_vim_edit_python_reference():
    out = _run([sys.executable, "bootstrap/main.py", "run", _VIM], INPUT, KEYS, _ROOT)
    assert out == EXPECTED


def test_vim_visual_delete_python_reference():
    out = _run(
        [sys.executable, "bootstrap/main.py", "run", _VIM], VIS_INPUT, VIS_KEYS, _ROOT
    )
    assert out == VIS_EXPECTED


@pytest.mark.skipif(which("gcc") is None, reason="native leg needs gcc")
def test_vim_edit_native_matches_reference():
    with tempfile.TemporaryDirectory() as d:
        cfile = os.path.join(d, "vim.c")
        binary = os.path.join(d, "vim")
        subprocess.run(
            [sys.executable, "bootstrap/main.py", "compile", _VIM, "-o", cfile],
            cwd=_ROOT, check=True, capture_output=True, timeout=180,
        )
        subprocess.run(
            ["gcc", "-w", cfile, "Toolchain/runtime/glang_runtime.c", "-o", binary],
            cwd=_ROOT, check=True, capture_output=True, timeout=60,
        )
        native = _run([binary], INPUT, KEYS, _ROOT)
        assert native == EXPECTED
        py = _run(
            [sys.executable, "bootstrap/main.py", "run", _VIM], INPUT, KEYS, _ROOT
        )
        assert native == py

        native_vis = _run([binary], VIS_INPUT, VIS_KEYS, _ROOT)
        assert native_vis == VIS_EXPECTED
