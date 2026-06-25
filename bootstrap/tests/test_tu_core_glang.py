"""Differential test for the self-hosted pure type utilities (compiler/tu_core.lang).

For each query script we run the Glang driver (compiler/tu_core_dump.lang) through
the interpreter and compare its output, line-for-line, against a Python reference
that parses the same type annotations (lexer.Lexer + parser.token_stream.TokenStream
+ parser.type_parser.TypeParser) and calls the real analyser.type_utils functions.

Query grammar (one per line, fields separated by '|', whitespace-trimmed):
    types_equal        | <TYPE> | <TYPE>
    type_str           | <TYPE>
    is_nullable        | <TYPE>
    is_numeric         | <TYPE>
    is_integer         | <TYPE>
    is_byte            | <TYPE>
    is_bool            | <TYPE>
    is_string          | <TYPE>
    is_pointer         | <TYPE>
    is_array           | <TYPE>
    is_function_pointer| <TYPE>
    binary_result_type | <OP> | <TYPE> | <TYPE>
    unary_result_type  | <OP> | <TYPE>

The Glang driver prints "true"/"false", the string result, or "ERR" if the
function (or a type parse) throws.  The Python reference mirrors this, mapping the
analyser's TypeError to "ERR".
"""

import os
import subprocess
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from lexer.lexer import Lexer
from parser.token_stream import TokenStream
from parser.type_parser import TypeParser
from errors.errors import TypeError as GlangTypeError
from errors.errors import ParseError as GlangParseError
from errors.errors import LexError as GlangLexError
import analyser.type_utils as tu

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _parse_type(src):
    toks = Lexer(src).tokenize()
    return TypeParser(TokenStream(toks)).parse_type()


def _bool(b):
    return "true" if b else "false"


def py_query(fields):
    """Compute the Python reference result for one query line (list of fields)."""
    op = fields[0]
    try:
        if op == "types_equal":
            return _bool(tu.types_equal(_parse_type(fields[1]), _parse_type(fields[2])))
        if op == "type_str":
            return tu.type_str(_parse_type(fields[1]))
        if op == "is_nullable":
            return _bool(tu.is_nullable(_parse_type(fields[1])))
        if op == "is_numeric":
            return _bool(tu.is_numeric(_parse_type(fields[1])))
        if op == "is_integer":
            return _bool(tu.is_integer(_parse_type(fields[1])))
        if op == "is_byte":
            return _bool(tu.is_byte(_parse_type(fields[1])))
        if op == "is_bool":
            return _bool(tu.is_bool(_parse_type(fields[1])))
        if op == "is_string":
            return _bool(tu.is_string(_parse_type(fields[1])))
        if op == "is_pointer":
            return _bool(tu.is_pointer(_parse_type(fields[1])))
        if op == "is_array":
            return _bool(tu.is_array(_parse_type(fields[1])))
        if op == "is_function_pointer":
            return _bool(tu.is_function_pointer(_parse_type(fields[1])))
        if op == "binary_result_type":
            res = tu.binary_result_type(
                fields[1], _parse_type(fields[2]), _parse_type(fields[3])
            )
            return tu.type_str(res)
        if op == "unary_result_type":
            res = tu.unary_result_type(fields[1], _parse_type(fields[2]))
            return tu.type_str(res)
        return "ERR"
    except (GlangTypeError, GlangParseError, GlangLexError):
        return "ERR"


def py_reference(script):
    out = []
    for line in script.splitlines():
        line = line.strip()
        if not line:
            continue
        fields = [f.strip() for f in line.split("|")]
        out.append(py_query(fields))
    return out


def glang_output(script):
    proc = subprocess.run(
        [sys.executable, "bootstrap/main.py", "run", "Toolchain/compiler/tu_core_dump.lang"],
        input=script.encode("utf-8"), capture_output=True, cwd=_ROOT,
    )
    if proc.returncode != 0:
        raise AssertionError(
            "driver exited %d:\n%s" % (proc.returncode, proc.stderr.decode("utf-8"))
        )
    text = proc.stdout.decode("utf-8")
    return [ln for ln in text.split("\n") if ln.strip() != ""]


# ── Query scripts ─────────────────────────────────────────────────────────────

TYPES = [
    "int", "float", "bool", "char", "byte", "string", "void",
    "Foo", "Foo*", "Foo**", "Foo?", "int[10]", "List<int>",
    "Map<string, int>", "Map<string, List<int>>",
    "fn(int, bool)->void", "fn()->int", "fn(int)->fn(int)->int",
]

ARITH_OPS = ["+", "-", "*", "/", "%"]
CMP_OPS = ["<", ">", "<=", ">="]
EQ_OPS = ["==", "!="]
LOGIC_OPS = ["&&", "||"]
BIT_OPS = ["&", "|", "^", "<<", ">>"]
NUM_TYPES = ["int", "float", "byte", "string", "bool", "Foo*", "Foo"]
UNARY_OPS = ["!", "~", "++", "--", "-", "unary-", "unary+", "?"]


def _predicates_script():
    lines = []
    for pred in ["is_nullable", "is_numeric", "is_integer", "is_byte", "is_bool",
                 "is_string", "is_pointer", "is_array", "is_function_pointer"]:
        for t in TYPES:
            lines.append(f"{pred} | {t}")
    return "\n".join(lines)


def _type_str_script():
    return "\n".join(f"type_str | {t}" for t in TYPES)


def _types_equal_script():
    lines = []
    for a in TYPES:
        for b in TYPES:
            lines.append(f"types_equal | {a} | {b}")
    return "\n".join(lines)


def _binary_script():
    lines = []
    for op in ARITH_OPS + CMP_OPS + EQ_OPS + LOGIC_OPS + BIT_OPS:
        for a in NUM_TYPES:
            for b in NUM_TYPES:
                lines.append(f"binary_result_type | {op} | {a} | {b}")
    # nullable / coalescing
    for a in ["int?", "Foo*", "string?"]:
        for b in ["int", "Foo*", "string", "float"]:
            lines.append(f"binary_result_type | ?? | {a} | {b}")
    # equality class/pointer mixed forms (null is not parseable as a type
    # annotation, so the null-vs-pointer paths can't be exercised here)
    for pair in [("Foo", "Foo*"), ("Foo*", "Foo"), ("Foo", "Bar*"),
                 ("int", "int*"), ("Foo", "Foo")]:
        lines.append(f"binary_result_type | == | {pair[0]} | {pair[1]}")
        lines.append(f"binary_result_type | != | {pair[0]} | {pair[1]}")
    lines.append("binary_result_type | @ | int | int")  # unknown op
    return "\n".join(lines)


def _unary_script():
    lines = []
    for op in UNARY_OPS:
        for t in NUM_TYPES:
            lines.append(f"unary_result_type | {op} | {t}")
    return "\n".join(lines)


SCRIPTS = {
    "predicates": _predicates_script(),
    "type_str": _type_str_script(),
    "types_equal": _types_equal_script(),
    "binary": _binary_script(),
    "unary": _unary_script(),
}


@pytest.mark.parametrize("name", sorted(SCRIPTS))
def test_tu_core_matches_python(name):
    script = SCRIPTS[name]
    expected = py_reference(script)
    actual = glang_output(script)
    assert actual == expected
