"""Differential test for the self-hosted state-free Pass2 helpers
(compiler/pass2_support.lang).

Runs a line-oriented command script through the Glang driver
(compiler/pass2_support_dump.lang) and compares its stdout, line by line,
against a Python reference that drives the REAL pass2 functions on
analyser.pass2_checker.Pass2Checker with a matching GlobalEnv.

Command grammar is documented in compiler/pass2_support_dump.lang's header.
"""

import os
import subprocess
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from lexer.lexer import Lexer
from parser.token_stream import TokenStream
from parser.type_parser import TypeParser
from parser.ast_nodes import (
    NamedType, CallExpr, LiteralExpr, MethodDecl, Param,
)
from analyser.symbol_table import GlobalEnv, ClassInfo, InterfaceInfo, EnumInfo
from analyser.pass2_checker import Pass2Checker
from analyser.type_utils import type_str
from errors.errors import TypeError as GTypeError

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_BINARY = {"+", "-", "*", "/", "%", "==", "!=", "<", "<=", ">", ">="}
_COMP = {"==", "!=", "<", "<=", ">", ">="}
_ALL = _BINARY | {"[]"}


def _parse_type(text):
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


def _make_enum(name):
    return EnumInfo(name=name, variants={}, decl=None)


def _bool(b):
    return "true" if b else "false"


def _is_overloadable(op):
    return op in _ALL


def _is_comparison(op):
    return op in _COMP


def py_run(script: str) -> str:
    env = GlobalEnv()
    checker = Pass2Checker(env)
    out = []
    for raw in script.split("\n"):
        line = raw.strip()
        if not line:
            continue
        segs = [s.strip() for s in line.split("|")]
        head = segs[0]
        parts = head.split(" ")
        cmd = parts[0]
        result = ""

        if cmd == "enum":
            env.enums[parts[1]] = _make_enum(parts[1])
            result = "ok"
        elif cmd == "iface":
            env.interfaces[parts[1]] = _make_iface(parts[1])
            result = "ok"
        elif cmd == "class":
            name = parts[1]
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
        elif cmd == "validate_cast":
            a = _parse_type(parts[1])
            b = _parse_type(parts[2])
            try:
                checker._validate_cast(a, b, 0, 0)
                result = "ok"
            except GTypeError as e:
                result = "ERR:" + e.msg
        elif cmd == "is_byte_literal":
            e = LiteralExpr("int", parts[1])
            try:
                result = _bool(checker._is_byte_literal(e))
            except GTypeError as ex:
                result = "ERR:" + ex.msg
        elif cmd == "is_overloadable_op":
            result = _bool(_is_overloadable(parts[1]))
        elif cmd == "is_comparison_overload_op":
            result = _bool(_is_comparison(parts[1]))
        elif cmd == "check_builtin_call":
            name = parts[1]
            arg_types = [_parse_type(s) for s in segs[1:] if s]
            args = [LiteralExpr("int", "0") for _ in arg_types]
            expr = CallExpr(name, args)
            # Feed the pre-checked arg types in order.
            it = iter(arg_types)
            checker._check_expr = lambda a, _it=it: next(_it)
            try:
                rt = checker._check_builtin_call(expr)
                result = "none" if rt is None else type_str(rt)
            except GTypeError as e:
                result = "ERR:" + e.msg
            finally:
                del checker._check_expr
        elif cmd == "op_method":
            op = parts[1]
            ret = _parse_type(parts[2])
            nparams = int(parts[3])
            is_static = parts[4] == "1"
            ptype = _parse_type(parts[5])
            owner = parts[6] if len(parts) > 6 else ""
            params = [Param("a%d" % i, ptype) for i in range(nparams)]
            m = MethodDecl("operator" + op, params, ret, None,
                           is_static=is_static, access="public")
            # _check_operator_method_decl reads self._current_class for the
            # owner-class param check; mirror the dump's `owner` string.
            saved = checker._current_class
            checker._current_class = (
                _make_class(owner, None, []) if owner else None
            )
            try:
                checker._check_operator_method_decl(m)
                result = "ok"
            except GTypeError as e:
                result = "ERR:" + e.msg
            finally:
                checker._current_class = saved
        else:
            result = "ERR:unknown command"
        out.append(line + " | " + result)
    return "\n".join(out)


def glang_run(script: str) -> str:
    proc = subprocess.run(
        [sys.executable, "bootstrap/main.py", "run", "Toolchain/compiler/pass2_support_dump.lang"],
        input=script.encode("utf-8"), capture_output=True, cwd=_ROOT,
    )
    return proc.stdout.decode("utf-8").strip()


SCRIPTS = [
    # is_overloadable_op / is_comparison_overload_op
    "is_overloadable_op +\nis_overloadable_op []\nis_overloadable_op ==\n"
    "is_overloadable_op &\nis_overloadable_op <<\nis_overloadable_op foo\n"
    "is_comparison_overload_op ==\nis_comparison_overload_op <\n"
    "is_comparison_overload_op +\nis_comparison_overload_op []",

    # byte literal in / out of range
    "is_byte_literal 0\nis_byte_literal 255\nis_byte_literal 128\n"
    "is_byte_literal 256\nis_byte_literal 300\nis_byte_literal 1000",

    # cast: enum <-> int
    "enum Color\nvalidate_cast Color int\nvalidate_cast int Color\n"
    "validate_cast Color float\nvalidate_cast bool Color",

    # cast: numeric pairs (legal) and illegal numeric
    "validate_cast int float\nvalidate_cast float int\nvalidate_cast int char\n"
    "validate_cast char int\nvalidate_cast int byte\nvalidate_cast byte int\n"
    "validate_cast char byte\nvalidate_cast byte char\nvalidate_cast bool int\n"
    "validate_cast int bool\nvalidate_cast float bool\nvalidate_cast string int",

    # cast: pointer <-> pointer, void*, class*
    "class Animal\nclass Dog extends Animal\n"
    "validate_cast Animal* void*\nvalidate_cast void* Animal*\n"
    "validate_cast Dog* Animal*\nvalidate_cast Animal* Dog*\n"
    "validate_cast int* float*\nvalidate_cast Animal* int\n"
    "validate_cast int Animal*",

    # builtin: print / printErr / len / toString
    "check_builtin_call print | int\ncheck_builtin_call print | string\n"
    "check_builtin_call printErr | bool\n"
    "check_builtin_call len | string\ncheck_builtin_call len | int[4]\n"
    "check_builtin_call toString | float\ncheck_builtin_call toString | char",

    # builtin: print arity + non-primitive errors
    "class Foo\ncheck_builtin_call print\ncheck_builtin_call print | int | int\n"
    "check_builtin_call print | Foo\ncheck_builtin_call len | int\n"
    "check_builtin_call toString | Foo*",

    # builtin: fixed signatures (substr / parse / starts/ends/contains/indexOf)
    "check_builtin_call substr | string | int | int\n"
    "check_builtin_call parseInt | string\ncheck_builtin_call parseFloat | string\n"
    "check_builtin_call startsWith | string | string\n"
    "check_builtin_call endsWith | string | string\n"
    "check_builtin_call contains | string | string\n"
    "check_builtin_call indexOf | string | string",

    # builtin: file IO + byte conv + args + misc
    "check_builtin_call readFile | string\ncheck_builtin_call writeFile | string | string\n"
    "check_builtin_call fileExists | string\n"
    "check_builtin_call bytesFromString | string\n"
    "check_builtin_call stringFromBytes | byte* | int\n"
    "check_builtin_call getArgCount\ncheck_builtin_call getArg | int\n"
    "check_builtin_call exit | int\ncheck_builtin_call intToStr | int\n"
    "check_builtin_call readStdin",

    # builtin: arity / type errors on fixed signatures + non-builtin
    "check_builtin_call substr | string | int\n"
    "check_builtin_call parseInt | int\n"
    "check_builtin_call getArgCount | int\n"
    "check_builtin_call notabuiltin | int\n"
    "check_builtin_call alsoNot",

    # operator method shape: valid binary + valid comparison + valid []
    "op_method + Foo 1 0 Foo Foo\nop_method == bool 1 0 Foo Foo\n"
    "op_method [] int 1 0 int Foo",

    # operator method shape: each violation
    "op_method foo int 1 0 Foo Foo\n"        # unsupported op
    "op_method + int 1 1 Foo Foo\n"          # static
    "op_method + int 0 0 Foo Foo\n"          # wrong param count
    "op_method + int 2 0 Foo Foo\n"          # wrong param count
    "op_method + void 1 0 Foo Foo\n"         # must return value
    "op_method == int 1 0 Foo Foo\n"         # comparison must return bool
    "op_method + int 1 0 Bar Foo",           # param must be owner class

    # operator method: no owner class -> param check skipped
    "op_method + int 1 0 Bar\nop_method [] int 1 0 Whatever",

    # valid binary again (sanity)
    "op_method - Foo 1 0 Foo Foo",
]


def _norm(text):
    return "\n".join(l.rstrip() for l in text.split("\n"))


@pytest.mark.parametrize("script", SCRIPTS)
def test_pass2_support(script):
    assert _norm(glang_run(script)) == _norm(py_run(script))
