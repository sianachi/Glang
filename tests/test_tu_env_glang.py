"""Differential test for the self-hosted env-coupled type utilities
(compiler/tu_env.lang).

Runs a line-oriented command script through the Glang driver
(compiler/tu_env_dump.lang) and compares its stdout, line by line, against a
Python reference that drives the real analyser.type_utils functions with the
same commands and a matching GlobalEnv.

Command grammar is documented in compiler/tu_env_dump.lang's header.
"""

import os
import subprocess
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from lexer.lexer import Lexer
from parser.token_stream import TokenStream
from parser.type_parser import TypeParser
from parser.ast_nodes import NamedType
from analyser.symbol_table import GlobalEnv, ClassInfo, InterfaceInfo
from analyser.type_utils import (
    is_assignable, _class_handle_name, superclass_chain, implements_interface,
)

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _parse_type(text: str):
    if text == "null":
        return NamedType("null")
    stream = TokenStream(Lexer(text).tokenize())
    return TypeParser(stream).parse_type()


def _make_class(name, superclass, interfaces):
    return ClassInfo(
        name=name, fields={}, static_fields={}, instance_methods={},
        static_methods={}, vtable={}, constructor=None, destructor=None,
        superclass=superclass, interfaces=interfaces, decl=None, access="public",
    )


def _make_iface(name):
    return InterfaceInfo(name=name, methods={}, decl=None)


def _bool(b):
    return "true" if b else "false"


def py_run(script: str) -> str:
    env = GlobalEnv()
    out = []
    for raw in script.split("\n"):
        line = raw.strip()
        if not line:
            continue
        parts = line.split(" ")
        cmd = parts[0]
        result = ""
        if cmd == "class":
            name = parts[1]
            # Real Python analyser uses None for "no superclass"; the Glang port
            # uses "" as its None-equivalent.  Map "" -> None for the reference.
            superclass = None
            ifaces = []
            i = 2
            while i < len(parts):
                tok = parts[i]
                if tok == "extends" and i + 1 < len(parts):
                    superclass = parts[i + 1]
                elif tok == "implements" and i + 1 < len(parts):
                    ifaces.append(parts[i + 1])
                i += 1
            env.classes[name] = _make_class(name, superclass, ifaces)
            result = "ok"
        elif cmd == "iface":
            env.interfaces[parts[1]] = _make_iface(parts[1])
            result = "ok"
        elif cmd == "is_assignable":
            a = _parse_type(parts[1])
            b = _parse_type(parts[2])
            result = _bool(is_assignable(a, b, env))
        elif cmd == "class_handle_name":
            t = _parse_type(parts[1])
            r = _class_handle_name(t, env)
            result = "" if r is None else r
        elif cmd == "superclass_chain":
            result = " ".join(superclass_chain(parts[1], env))
        elif cmd == "implements_interface":
            result = _bool(implements_interface(parts[1], parts[2], env))
        else:
            result = "ERR:unknown command"
        out.append(line + " | " + result)
    return "\n".join(out)


def glang_run(script: str) -> str:
    proc = subprocess.run(
        [sys.executable, "main.py", "run", "compiler/tu_env_dump.lang"],
        input=script.encode("utf-8"), capture_output=True, cwd=_ROOT,
    )
    return proc.stdout.decode("utf-8").strip()


_HIER = (
    "class Animal\n"
    "class Dog extends Animal\n"
    "class Puppy extends Dog\n"
    "iface Pet\n"
    "iface Swimmer\n"
    "class Cat extends Animal implements Pet\n"
    "class Fish implements Swimmer\n"
)

SCRIPTS = [
    # identical types
    "class Animal\nis_assignable Animal* Animal*\nis_assignable int int\nis_assignable Animal Animal",
    # null -> pointer / fn-ptr / nullable
    "class Animal\nis_assignable null Animal*\nis_assignable null int\nis_assignable null Animal?",
    # T -> T?  (and the non-matching base)
    "class Animal\nis_assignable int int?\nis_assignable bool int?\nis_assignable Animal Animal?",
    # subclass pointer covariance (single + multi-level + reverse fails)
    _HIER + "is_assignable Dog* Animal*\nis_assignable Puppy* Animal*\n"
            "is_assignable Animal* Dog*\nis_assignable Cat* Dog*",
    # interface widening through pointers
    _HIER + "is_assignable Cat* Pet*\nis_assignable Fish* Swimmer*\n"
            "is_assignable Dog* Pet*\nis_assignable Cat* Swimmer*",
    # class value / pointer handle equivalence (Foo vs Foo*) incl. widening
    _HIER + "is_assignable Dog Dog*\nis_assignable Dog* Dog\n"
            "is_assignable Dog Animal*\nis_assignable Cat Pet*\nis_assignable Dog Cat*",
    # class_handle_name: value, pointer, double pointer, non-class, unknown
    _HIER + "class_handle_name Dog\nclass_handle_name Dog*\nclass_handle_name Dog**\n"
            "class_handle_name int\nclass_handle_name Missing*\nclass_handle_name Pet",
    # superclass_chain: single / multi-level / unknown / absent
    _HIER + "superclass_chain Animal\nsuperclass_chain Dog\nsuperclass_chain Puppy\n"
            "superclass_chain Fish\nsuperclass_chain Missing",
    # superclass_chain cycle-safe (A extends B, B extends A)
    "class A extends B\nclass B extends A\nsuperclass_chain A\nsuperclass_chain B",
    # implements_interface: direct / inherited / absent / unknown class
    _HIER + "class Lab extends Cat\n"
            "implements_interface Cat Pet\nimplements_interface Lab Pet\n"
            "implements_interface Dog Pet\nimplements_interface Fish Pet\n"
            "implements_interface Missing Pet",
]


def _norm(text):
    # An empty result yields "<cmd> | " in Python but "<cmd> |" once Glang's
    # output is captured/trimmed; rstrip each line so the empty-result case
    # (class_handle_name of a non-class) compares equal.
    return "\n".join(l.rstrip() for l in text.split("\n"))


@pytest.mark.parametrize("script", SCRIPTS)
def test_tu_env(script):
    assert _norm(glang_run(script)) == _norm(py_run(script))
