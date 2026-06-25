"""Differential test for the self-hosted symbol table (compiler/symtab.lang).

Runs a line-oriented command script through the Glang driver
(compiler/symtab_dump.lang) and compares its stdout, line by line, against a
Python reference that drives the real analyser.symbol_table.SymbolTable /
GlobalEnv with the same commands.

Command grammar is documented in compiler/symtab_dump.lang's header.
"""

import os
import subprocess
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from lexer.lexer import Lexer
from parser.token_stream import TokenStream
from parser.type_parser import TypeParser
from analyser.symbol_table import (
    SymbolTable, GlobalEnv, ClassInfo, EnumInfo, UnionInfo,
)
from compiler.ast_serializer import _type_str
from errors.errors import TypeError as GTE

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _parse_type(text: str):
    stream = TokenStream(Lexer(text).tokenize())
    return TypeParser(stream).parse_type()


def _make_class(name: str, superclass: str | None):
    return ClassInfo(
        name=name, fields={}, static_fields={}, instance_methods={},
        static_methods={}, vtable={}, constructor=None, destructor=None,
        superclass=superclass, interfaces=[], decl=None, access="public",
    )


def _bool(b):
    return "true" if b else "false"


def py_run(script: str) -> str:
    """Python reference: drive the real SymbolTable/GlobalEnv, mirror the driver."""
    env = GlobalEnv()
    scope = SymbolTable(None)
    out = []
    for raw in script.split("\n"):
        line = raw.strip()
        if not line:
            continue
        parts = line.split(" ")
        cmd = parts[0]
        result = ""
        if cmd == "register_class":
            name = parts[1]
            superclass = parts[3] if len(parts) >= 4 and parts[2] == "extends" else ""
            env.classes[name] = _make_class(name, superclass)
            result = "ok"
        elif cmd == "register_enum":
            env.enums[parts[1]] = EnumInfo(name=parts[1], variants={}, decl=None)
            result = "ok"
        elif cmd == "register_union":
            env.unions[parts[1]] = UnionInfo(
                name=parts[1], type_params=[], variants={}, decl=None)
            result = "ok"
        elif cmd == "define":
            name = parts[1]
            is_const = len(parts) >= 4 and parts[3] == "const"
            try:
                ty = _parse_type(parts[2])
                scope.define(name, ty, 0, 0, is_const)
                result = "ok"
            except GTE as e:
                result = "ERR:" + e.msg
        elif cmd == "lookup":
            try:
                result = _type_str(scope.lookup(parts[1]))
            except GTE as e:
                result = "ERR:" + e.msg
        elif cmd == "lookup_local":
            ty = scope.lookup_local(parts[1])
            result = "null" if ty is None else _type_str(ty)
        elif cmd == "is_const_var":
            result = _bool(scope.is_const_var(parts[1]))
        elif cmd == "find_scope":
            result = "null" if scope.find_scope(parts[1]) is None else "found"
        elif cmd == "push":
            scope = scope.child()
            result = "ok"
        elif cmd == "pop":
            if scope._parent is None:
                result = "ERR:pop at root"
            else:
                scope = scope._parent
                result = "ok"
        elif cmd == "is_class":
            result = _bool(env.is_class(parts[1]))
        elif cmd == "is_interface":
            result = _bool(env.is_interface(parts[1]))
        elif cmd == "is_enum":
            result = _bool(env.is_enum(parts[1]))
        elif cmd == "is_union":
            result = _bool(env.is_union(parts[1]))
        elif cmd == "is_primitive":
            result = _bool(env.is_primitive(parts[1]))
        elif cmd == "resolve_type":
            try:
                env.resolve_type(_parse_type(parts[1]))
                result = "ok"
            except GTE as e:
                result = "ERR:" + e.msg
        elif cmd == "is_descendant_of":
            root = SymbolTable(None)
            a = root.child()
            b = a.child()
            result = "B<root:%s B<A:%s root<B:%s" % (
                _bool(b.is_descendant_of(root)),
                _bool(b.is_descendant_of(a)),
                _bool(root.is_descendant_of(b)),
            )
        else:
            result = "ERR:unknown command"
        out.append(line + " | " + result)
    return "\n".join(out)


def glang_run(script: str) -> str:
    proc = subprocess.run(
        [sys.executable, "main.py", "run", "compiler/symtab_dump.lang"],
        input=script.encode("utf-8"), capture_output=True, cwd=_ROOT,
    )
    return proc.stdout.decode("utf-8").strip()


SCRIPTS = [
    # define / lookup / shadow-in-child
    "define x int\nlookup x\nlookup_local x\ndefine x bool",
    "define x int\npush\ndefine x bool\nlookup x\nlookup_local x\npop\nlookup x",
    # find_scope
    "define x int\npush\nfind_scope x\nfind_scope y\npop\nfind_scope x",
    # is_const_var
    "define x int const\ndefine y float\nis_const_var x\nis_const_var y\nis_const_var z",
    # undefined lookup error message
    "lookup nope",
    # is_descendant_of (true and false in one probe)
    "is_descendant_of",
    # all is_* predicates over a populated env
    ("register_class Dog extends Animal\nregister_class Animal\nregister_enum Color\n"
     "register_union Opt\nis_class Dog\nis_class Missing\nis_interface Dog\n"
     "is_enum Color\nis_enum Dog\nis_union Opt\nis_union Color\n"
     "is_primitive int\nis_primitive float\nis_primitive bool\nis_primitive char\n"
     "is_primitive byte\nis_primitive string\nis_primitive void\nis_primitive Dog"),
    # resolve_type: primitive / class / enum / union / pointer / unknown / generic
    ("register_class Dog\nregister_enum Color\nregister_union Opt\n"
     "resolve_type int\nresolve_type Dog\nresolve_type Color\nresolve_type Opt\n"
     "resolve_type Dog*\nresolve_type Dog**\nresolve_type int[4]\n"
     "resolve_type fn(int,Dog*)->bool\n"
     "resolve_type Nope\nresolve_type Opt<int>"),
    # nested pointer/array to unknown reports the unknown base
    "resolve_type Missing*\nresolve_type Missing[3]",
    # pop at root edge
    "pop",
    # const flag survives across child lookup
    "define c int const\npush\nis_const_var c\nlookup c\npop",
]


@pytest.mark.parametrize("script", SCRIPTS)
def test_symtab(script):
    assert glang_run(script) == py_run(script)
