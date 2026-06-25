"""Coordinator helper for the Phase-4 end-to-end gate of the self-hosted analyser.

Runs the full Glang analysis pipeline (compiler/analyse_dump.lang: inject Exception →
namespace_resolve → monomorphize → pass1_collect → Pass2Checker.check_program) on a
source string and reports the outcome, so the `ok(...)`/`err(...)` cases from
tests/test_analyser.py can be run differentially against the Glang implementation.

The end-to-end (ok/err) cases are the bulk of test_analyser.py; the direct type_utils /
SymbolTable unit tests and the Pass1 GlobalEnv-introspection tests are covered separately
by the per-module differential suites (test_tu_core/tu_env/symtab/pass1_glang.py).

`analyse_dump.lang` prints `OK` on success or `TYPEERROR\t<percent-encoded-msg>` on a type
error (and `PARSEERROR`/`LEXERROR`/`LOADERROR` on earlier-stage failures).
"""

from __future__ import annotations

import os
import subprocess
import sys

from errors.errors import TypeError as GTE

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DRIVER = "compiler/analyse_dump.lang"
_NATIVE = os.environ.get("GLANG_ANALYSER_BACKEND") == "glang-native"
_binary: str | None = None


def _decode(s: str) -> str:
    """Reverse analyse_dump's percent-encoding of the error message."""
    out: list[str] = []
    i = 0
    while i < len(s):
        if s[i] == "%" and i + 2 < len(s) + 1 and len(s) - i >= 3:
            try:
                out.append(chr(int(s[i + 1:i + 3], 16)))
                i += 3
                continue
            except ValueError:
                pass
        out.append(s[i])
        i += 1
    return "".join(out)


def _native_binary() -> str:
    global _binary
    if _binary is None:
        import tempfile
        d = tempfile.mkdtemp(prefix="glang_an_")
        c = os.path.join(d, "an.c")
        b = os.path.join(d, "an")
        subprocess.run([sys.executable, "main.py", "compile", _DRIVER, "-o", c],
                       cwd=_ROOT, check=True, capture_output=True)
        subprocess.run(["gcc", "-w", c, "runtime/glang_runtime.c", "-o", b],
                       cwd=_ROOT, check=True, capture_output=True)
        _binary = b
    return _binary


def glang_analyse(src: str) -> None:
    """Run the Glang pipeline on `src`.

    Returns None on success; raises errors.errors.TypeError(msg, 0, 0) if the Glang
    analyser reports a type error (so it plugs into test_analyser.py's `err` helper,
    which checks `fragment in exc.msg`).  Raises AssertionError on an unexpected
    (parse/lex/load) failure or malformed driver output.
    """
    cmd = [_native_binary()] if _NATIVE else [sys.executable, "main.py", "run", _DRIVER]
    proc = subprocess.run(cmd, input=src.encode("utf-8"), capture_output=True, cwd=_ROOT)
    out = proc.stdout.decode("utf-8").strip()
    lines = [ln for ln in out.splitlines() if ln]
    if not lines:
        raise AssertionError(
            f"empty analyse_dump output; stderr={proc.stderr.decode('utf-8')[:600]!r}"
        )
    last = lines[-1]
    if last == "OK":
        return None
    if last.startswith("TYPEERROR\t"):
        raise GTE(_decode(last.split("\t", 1)[1]), 0, 0)
    raise AssertionError(f"unexpected analyse_dump output: {out!r}")
