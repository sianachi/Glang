"""Golden-file integration tests for the example programs.

Each ``examples/*.lang`` is run end-to-end and its stdout compared against the
sibling ``examples/*.expected`` file. This shares the exact run logic with the
standalone ``examples/run_examples.py`` harness, so the two never drift.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "Toolchain", "examples"))

from run_examples import discover, expected_path, run_example  # noqa: E402

EXAMPLES = discover()


@pytest.mark.parametrize("lang_path", EXAMPLES, ids=os.path.basename)
def test_example_matches_golden(lang_path):
    exp_path = expected_path(lang_path)
    assert os.path.exists(exp_path), (
        f"missing golden file for {os.path.basename(lang_path)} "
        f"(run: python3 examples/run_examples.py --generate)"
    )
    with open(exp_path, "r", encoding="utf-8") as f:
        expected = f.read()

    _, output = run_example(lang_path)
    produced = "".join(line + "\n" for line in output)
    assert produced == expected


def test_examples_exist():
    # Guard against the directory being empty or the discovery glob breaking.
    assert EXAMPLES, "no example .lang files discovered"
