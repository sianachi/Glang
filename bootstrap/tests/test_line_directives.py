"""Tests for GLANG_LINES=1 — #line directives mapping generated C to .lang source.

The self-hosted compiler emits `#line N "<path>"` before each statement in a
block when GLANG_LINES=1, so gcc diagnostics and debuggers point back at the
original Glang source. The feature is opt-in and stdout-invisible, so we assert
directly on the generated C: the directives appear (with correct line numbers and
the source path) only when the flag is set, and never change program behaviour.
"""

import os
import re
import subprocess
import sys
import tempfile
from shutil import which

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

PROG = """\
int main() {
    int x = 3;
    int y = 4;
    print(toString(x + y));
    return 0;
}
"""


def _compile(src_path, out_path, lines):
    env = dict(os.environ)
    if lines:
        env["GLANG_LINES"] = "1"
    else:
        env.pop("GLANG_LINES", None)
    subprocess.run(
        [sys.executable, "bootstrap/main.py", "compile", src_path, "-o", out_path],
        cwd=_ROOT, check=True, capture_output=True, timeout=180, env=env,
    )
    with open(out_path, "r", encoding="utf-8") as f:
        return f.read()


def test_flag_off_emits_no_line_directives():
    with tempfile.TemporaryDirectory() as d:
        src = os.path.join(d, "p.lang")
        with open(src, "w", encoding="utf-8") as f:
            f.write(PROG)
        c = _compile(src, os.path.join(d, "p.c"), lines=False)
        assert "#line" not in c


def test_flag_on_maps_each_statement_to_its_source_line():
    with tempfile.TemporaryDirectory() as d:
        src = os.path.join(d, "p.lang")
        with open(src, "w", encoding="utf-8") as f:
            f.write(PROG)
        c = _compile(src, os.path.join(d, "p.c"), lines=True)
        # main()'s four statements sit on source lines 2..5.
        found = re.findall(r'#line (\d+) "([^"]+)"', c)
        nums = [int(n) for n, path in found]
        for expected in (2, 3, 4, 5):
            assert expected in nums, f"missing #line {expected}; got {nums}"
        # Every directive names the real source file.
        assert all(path.endswith("p.lang") for _, path in found)


@pytest.mark.skipif(which("gcc") is None, reason="native leg needs gcc")
def test_line_directives_do_not_change_behaviour():
    with tempfile.TemporaryDirectory() as d:
        src = os.path.join(d, "p.lang")
        with open(src, "w", encoding="utf-8") as f:
            f.write(PROG)
        cfile = os.path.join(d, "p.c")
        _compile(src, cfile, lines=True)
        binary = os.path.join(d, "p")
        subprocess.run(
            ["gcc", "-w", cfile, "Toolchain/runtime/glang_runtime.c", "-o", binary],
            cwd=_ROOT, check=True, capture_output=True, timeout=60,
        )
        proc = subprocess.run([binary], cwd=_ROOT, capture_output=True, timeout=20)
        assert proc.returncode == 0
        assert proc.stdout.decode() == "7\n"
