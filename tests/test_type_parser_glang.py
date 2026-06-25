"""Differential test for the self-hosted type parser (compiler/type_parser.lang).

For each type annotation, parse it with both the Python TypeParser and the Glang
one (via compiler/type_dump.lang, run through the interpreter) and assert the
canonical forms agree.  The Python canonical form is ast_serializer._type_str,
which compiler/ast.lang::showType is written to match exactly.
"""

import os
import subprocess
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from lexer.lexer import Lexer
from parser.token_stream import TokenStream
from parser.type_parser import TypeParser
from compiler.ast_serializer import _type_str

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

TYPES = [
    "int", "float", "bool", "char", "byte", "string", "void",
    "Foo", "Foo*", "Foo**", "Foo***",
    "Foo?", "int[10]", "int[256]",
    "List<int>", "Map<string, int>", "Map<string, List<int>>",
    "List<List<List<int>>>", "Map<string, Map<int, bool>>",
    "Foo<int>*", "List<Foo*>", "List<Foo*>*",
    "a::b::C", "a::b::C<int>", "ns::List<ns::Item>**",
    "fn(int, bool)->void", "fn()->int", "fn(int)->fn(int)->int",
    "fn(List<int>, string)->Map<string, int>",
    "Node*[8]",
]


def py_canonical(src: str) -> str:
    toks = Lexer(src).tokenize()
    return _type_str(TypeParser(TokenStream(toks)).parse_type())


def glang_canonical(src: str) -> str:
    proc = subprocess.run(
        [sys.executable, "main.py", "run", "compiler/type_dump.lang"],
        input=src.encode("utf-8"), capture_output=True, cwd=_ROOT,
    )
    return proc.stdout.decode("utf-8").strip()


@pytest.mark.parametrize("src", TYPES)
def test_type_matches_python(src):
    assert glang_canonical(src) == py_canonical(src)
