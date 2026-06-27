"""Differential test for std/static.lang (binary-safe file I/O + path safety).

static.lang is pure Glang over the file builtins (fileSize / readFileInto /
writeFileFrom / listDir), which hit the real filesystem on every backend. The
same program runs under the Python reference interpreter and the native compiler;
output must be byte-identical. The key property exercised is a binary round-trip
through a file containing 0x00 and 0xFF — which string-based readFile/writeFile
cannot do — plus path-traversal rejection in sanitizeRelPath.
"""

import os
import subprocess
import sys
import tempfile
from shutil import which

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# A scratch dir the program writes to / reads from / lists. Substituted in below.
PROG_TMPL = r"""
import "std/static.lang";

int main() {
    // --- MIME + extension ---
    print(mimeType("/x/LOGO.PNG"));
    print(mimeType("a/b/app.js"));
    print(mimeType("plain"));
    print(pathExtension("y.tar.gz"));

    // --- path safety ---
    print(sanitizeRelPath("css/app.css"));
    print("[" + sanitizeRelPath("../secret") + "]");
    print("[" + sanitizeRelPath("/abs/x") + "]");
    print("[" + sanitizeRelPath("a/../../b") + "]");
    print(sanitizeRelPath("./a/./b.txt"));

    // --- binary round-trip via Bytes (0x00 and 0xFF must survive) ---
    Bytes* b = new Bytes(6);
    b->append((byte)0); b->append((byte)255); b->append((byte)65);
    b->append((byte)0); b->append((byte)66); b->append((byte)255);
    print(writeBytesFile("__DIR__/blob.bin", b));
    int sz = fileSize("__DIR__/blob.bin");
    print(sz);
    Bytes* r = readFileBytes("__DIR__/blob.bin");
    print(r->length());
    print((int)(r->get(0)));
    print((int)(r->get(1)));
    print((int)(r->get(3)));
    print((int)(r->get(5)));
    print(readFileBytes("__DIR__/does-not-exist") == null);

    // --- listing (sorted, deterministic) ---
    Bytes* z = new Bytes(1); z->append((byte)97);
    writeBytesFile("__DIR__/aaa.txt", z);
    List<string> names = listDirNames("__DIR__");
    print(names.length());
    return 0;
}
"""

EXPECTED = [
    "image/png", "text/javascript; charset=utf-8", "application/octet-stream", "gz",
    "css/app.css", "[]", "[]", "[]", "a/b.txt",
    "true", "6", "6", "0", "255", "0", "255",
    "true",
    "2",   # blob.bin + aaa.txt
]


def _write_prog(scratch: str) -> str:
    fd, path = tempfile.mkstemp(suffix=".lang")
    with os.fdopen(fd, "w") as f:
        f.write(PROG_TMPL.replace("__DIR__", scratch))
    return path


def _interp_run(path: str) -> "list[str]":
    proc = subprocess.run(
        [sys.executable, "bootstrap/main.py", "run", path],
        cwd=_ROOT, capture_output=True, text=True, timeout=60,
    )
    assert proc.returncode == 0, proc.stderr
    out = proc.stdout
    return out.split("\n")[:-1] if out.endswith("\n") else out.split("\n")


def _compiled_run(path: str) -> "list[str]":
    with tempfile.TemporaryDirectory() as d:
        cfile = os.path.join(d, "p.c")
        binary = os.path.join(d, "p")
        subprocess.run(
            [sys.executable, "bootstrap/main.py", "compile", path, "-o", cfile],
            cwd=_ROOT, check=True, capture_output=True,
        )
        subprocess.run(
            ["gcc", "-w", cfile, "Toolchain/runtime/glang_runtime.c", "-o", binary],
            cwd=_ROOT, check=True, capture_output=True,
        )
        proc = subprocess.run([binary], cwd=_ROOT, capture_output=True, text=True, timeout=20)
        assert proc.returncode == 0, proc.stderr
        out = proc.stdout
        return out.split("\n")[:-1] if out.endswith("\n") else out.split("\n")


def test_static_interpreter():
    with tempfile.TemporaryDirectory() as scratch:
        path = _write_prog(scratch)
        try:
            assert _interp_run(path) == EXPECTED
        finally:
            os.unlink(path)


@pytest.mark.skipif(which("gcc") is None, reason="gcc not available")
def test_static_compiled_matches_interpreter():
    # Fresh scratch dir per backend so the directory-listing count is stable.
    with tempfile.TemporaryDirectory() as sc:
        cp = _write_prog(sc)
        try:
            compiled = _compiled_run(cp)
        finally:
            os.unlink(cp)
    with tempfile.TemporaryDirectory() as si:
        ip = _write_prog(si)
        try:
            interpreted = _interp_run(ip)
        finally:
            os.unlink(ip)
    assert compiled == EXPECTED == interpreted
