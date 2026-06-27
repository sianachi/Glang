"""Differential tests for the pure-Glang stdlib additions.

Covers result, random, hex, base64, hash, url, path, csv, uuid, heap, deque,
bitset, lru, cli, log, and the pure parts of http_client / multipart. Each
program is run under the Python reference interpreter and the native compiler;
the two outputs must be byte-identical (the project's correctness contract), and
a few sentinel values pin down expected results.

The example programs in Toolchain/examples are reused as test inputs, so they are
exercised on both backends in addition to the interpreter-only golden harness.
"""

import os
import subprocess
import sys
import tempfile
from shutil import which

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_EXAMPLES = os.path.join(_ROOT, "Toolchain", "examples")


def _interp(path: str) -> "list[str]":
    proc = subprocess.run(
        [sys.executable, "bootstrap/main.py", "run", path],
        cwd=_ROOT, capture_output=True, text=True, timeout=60,
    )
    assert proc.returncode == 0, proc.stderr
    out = proc.stdout
    return out.split("\n")[:-1] if out.endswith("\n") else out.split("\n")


def _compiled(path: str) -> "list[str]":
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
        proc = subprocess.run([binary], cwd=_ROOT, capture_output=True, text=True, timeout=30)
        assert proc.returncode == 0, proc.stderr
        out = proc.stdout
        return out.split("\n")[:-1] if out.endswith("\n") else out.split("\n")


def _both(path: str) -> "tuple[list[str], list[str]]":
    interp = _interp(path)
    if which("gcc") is None:
        return interp, interp
    return interp, _compiled(path)


def _temp_prog(src: str) -> str:
    fd, path = tempfile.mkstemp(suffix=".lang", dir=_ROOT)
    with os.fdopen(fd, "w") as f:
        f.write(src)
    return path


def test_encoding_demo_matches_across_backends():
    i, c = _both(os.path.join(_EXAMPLES, "encoding_demo.lang"))
    assert i == c
    joined = "\n".join(i)
    assert "hex:    486900ff01fe" in joined       # binary bytes incl. 0x00/0xFF
    assert "base64: SGkA/wH+" in joined
    assert 'crc32("glang"):  4252829502' in joined
    assert "uuid4:  " in joined and "-4" in joined  # version-4 nibble present


def test_collections_demo_matches_across_backends():
    i, c = _both(os.path.join(_EXAMPLES, "collections_demo.lang"))
    assert i == c
    joined = "\n".join(i)
    assert "heap pop order: 1 3 5 7 9" in joined
    assert "evens set count: 8" in joined
    assert "after evict, has b? false" in joined


def test_web_helpers_demo_matches_across_backends():
    i, c = _both(os.path.join(_EXAMPLES, "web_helpers_demo.lang"))
    assert i == c
    joined = "\n".join(i)
    assert "encode: a%20b%26c%3Dd" in joined
    assert "normalize: /a/c" in joined
    assert "csv rows: 2, field: hello, world" in joined
    assert "multipart user: ada" in joined
    assert "parsed status: 204 No Content" in joined


CLI_LOG_PROG = r"""
import "std/cli.lang";
import "std/log.lang";

int main() {
    List<string> argv = List<string>();
    argv.add("--name"); argv.add("glang");
    argv.add("--port=8080");
    argv.add("--verbose");
    argv.add("in.txt"); argv.add("out.txt");

    List<string> flags = List<string>(); flags.add("verbose");
    CliArgs* a = parseArgsFlags(argv, flags);
    print(a->getOpt("name", "?"));
    print(intToStr(a->getOptInt("port", 0)));
    print(toString(a->getFlag("verbose")));
    print(intToStr(a->count()));
    print(a->positional(0));
    print(formatLogLine(1700000000000, 2, "svc", "slow"));
    print(logLevelName(3));
    print(intToStr(logLevelFromName("debug")));
    return 0;
}
"""


def test_cli_and_log_match_across_backends():
    path = _temp_prog(CLI_LOG_PROG)
    try:
        i, c = _both(path)
    finally:
        os.unlink(path)
    assert i == c
    assert i == [
        "glang", "8080", "true", "2", "in.txt",
        "1700000000000 [WARN] svc: slow", "ERROR", "0",
    ]
