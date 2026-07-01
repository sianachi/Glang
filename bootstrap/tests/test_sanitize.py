"""Tests for the opt-in compiled-mode sanitizer (GLANG_SANITIZE=1).

When compiled with GLANG_SANITIZE=1, the emitter routes alloc/free/indexing
through a size-aware runtime registry that aborts on an out-of-bounds index,
a use-after-free, or a double free. When off, code is emitted unchecked (and a
correct program behaves identically either way).
"""

import os
import subprocess
import sys
import tempfile
from shutil import which

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

VALID = """
int main() {
    int* a = alloc(int, 4);
    for (int i = 0; i < 4; i = i + 1) { a[i] = i * i; }
    int total = 0;
    for (int i = 0; i < 4; i = i + 1) { total = total + a[i]; }
    print(total);   // 0+1+4+9 = 14
    free(a);
    return 0;
}
"""

OOB = """
int main() {
    int* a = alloc(int, 3);
    a[0] = 1;
    print(a[7]);   // out of bounds
    return 0;
}
"""


def _compile(src, sanitize):
    d = tempfile.mkdtemp()
    lang = os.path.join(d, "p.lang")
    cfile = os.path.join(d, "p.c")
    binary = os.path.join(d, "p")
    with open(lang, "w", encoding="utf-8") as f:
        f.write(src)
    env = dict(os.environ)
    if sanitize:
        env["GLANG_SANITIZE"] = "1"
    else:
        env.pop("GLANG_SANITIZE", None)
    subprocess.run(
        [sys.executable, "bootstrap/main.py", "compile", lang, "-o", cfile],
        cwd=_ROOT, check=True, capture_output=True, timeout=180, env=env,
    )
    subprocess.run(
        ["gcc", "-w", cfile, "Toolchain/runtime/glang_runtime.c", "-o", binary],
        cwd=_ROOT, check=True, capture_output=True, timeout=60,
    )
    return binary


needs_gcc = pytest.mark.skipif(which("gcc") is None, reason="needs gcc")


@needs_gcc
def test_valid_program_identical_with_and_without_sanitize():
    plain = subprocess.run([_compile(VALID, False)], capture_output=True, timeout=20)
    checked = subprocess.run([_compile(VALID, True)], capture_output=True, timeout=20)
    assert plain.returncode == 0 and checked.returncode == 0
    assert plain.stdout == checked.stdout == b"14\n"


@needs_gcc
def test_out_of_bounds_aborts_only_when_sanitized():
    # Unchecked: reads adjacent memory, does not abort.
    plain = subprocess.run([_compile(OOB, False)], capture_output=True, timeout=20)
    assert plain.returncode == 0
    # Checked: aborts with a diagnostic.
    checked = subprocess.run([_compile(OOB, True)], capture_output=True, timeout=20)
    assert checked.returncode != 0
    assert b"out of bounds" in checked.stderr
