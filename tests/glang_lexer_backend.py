"""Drop-in backend that runs the self-hosted Glang lexer and adapts its output
to the ``lexer.lexer.Lexer`` interface, so the existing ``tests/test_lexer.py``
suite can be run against it unchanged (differential testing).

Each ``GlangLexer(src).tokenize()`` runs ``compiler/lex_dump.lang`` on ``src``
and parses its one-line-per-token output back into ``Token`` objects.  A
``LEXERROR`` line is turned back into a ``LexError`` so ``pytest.raises`` works.

Two engines, chosen by the ``GLANG_LEXER_BACKEND`` value:

* ``glang`` (default) — run via the interpreter.  Strings are Python ``str``,
  so this faithfully exercises the lexer's *logic* against the Python reference,
  including embedded NUL bytes (``"\0"``).
* ``glang-native`` — compile lex_dump to a native binary (also exercises the
  transpiler).  One known divergence: a value containing a NUL byte comes back
  empty, because a compiled Glang string is ``char*`` (NUL-terminated) and
  cannot hold an embedded NUL.
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile

from lexer.token_types import TokenType
from lexer.lexer import Token
from errors.errors import LexError

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_binary: str | None = None


def _build() -> str:
    """Compile + link compiler/lex_dump.lang to a native binary (once)."""
    global _binary
    if _binary is not None:
        return _binary
    workdir = tempfile.mkdtemp(prefix="glang_lex_")
    c_file = os.path.join(workdir, "lex_dump.c")
    binary = os.path.join(workdir, "lex_dump")
    subprocess.run(
        [sys.executable, "main.py", "compile", "compiler/lex_dump.lang", "-o", c_file],
        cwd=_ROOT, check=True, capture_output=True,
    )
    subprocess.run(
        ["gcc", "-w", c_file, "runtime/glang_runtime.c", "-o", binary],
        cwd=_ROOT, check=True, capture_output=True,
    )
    _binary = binary
    return binary


def _decode(s: str) -> str:
    """Reverse compiler/lex_dump.lang's encodeVal: ``%XX`` → that byte."""
    out: list[str] = []
    i = 0
    while i < len(s):
        if s[i] == "%":
            out.append(chr(int(s[i + 1:i + 3], 16)))
            i += 3
        else:
            out.append(s[i])
            i += 1
    return "".join(out)


class GlangLexer:
    """Mimics lexer.lexer.Lexer using the self-hosted lexer as the engine."""

    def __init__(self, source: str) -> None:
        self._source = source

    def tokenize(self) -> list[Token]:
        if os.environ.get("GLANG_LEXER_BACKEND") == "glang-native":
            cmd = [_build()]
        else:
            cmd = [sys.executable, "main.py", "run", "compiler/lex_dump.lang"]
        proc = subprocess.run(
            cmd, input=self._source.encode("utf-8"),
            capture_output=True, cwd=_ROOT,
        )
        out = proc.stdout.decode("utf-8")
        tokens: list[Token] = []
        for line in out.split("\n"):
            if not line:
                continue
            name, enc_value, pos = line.split("\t")
            line_no, col = pos.split(":")
            value = _decode(enc_value)
            if name == "LEXERROR":
                raise LexError(value, int(line_no), int(col))
            tokens.append(Token(TokenType[name], value, int(line_no), int(col)))
        return tokens
