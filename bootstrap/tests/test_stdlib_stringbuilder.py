"""Tests for StringBuilder (std/stringbuilder.lang)."""
import sys, os, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from loader.loader import Loader
from analyser.analyser import Analyser
from interpreter.interpreter import Interpreter

_PRE = 'import "std/stringbuilder.lang";'


def run_out(src: str):
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "prog.lang")
        with open(path, "w", encoding="utf-8") as f:
            f.write(src)
        prog = Loader().load(path)
        env = Analyser().analyse(prog)
        interp = Interpreter(env)
        code = interp.run(prog)
        return code, interp.output


def main(body: str) -> str:
    return f"{_PRE}\nint main() {{\n{body}\nreturn 0;\n}}"


class TestStringBuilderBasic:
    def test_empty_build(self):
        _, out = run_out(main("""\
StringBuilder sb = StringBuilder();
print(sb.build());
print(sb.length());
"""))
        assert out == ["", "0"]

    def test_append_strings(self):
        _, out = run_out(main("""\
StringBuilder sb = StringBuilder();
sb.append("hello");
sb.append(", ");
sb.append("world");
print(sb.build());
"""))
        assert out == ["hello, world"]

    def test_append_char(self):
        _, out = run_out(main("""\
StringBuilder sb = StringBuilder();
sb.append("ab");
sb.appendChar('c');
print(sb.build());
"""))
        assert out == ["abc"]

    def test_append_int(self):
        _, out = run_out(main("""\
StringBuilder sb = StringBuilder();
sb.append("count=");
sb.appendInt(42);
print(sb.build());
"""))
        assert out == ["count=42"]

    def test_append_int_negative(self):
        _, out = run_out(main("""\
StringBuilder sb = StringBuilder();
sb.appendInt(-7);
print(sb.build());
"""))
        assert out == ["-7"]

    def test_append_line(self):
        _, out = run_out(main("""\
StringBuilder sb = StringBuilder();
sb.appendLine("first");
sb.append("second");
string s = sb.build();
print(len(s));
"""))
        # "first\nsecond" = 12 chars
        assert out == ["12"]

    def test_length(self):
        _, out = run_out(main("""\
StringBuilder sb = StringBuilder();
sb.append("abc");
sb.appendChar('d');
print(sb.length());
"""))
        assert out == ["4"]

    def test_clear(self):
        _, out = run_out(main("""\
StringBuilder sb = StringBuilder();
sb.append("hello");
sb.clear();
print(sb.length());
print(sb.build());
"""))
        assert out == ["0", ""]

    def test_reuse_after_clear(self):
        _, out = run_out(main("""\
StringBuilder sb = StringBuilder();
sb.append("first");
sb.clear();
sb.append("second");
print(sb.build());
"""))
        assert out == ["second"]


class TestStringBuilderLoop:
    def test_build_csv_row(self):
        _, out = run_out(main("""\
StringBuilder sb = StringBuilder();
int n = 5;
for (int i = 0; i < n; ++i) {
    if (i > 0) { sb.append(","); }
    sb.appendInt(i * i);
}
print(sb.build());
"""))
        assert out == ["0,1,4,9,16"]
