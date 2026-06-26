"""Tests for managed memory: `managed class` types and the `T@` handle.

Covers the analyser (type rules, error cases) and the interpreter (runtime
semantics). The native-compiler and self-hosted-interpreter paths are exercised
by the differential parser/analyser suites and the managed_memory example's
golden file; here we pin the reference semantics.
"""

import sys
import os

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from lexer.lexer import Lexer
from parser.parser import Parser
from parser.ast_nodes import ManagedHandleType, NamedType, PointerType
from analyser.analyser import Analyser
from analyser.type_utils import type_str
from errors.errors import TypeError as GTE, ParseError

from tests.test_analyser import analyse, ok, err
from tests.test_interpreter import run, run_out


# --- Parsing / type strings -------------------------------------------------

def test_handle_type_parses():
    src = "managed class N { N() {} } N@ f(N@ x) { return x; }"
    analyse(src)  # no error


def test_handle_type_string():
    from parser.type_parser import TypeParser
    from parser.token_stream import TokenStream
    toks = Lexer("Foo@").tokenize()
    t = TypeParser(TokenStream(toks)).parse_type()
    assert isinstance(t, ManagedHandleType)
    assert type_str(t) == "Foo@"


def test_managed_flag_on_classdecl():
    prog = Parser(Lexer("managed class M { M() {} }").tokenize()).parse()
    cls = prog.declarations[0]
    assert cls.is_managed is True
    prog2 = Parser(Lexer("class P { P() {} }").tokenize()).parse()
    assert prog2.declarations[0].is_managed is False


# --- Analyser: new yields a handle ------------------------------------------

def test_new_managed_yields_handle():
    src = "managed class M { int v; M() { this.v = 1; } } M@ make() { return new M(); }"
    ok(src)


def test_new_managed_not_assignable_to_pointer():
    # A managed `new` is a handle (M@), not a raw pointer (M*).
    err(
        "managed class M { M() {} } void f() { M* p = new M(); }",
        "M*",
    )


def test_handle_requires_managed_class():
    err(
        "class P { P() {} } void f() { P@ x = null; }",
        "requires a managed class",
    )


def test_handle_on_undefined_is_error():
    err("void f() { Bogus@ x = null; }", "unknown type")


# --- Analyser: delete is rejected on handles --------------------------------

def test_delete_handle_rejected():
    err(
        "managed class M { M() {} } void f() { M@ x = new M(); delete x; }",
        "managed handle",
    )


def test_delete_pointer_still_ok():
    ok("class P { P() {} } void f() { P* p = new P(); delete p; }")


# --- Analyser: handles do not mix with pointers -----------------------------

def test_handle_and_pointer_distinct():
    err(
        "managed class M { M() {} } void f() { M@ h = new M(); M* p = h; }",
        "cannot",
    )


def test_handle_null_and_aliasing_typecheck():
    ok(
        "managed class M { int v; M() { this.v = 0; } } "
        "void f() { M@ a = new M(); M@ b = a; b = null; if (a == null) { } }"
    )


# --- Interpreter: runtime semantics -----------------------------------------

def test_interp_fields_and_methods():
    code, out = run_out(
        "managed class C { int v; C(int x) { this.v = x; } int get() { return this.v; } } "
        "int main() { C@ c = new C(42); print(c.get()); print(c.v); return 0; }"
    )
    assert code == 0
    assert out == ["42", "42"]


def test_interp_linked_list_sum():
    code, out = run_out(
        "managed class N { int value; N@ next; N(int v) { this.value = v; this.next = null; } "
        "int sum() { int t = this.value; if (this.next != null) { t = t + this.next.sum(); } return t; } } "
        "int main() { N@ h = new N(1); h.next = new N(2); h.next.next = new N(3); print(h.sum()); return 0; }"
    )
    assert code == 0
    assert out == ["6"]


def test_interp_aliasing():
    code, out = run_out(
        "managed class B { int v; B() { this.v = 0; } } "
        "int main() { B@ a = new B(); B@ b = a; b.v = 9; print(a.v); return 0; }"
    )
    assert code == 0
    assert out == ["9"]


def test_interp_null_handle():
    code, out = run_out(
        "managed class M { M() {} } "
        "int main() { M@ m = null; if (m == null) { print(1); } else { print(0); } return 0; }"
    )
    assert code == 0
    assert out == ["1"]


def test_interp_inheritance_widening():
    code, out = run_out(
        "managed class S { int tag; S() { this.tag = 5; } } "
        "managed class Sq extends S { int side; Sq(int s) : super() { this.side = s; } } "
        "int main() { Sq@ q = new Sq(3); S@ b = q; print(q.side); print(b.tag); return 0; }"
    )
    assert code == 0
    assert out == ["3", "5"]
