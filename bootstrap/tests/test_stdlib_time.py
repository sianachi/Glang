"""End-to-end tests for the time builtins and std/time.lang.

Timing is non-deterministic, so tests assert only ordering/sign invariants,
never exact durations.
"""

import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from loader.loader import Loader
from analyser.analyser import Analyser
from interpreter.interpreter import Interpreter


def run_out(src: str):
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "prog.lang")
        with open(path, "w", encoding="utf-8") as f:
            f.write(src)
        program = Loader().load(path)
        env = Analyser().analyse(program)
        interp = Interpreter(env)
        code = interp.run(program)
        return code, interp.output


def test_monotonic_clock_and_elapsed():
    _, out = run_out('import "std/time.lang";\n' + """
    int main() {
        int start = nowNanos();
        int after = nowNanos();
        print(after >= start);            // monotonic
        print(time::elapsedMs(start) >= 0);
        print(time::elapsedUs(start) >= 0);
        return 0;
    }
    """)
    assert out == ["true", "true", "true"]


def test_wall_clock_past_epoch():
    _, out = run_out("""
    int main() {
        print(wallMillis() > 1000000000000);   // well after year 2001
        return 0;
    }
    """)
    assert out == ["true"]


def test_sleep_advances_clock():
    _, out = run_out("""
    int main() {
        int a = nowNanos();
        sleepMs(1);
        int b = nowNanos();
        print(b >= a);
        return 0;
    }
    """)
    assert out == ["true"]
