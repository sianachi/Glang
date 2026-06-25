"""Differential test for the self-hosted return checker (compiler/retcheck.lang).

For each top-level FunctionDecl and each class MethodDecl (with a body), both
the Python reference (analyser.return_checker.always_returns) and the Glang
driver (compiler/retcheck_dump.lang, via the interpreter) emit one line:

    <name> | <true|false>

The per-line lists (in declaration order) must agree exactly.

Inputs: targeted snippets covering every all-paths-return rule, plus every
function/method in a selection of examples/*.lang and stdlib/*.lang files.
"""

import glob
import os
import subprocess
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from lexer.lexer import Lexer
from parser.parser import Parser
from parser import ast_nodes as A
from analyser.return_checker import always_returns

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _body_stmts(body):
    if isinstance(body, A.Block):
        return body.stmts
    return [body]


def py_lines(src: str) -> str:
    """Reference: parse with the Python parser, walk fns/methods, emit lines."""
    prog = Parser(Lexer(src).tokenize()).parse()
    out = []
    for d in prog.declarations:
        if isinstance(d, A.FunctionDecl):
            out.append(f"{d.name} | {'true' if always_returns(_body_stmts(d.body)) else 'false'}")
        elif isinstance(d, A.ClassDecl):
            for m in d.methods:
                if m.body is not None:
                    out.append(f"{m.name} | {'true' if always_returns(_body_stmts(m.body)) else 'false'}")
    return "\n".join(out)


def glang_lines(src: str) -> str:
    proc = subprocess.run(
        [sys.executable, "main.py", "run", "compiler/retcheck_dump.lang"],
        input=src.encode("utf-8"), capture_output=True, cwd=_ROOT,
    )
    if proc.returncode != 0:
        raise AssertionError(
            "driver failed:\n" + proc.stdout.decode() + proc.stderr.decode()
        )
    return proc.stdout.decode("utf-8").strip()


SNIPPETS = [
    # bare return / no return
    "int f() { return 1; }",
    "void f() { g(); }",
    "void f() { }",
    # if without else -> false; if/else both return -> true
    "int f() { if (a) { return 1; } }",
    "int f() { if (a) { return 1; } else { return 2; } }",
    "int f() { if (a) { g(); } else { return 2; } }",
    # else-if chains
    "int f() { if (a) { return 1; } else if (b) { return 2; } else { return 3; } }",
    "int f() { if (a) { return 1; } else if (b) { return 2; } }",
    # loops never count as always-return
    "int f() { while (x) { return 1; } }",
    "int f() { do { return 1; } while (x); }",
    "int f() { for (int i = 0; i < n; ++i) { return 1; } }",
    "int f() { foreach (int v in xs) { return 1; } }",
    # throw counts as returning
    "int f() { throw new Error(m); }",
    # try/catch: body and all catches must return
    "int f() { try { return 1; } catch (Error* e) { return 2; } }",
    "int f() { try { return 1; } catch (Error* e) { g(); } }",
    "int f() { try { g(); } catch (Error* e) { return 2; } }",
    "int f() { try { return 1; } catch (A* e) { return 2; } catch (B* e) { return 3; } }",
    "int f() { try { return 1; } catch (A* e) { return 2; } catch (B* e) { g(); } }",
    # match: all arms must return
    "int f() { match (*e) { Expr.Num(v) => { return v; } _ => { return 0; } } }",
    "int f() { match (*e) { Expr.Num(v) => { return v; } _ => { g(); } } }",
    # using delegates to its body
    "int f() { using (File* h = open(p)) { return 1; } }",
    "int f() { using (File* h = open(p)) { g(); } }",
    # nested block
    "int f() { { return 1; } }",
    "int f() { { g(); } }",
    # trailing return after a non-returning if
    "int f() { if (a) { g(); } return 1; }",
    # methods inside a class (ctor must precede methods per the parser)
    "class C { C() { x(); } int m() { return 9; } void n() { g(); } "
    "int q() { if (a) { return 1; } else { return 2; } } }",
]


def _sources():
    cases = list(SNIPPETS)
    files = sorted(glob.glob(os.path.join(_ROOT, "examples", "*.lang")))
    files += sorted(glob.glob(os.path.join(_ROOT, "stdlib", "*.lang")))
    for fp in files:
        with open(fp, "r", encoding="utf-8") as fh:
            cases.append(fh.read())
    return cases


@pytest.mark.parametrize("src", _sources())
def test_retcheck_matches_python(src):
    # Skip sources the Python parser itself rejects (keeps the diff on the
    # checker, not on parser quirks); a clean parse must agree on both sides.
    try:
        Parser(Lexer(src).tokenize()).parse()
    except Exception:
        pytest.skip("source not parseable by Python parser")
    assert glang_lines(src) == py_lines(src)
