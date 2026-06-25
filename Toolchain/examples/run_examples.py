#!/usr/bin/env python3
"""Run every example program and check its output against a golden file.

Each ``examples/<name>.lang`` has a golden file ``examples/expected/<name>.expected``
holding the exact stdout the program should produce. This runner executes each example
end-to-end (load → analyse → interpret) in a throwaway working directory — so
examples that touch the filesystem stay self-contained — and diffs the captured
output against the golden file.

Usage:
    python3 examples/run_examples.py            # check all examples
    python3 examples/run_examples.py --generate # (re)write the .expected files

This is an integration harness, intentionally separate from the unit tests in
tests/. ``tests/test_examples.py`` runs the same examples under pytest.
"""

from __future__ import annotations

import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "bootstrap"))

from loader.loader import Loader
from analyser.analyser import Analyser
from interpreter.interpreter import Interpreter

EXAMPLES_DIR = os.path.dirname(os.path.abspath(__file__))
EXPECTED_DIR = os.path.join(EXAMPLES_DIR, "expected")


def discover() -> list[str]:
    return sorted(
        os.path.join(EXAMPLES_DIR, f)
        for f in os.listdir(EXAMPLES_DIR)
        if f.endswith(".lang")
    )


def expected_path(lang_path: str) -> str:
    name = os.path.basename(lang_path)[: -len(".lang")]
    return os.path.join(EXPECTED_DIR, name + ".expected")


def run_example(lang_path: str) -> tuple[int, list[str]]:
    """Execute one example in a scratch working directory; return its exit code
    and the list of printed lines."""
    program = Loader().load(lang_path)
    env = Analyser().analyse(program)
    interp = Interpreter(env)
    cwd = os.getcwd()
    with tempfile.TemporaryDirectory() as scratch:
        os.chdir(scratch)
        try:
            code = interp.run(program)
        finally:
            os.chdir(cwd)
    return code, interp.output


def main(argv: list[str]) -> int:
    generate = "--generate" in argv
    if generate:
        os.makedirs(EXPECTED_DIR, exist_ok=True)
    failures = 0
    for lang_path in discover():
        name = os.path.basename(lang_path)
        try:
            _, output = run_example(lang_path)
        except Exception as e:  # a crash is always a failure
            print(f"FAIL {name}: {type(e).__name__}: {e}")
            failures += 1
            continue

        produced = "".join(line + "\n" for line in output)
        exp_path = expected_path(lang_path)

        if generate:
            with open(exp_path, "w", encoding="utf-8") as f:
                f.write(produced)
            print(f"wrote {os.path.basename(exp_path)}")
            continue

        if not os.path.exists(exp_path):
            print(f"FAIL {name}: no .expected file (run with --generate)")
            failures += 1
            continue
        with open(exp_path, "r", encoding="utf-8") as f:
            expected = f.read()
        if produced == expected:
            print(f"ok   {name}")
        else:
            print(f"FAIL {name}: output mismatch")
            print(f"  expected: {expected!r}")
            print(f"  produced: {produced!r}")
            failures += 1

    if not generate and failures:
        print(f"\n{failures} example(s) failed")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
