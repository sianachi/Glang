#!/usr/bin/env python3
"""Glang command-line entry point.

Usage:
    glang run     <file.lang> [args...]
    glang compile <file.lang> [-o output.c]

`run` interprets via the Python reference front-end + interpreter.
`compile` is pure GScript: it builds the self-hosted `glangc` (from the
committed `glangc.c` seed) and uses it to emit C — no Python front-end involved.

Any Glang error is printed to stderr and reported as exit code 1;
a usage error is exit code 2; otherwise exits with main()'s return value.
"""

from __future__ import annotations

import os
import subprocess
import sys

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

_ROOT = os.path.dirname(os.path.abspath(__file__))          # .../bootstrap
_REPO = os.path.dirname(_ROOT)                               # repo root
_TOOLCHAIN = os.path.join(_REPO, 'Toolchain')                # GScript toolchain

# The GScript stdlib/runtime live under Toolchain/; make the loader find them.
os.environ.setdefault('GLANG_STDLIB', os.path.join(_TOOLCHAIN, 'stdlib'))


def run_file(path: str, prog_args: list[str] | None = None) -> int:
    """Load, analyse, and execute ``path``; return the program's exit code."""
    program = Loader().load(path)
    env = Analyser().analyse(program)
    interpreter = Interpreter(env, out=sys.stdout, err=sys.stderr, prog_args=prog_args)
    return interpreter.run(program)


def _ensure_glangc() -> str:
    """Build (if missing/stale) and return the path to the native ``glangc``.

    Bootstraps from the committed ``glangc.c`` seed — no Python front-end.
    """
    glangc = os.path.join(_TOOLCHAIN, 'glangc')
    seed = os.path.join(_TOOLCHAIN, 'glangc.c')
    runtime = os.path.join(_TOOLCHAIN, 'runtime', 'glang_runtime.c')
    if not os.path.exists(seed):
        raise FileNotFoundError(
            "Toolchain/glangc.c seed not found; run Toolchain/build.sh"
        )
    stale = (not os.path.exists(glangc)
             or os.path.getmtime(glangc) < os.path.getmtime(seed))
    if stale:
        subprocess.run(['gcc', '-O1', '-w', seed, runtime, '-o', glangc],
                       cwd=_TOOLCHAIN, check=True)
    return glangc


def compile_file(path: str, out_c: str) -> int:
    """Compile ``path`` to C at ``out_c`` using the self-hosted ``glangc``.

    glangc runs with cwd=Toolchain/ so its ``std/...`` imports resolve against
    Toolchain/stdlib; input/output are passed as absolute paths.
    """
    glangc = _ensure_glangc()
    return subprocess.run(
        [glangc, os.path.abspath(path), os.path.abspath(out_c)],
        cwd=_TOOLCHAIN,
    ).returncode


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
