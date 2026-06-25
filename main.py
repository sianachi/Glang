#!/usr/bin/env python3
"""Glang command-line entry point.

Usage:
    glang run     <file.lang> [args...]
    glang compile <file.lang> [-o output.c]

Pipeline: load (resolve imports) -> analyse -> interpret/transpile.
Any Glang error is printed to stderr and reported as exit code 1;
a usage error is exit code 2; otherwise exits with main()'s return value.
"""

from __future__ import annotations

import os
import sys
import tempfile

# Allow running as `python main.py ...` from any directory.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from glang_loader.loader import Loader
from analyser.analyser import Analyser
from interpreter.interpreter import Interpreter
from errors.errors import GlangError

USAGE = (
    "usage:\n"
    "  glang run     <file.lang> [args...]\n"
    "  glang compile <file.lang> [-o output.c]"
)

_ROOT = os.path.dirname(os.path.abspath(__file__))


def run_file(path: str, prog_args: list[str] | None = None) -> int:
    """Load, analyse, and execute ``path``; return the program's exit code."""
    program = Loader().load(path)
    env = Analyser().analyse(program)
    interpreter = Interpreter(env, out=sys.stdout, err=sys.stderr, prog_args=prog_args)
    return interpreter.run(program)


def compile_file(path: str, out_c: str) -> int:
    """Load, analyse, serialise, and transpile ``path`` to C at ``out_c``."""
    from compiler.ast_serializer import serialize

    program = Loader().load(path)
    env = Analyser().analyse(program)
    ast_text = serialize(program, env)

    with tempfile.NamedTemporaryFile(
        mode='w', suffix='.glast', delete=False, encoding='utf-8'
    ) as f:
        f.write(ast_text)
        ast_file = f.name

    transpiler = os.path.join(_ROOT, 'compiler', 'transpiler.lang')
    try:
        return run_file(transpiler, prog_args=[ast_file, out_c])
    finally:
        try:
            os.unlink(ast_file)
        except OSError:
            pass


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)

    if len(args) < 1:
        print(USAGE, file=sys.stderr)
        return 2

    cmd = args[0]

    if cmd == 'run':
        if len(args) < 2:
            print(USAGE, file=sys.stderr)
            return 2
        try:
            return run_file(args[1], prog_args=args[2:])
        except GlangError as err:
            print(f"error: {err}", file=sys.stderr)
            return 1

    elif cmd == 'compile':
        if len(args) < 2:
            print(USAGE, file=sys.stderr)
            return 2
        src = args[1]
        out_c = src.replace('.lang', '.c') if src.endswith('.lang') else src + '.c'
        # parse optional -o flag
        i = 2
        while i < len(args):
            if args[i] == '-o' and i + 1 < len(args):
                out_c = args[i + 1]
                i += 2
            else:
                i += 1
        try:
            return compile_file(src, out_c)
        except GlangError as err:
            print(f"error: {err}", file=sys.stderr)
            return 1

    else:
        print(USAGE, file=sys.stderr)
        return 2


if __name__ == "__main__":
    import threading
    _result = [2]
    def _run() -> None:
        _result[0] = main()
    # 64 MB stack — prevents C stack overflow in Cython-compiled recursive modules
    threading.stack_size(64 * 1024 * 1024)
    t = threading.Thread(target=_run)
    t.start()
    t.join()
    sys.exit(_result[0])
