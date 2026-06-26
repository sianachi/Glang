"""Differential backend for the self-hosted interpreter (Toolchain/compiler/interp.lang).

Runs a Glang source string through the Glang interpreter driver
(Toolchain/compiler/interp_dump.lang) and reconstructs what the Python
Interpreter's run()/run_out() return:

  gi_run(src) -> (exit_code, output_lines)
  raises errors.errors.RuntimeError on a runtime error (RTERR), so it plugs into
  test_interpreter.py's `with pytest.raises(RuntimeError)` cases.

Select it by exporting GLANG_INTERP_BACKEND=glang (interpreted driver) or
GLANG_INTERP_BACKEND=glang-native (compile the driver with glangc first).
"""

from __future__ import annotations

import os
import subprocess
import sys

from errors.errors import RuntimeError as GRE

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(os.path.dirname(_HERE))          # repo root
_TOOLCHAIN = os.path.join(_REPO, "Toolchain")
_MAIN = os.path.join(_REPO, "bootstrap", "main.py")
_DRIVER = "compiler/interp_dump.lang"                     # relative to cwd=Toolchain
_NATIVE = os.environ.get("GLANG_INTERP_BACKEND") == "glang-native"
_binary: "str | None" = None


def _decode(s: str) -> str:
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
        d = tempfile.mkdtemp(prefix="glang_interp_")
        c = os.path.join(d, "interp.c")
        b = os.path.join(d, "interp")
        subprocess.run([sys.executable, _MAIN, "compile", _DRIVER, "-o", c],
                       cwd=_TOOLCHAIN, check=True, capture_output=True)
        subprocess.run(["gcc", "-O1", "-w", c, "runtime/glang_runtime.c", "-o", b],
                       cwd=_TOOLCHAIN, check=True, capture_output=True)
        _binary = b
    return _binary


def gi_run(src: str) -> "tuple[int, list[str]]":
    cmd = [_native_binary()] if _NATIVE else [sys.executable, _MAIN, "run", _DRIVER]
    proc = subprocess.run(cmd, input=src.encode("utf-8"),
                          capture_output=True, cwd=_TOOLCHAIN)
    out = proc.stdout.decode("utf-8")
    lines = [ln for ln in out.split("\n") if ln]
    output: list[str] = []
    code = 0
    for ln in lines:
        if "\t" in ln:
            tag, _, rest = ln.partition("\t")
        else:
            tag, rest = ln, ""
        if tag == "OUT":
            output.append(_decode(rest))
        elif tag == "ERR":
            pass  # printErr — not part of run_out's stdout list
        elif tag == "EXIT":
            code = int(rest)
        elif tag == "RTERR":
            raise GRE(_decode(rest), 0, 0)
        elif tag in ("TYPEERROR", "PARSEERROR", "LEXERROR"):
            raise AssertionError(
                f"{tag} from interp driver: {_decode(rest)!r}\n"
                f"stderr={proc.stderr.decode('utf-8')[:600]!r}"
            )
    if not lines:
        raise AssertionError(
            f"empty interp_dump output; stderr={proc.stderr.decode('utf-8')[:600]!r}"
        )
    return code, output
