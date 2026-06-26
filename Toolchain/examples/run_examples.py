#!/usr/bin/env python3
"""Golden-file harness for the Glang example programs.

Each ``Toolchain/examples/*.lang`` is run through the Python reference
front-end + interpreter (the same path as ``bootstrap/main.py run``) and its
captured stdout lines are compared against the sibling
``Toolchain/examples/expected/<name>.expected`` file.

``bootstrap/tests/test_examples.py`` imports ``discover``, ``expected_path`` and
``run_example`` from here so the test suite and this standalone CLI never drift.

Usage:
    python3 Toolchain/examples/run_examples.py            # check against goldens
    python3 Toolchain/examples/run_examples.py --generate # (re)write goldens
"""

from __future__ import annotations

import glob
import io
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))                  # .../Toolchain/examples
_TOOLCHAIN = os.path.dirname(_HERE)                                 # .../Toolchain
_REPO = os.path.dirname(_TOOLCHAIN)                                 # repo root
_BOOTSTRAP = os.path.join(_REPO, "bootstrap")                       # Python reference

# Make the reference packages importable and point the loader at the stdlib,
# whether invoked via pytest or directly from any working directory.
if _BOOTSTRAP not in sys.path:
    sys.path.insert(0, _BOOTSTRAP)
os.environ.setdefault("GLANG_STDLIB", os.path.join(_TOOLCHAIN, "stdlib"))

from loader.loader import Loader            # noqa: E402
from analyser.analyser import Analyser      # noqa: E402
from interpreter.interpreter import Interpreter  # noqa: E402

_EXPECTED_DIR = os.path.join(_HERE, "expected")


def discover() -> list[str]:
    """All example program paths, sorted for stable test ids."""
    return sorted(glob.glob(os.path.join(_HERE, "*.lang")))


def expected_path(lang_path: str) -> str:
    """The golden file path for a given example."""
    stem = os.path.splitext(os.path.basename(lang_path))[0]
    return os.path.join(_EXPECTED_DIR, stem + ".expected")


def run_example(lang_path: str) -> tuple[int, list[str]]:
    """Load, analyse, and interpret ``lang_path`` with empty stdin.

    Returns ``(exit_code, output_lines)`` where ``output_lines`` are the
    ``print`` lines (without trailing newlines).
    """
    program = Loader().load(lang_path)
    env = Analyser().analyse(program)
    interp = Interpreter(env)
    saved_stdin = sys.stdin
    sys.stdin = io.StringIO("")          # examples get a deterministic empty stdin
    try:
        code = interp.run(program)
    finally:
        sys.stdin = saved_stdin
    return code, interp.output


def _golden_text(output: list[str]) -> str:
    return "".join(line + "\n" for line in output)


def _generate() -> int:
    os.makedirs(_EXPECTED_DIR, exist_ok=True)
    for lang in discover():
        _, output = run_example(lang)
        with open(expected_path(lang), "w", encoding="utf-8") as f:
            f.write(_golden_text(output))
        print(f"wrote {os.path.relpath(expected_path(lang), _REPO)}")
    return 0


def _check() -> int:
    failures = 0
    for lang in discover():
        exp = expected_path(lang)
        name = os.path.basename(lang)
        if not os.path.exists(exp):
            print(f"MISSING golden: {name}")
            failures += 1
            continue
        with open(exp, "r", encoding="utf-8") as f:
            expected = f.read()
        try:
            _, output = run_example(lang)
        except Exception as e:  # noqa: BLE001 — report which example blew up
            print(f"ERROR {name}: {e}")
            failures += 1
            continue
        if _golden_text(output) != expected:
            print(f"MISMATCH {name}")
            failures += 1
        else:
            print(f"ok {name}")
    return 1 if failures else 0


def main(argv: list[str]) -> int:
    if "--generate" in argv:
        return _generate()
    return _check()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
