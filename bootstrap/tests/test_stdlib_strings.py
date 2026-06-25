"""Tests for the extended strings namespace (std/string.lang)."""
import sys, os, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from loader.loader import Loader
from analyser.analyser import Analyser
from interpreter.interpreter import Interpreter
from errors.errors import TypeError as GTE


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


def ok(src: str):
    run_out(src)


def err(src: str, fragment: str):
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "prog.lang")
        with open(path, "w", encoding="utf-8") as f:
            f.write(src)
        prog = Loader().load(path)
        with pytest.raises(GTE, match=fragment):
            Analyser().analyse(prog)


_PRE = 'import "std/string.lang";'


def main(body: str, preamble: str = _PRE) -> str:
    return f"{preamble}\nint main() {{\n{body}\nreturn 0;\n}}"


# ---------------------------------------------------------------------------
# strings::indexOf (char version)
# ---------------------------------------------------------------------------

class TestIndexOf:
    def test_found(self):
        _, out = run_out(main('print(strings::indexOf("hello", \'l\'));'))
        assert out == ["2"]

    def test_not_found(self):
        _, out = run_out(main('print(strings::indexOf("hello", \'z\'));'))
        assert out == ["-1"]

    def test_first_occurrence(self):
        _, out = run_out(main('print(strings::indexOf("abab", \'b\'));'))
        assert out == ["1"]

    def test_empty_string(self):
        _, out = run_out(main('print(strings::indexOf("", \'a\'));'))
        assert out == ["-1"]


# ---------------------------------------------------------------------------
# strings::substring
# ---------------------------------------------------------------------------

class TestSubstring:
    def test_basic(self):
        _, out = run_out(main('print(strings::substring("hello world", 6, 5));'))
        assert out == ["world"]

    def test_from_start(self):
        _, out = run_out(main('print(strings::substring("abcdef", 0, 3));'))
        assert out == ["abc"]

    def test_length_zero(self):
        _, out = run_out(main('print(strings::substring("hello", 2, 0));'))
        assert out == [""]


# ---------------------------------------------------------------------------
# strings::padRight
# ---------------------------------------------------------------------------

class TestPadRight:
    def test_pads_with_spaces(self):
        _, out = run_out(main("print(strings::padRight(\"hi\", 5, ' '));"))
        assert out == ["hi   "]

    def test_pads_with_char(self):
        _, out = run_out(main("print(strings::padRight(\"a\", 4, '.'));"))
        assert out == ["a..."]

    def test_no_pad_needed(self):
        _, out = run_out(main("print(strings::padRight(\"hello\", 3, ' '));"))
        assert out == ["hello"]


# ---------------------------------------------------------------------------
# strings::intToStr
# ---------------------------------------------------------------------------

class TestIntToStr:
    def test_zero(self):
        _, out = run_out(main('print(strings::intToStr(0));'))
        assert out == ["0"]

    def test_positive(self):
        _, out = run_out(main('print(strings::intToStr(12345));'))
        assert out == ["12345"]

    def test_negative(self):
        _, out = run_out(main('print(strings::intToStr(-42));'))
        assert out == ["-42"]

    def test_single_digit(self):
        _, out = run_out(main('print(strings::intToStr(7));'))
        assert out == ["7"]


# ---------------------------------------------------------------------------
# strings::charToStr
# ---------------------------------------------------------------------------

class TestCharToStr:
    def test_basic(self):
        _, out = run_out(main("print(strings::charToStr('A'));"))
        assert out == ["A"]

    def test_digit_char(self):
        _, out = run_out(main("print(strings::charToStr('9'));"))
        assert out == ["9"]


# ---------------------------------------------------------------------------
# strings::split
# ---------------------------------------------------------------------------

class TestSplit:
    def test_simple(self):
        _, out = run_out(main("""\
List<string> parts = strings::split("a,b,c", ',');
print(parts.length());
print(parts.get(0));
print(parts.get(1));
print(parts.get(2));
"""))
        assert out == ["3", "a", "b", "c"]

    def test_no_delimiter(self):
        _, out = run_out(main("""\
List<string> parts = strings::split("hello", ',');
print(parts.length());
print(parts.get(0));
"""))
        assert out == ["1", "hello"]

    def test_adjacent_delimiters(self):
        _, out = run_out(main("""\
List<string> parts = strings::split("a,,b", ',');
print(parts.length());
print(parts.get(1));
"""))
        assert out == ["3", ""]

    def test_empty_string(self):
        _, out = run_out(main("""\
List<string> parts = strings::split("", ',');
print(parts.length());
"""))
        assert out == ["1"]


# ---------------------------------------------------------------------------
# strings::join
# ---------------------------------------------------------------------------

class TestJoin:
    def test_basic(self):
        _, out = run_out(main("""\
List<string> parts = strings::split("hello world", ' ');
print(strings::join(parts, "-"));
"""))
        assert out == ["hello-world"]

    def test_empty_sep(self):
        _, out = run_out(main("""\
List<string> parts = strings::split("abc", ',');
print(strings::join(parts, ""));
"""))
        assert out == ["abc"]

    def test_single_element(self):
        _, out = run_out(main("""\
List<string> parts = List<string>();
parts.add("only");
print(strings::join(parts, ", "));
"""))
        assert out == ["only"]


# ---------------------------------------------------------------------------
# intToStr builtin (global)
# ---------------------------------------------------------------------------

class TestIntToStrBuiltin:
    def test_positive(self):
        _, out = run_out(main('print(intToStr(999));', preamble=""))
        assert out == ["999"]

    def test_negative(self):
        _, out = run_out(main('print(intToStr(-1));', preamble=""))
        assert out == ["-1"]

    def test_zero(self):
        _, out = run_out(main('print(intToStr(0));', preamble=""))
        assert out == ["0"]
