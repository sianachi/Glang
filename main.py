#!/usr/bin/env python3
"""Phase 7 — Glang command-line entry point.

Usage:
    glang run <file.lang>

Pipeline: load (resolve imports) -> analyse -> interpret. Any Glang error
(lex/parse/type/runtime/import) is printed to stderr and reported as exit
code 1; a usage error is exit code 2; otherwise the process exits with the
value returned by the program's `main` function.
"""

from __future__ import annotations

import os
import sys

# Allow running as `python main.py ...` from any directory: ensure the project
# root (this file's directory) is importable.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from loader.loader import Loader
from analyser.analyser import Analyser
from interpreter.interpreter import Interpreter
from errors.errors import GlangError

USAGE = "usage: glang run <file.lang> [args...]"


def run_file(path: str, prog_args: list[str] | None = None) -> int:
    """Load, analyse, and execute ``path``; return the program's exit code."""
    program = Loader().load(path)
    env = Analyser().analyse(program)
    interpreter = Interpreter(env, out=sys.stdout, err=sys.stderr, prog_args=prog_args)
    return interpreter.run(program)


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)

    if len(args) < 2 or args[0] != "run":
        print(USAGE, file=sys.stderr)
        return 2

    try:
        return run_file(args[1], prog_args=args[2:])
    except GlangError as err:
        print(f"error: {err}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
