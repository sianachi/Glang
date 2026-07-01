"""Cross-backend differential test for the filesystem / environment built-ins.

Runs a program that reads an environment variable and creates, renames, and
removes files/directories through the Python interpreter and the native compiled
binary, each in its own fresh temp directory with the same environment, and
asserts identical output.
"""

import os
import subprocess
import sys
import tempfile
from shutil import which

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

PROG = """
int main() {
    print(getEnv("GLANG_FS_TEST"));
    print(getEnv("GLANG_FS_UNSET") == "");
    string dir = getArg(0);
    print(makeDir(dir + "/sub"));
    print(isDir(dir + "/sub"));
    writeFile(dir + "/f.txt", "x");
    print(fileExists(dir + "/f.txt"));
    print(renameFile(dir + "/f.txt", dir + "/g.txt"));
    print(fileExists(dir + "/g.txt"));
    print(removeFile(dir + "/g.txt"));
    print(fileExists(dir + "/g.txt") == false);
    print(isDir(dir + "/nope"));
    return 0;
}
"""

EXPECTED = ["hello", "true", "true", "true", "true", "true", "true", "true", "true", "false"]


def _lines(text):
    return [ln for ln in text.split("\n") if ln]


def _env():
    e = dict(os.environ)
    e["GLANG_FS_TEST"] = "hello"
    e.pop("GLANG_FS_UNSET", None)
    return e


def _run_py(prog_path, work):
    proc = subprocess.run(
        [sys.executable, "bootstrap/main.py", "run", prog_path, work],
        cwd=_ROOT, capture_output=True, timeout=60, env=_env(),
    )
    assert proc.returncode == 0, proc.stderr.decode(errors="replace")
    return _lines(proc.stdout.decode())


def test_fs_builtins_interpreter():
    with tempfile.TemporaryDirectory() as d:
        prog = os.path.join(d, "p.lang")
        with open(prog, "w", encoding="utf-8") as f:
            f.write(PROG)
        work = os.path.join(d, "work")
        os.mkdir(work)
        assert _run_py(prog, work) == EXPECTED


@pytest.mark.skipif(which("gcc") is None, reason="native leg needs gcc")
def test_fs_builtins_native_matches_interpreter():
    with tempfile.TemporaryDirectory() as d:
        prog = os.path.join(d, "p.lang")
        with open(prog, "w", encoding="utf-8") as f:
            f.write(PROG)
        cfile = os.path.join(d, "p.c")
        binary = os.path.join(d, "p")
        subprocess.run(
            [sys.executable, "bootstrap/main.py", "compile", prog, "-o", cfile],
            cwd=_ROOT, check=True, capture_output=True, timeout=180,
        )
        subprocess.run(
            ["gcc", "-w", cfile, "Toolchain/runtime/glang_runtime.c", "-o", binary],
            cwd=_ROOT, check=True, capture_output=True, timeout=60,
        )
        w1 = os.path.join(d, "wn")
        os.mkdir(w1)
        native = subprocess.run([binary, w1], cwd=_ROOT, capture_output=True,
                                timeout=20, env=_env())
        assert native.returncode == 0, native.stderr.decode(errors="replace")
        assert _lines(native.stdout.decode()) == EXPECTED
