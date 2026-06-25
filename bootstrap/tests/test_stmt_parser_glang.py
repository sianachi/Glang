"""Differential test for the self-hosted statement parser (stmt_parser.lang).

Each statement is parsed by both the Python StmtParser and the Glang one (via
compiler/stmt_dump.lang, through the interpreter); canonical S-expr forms must
agree.  show_stmt/show_expr below are the exact Python twins of ast.lang's
showStmt/showExpr (including the ExprStmt wrapper and ClosureExpr).
"""

import os
import subprocess
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from lexer.lexer import Lexer
from parser.token_stream import TokenStream
from parser.type_parser import TypeParser
from parser.expr_parser import ExprParser
from parser.stmt_parser import StmtParser
from parser import ast_nodes as A
from compiler.ast_serializer import _type_str

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _targs(ta):
    return "" if not ta else "<" + ",".join(_type_str(t) for t in ta) + ">"


def _args(args):
    return "[" + " ".join(show_expr(a) for a in args) + "]"


def _params(ps):
    parts = []
    for p in ps:
        pre = "const " if p.is_const else ""
        parts.append(f"{pre}{_type_str(p.type)} {p.name}")
    return "[" + " ".join(parts) + "]"


def show_expr(e) -> str:
    if isinstance(e, A.LiteralExpr):     return f"lit:{e.kind}:{e.value}"
    if isinstance(e, A.IdentifierExpr):  return f"id:{e.name}"
    if isinstance(e, A.NullExpr):        return "null"
    if isinstance(e, A.ThisExpr):        return "this"
    if isinstance(e, A.SuperExpr):       return "super"
    if isinstance(e, A.UnaryExpr):       return f"(u {e.op} {show_expr(e.operand)})"
    if isinstance(e, A.BinaryExpr):      return f"(b {e.op} {show_expr(e.left)} {show_expr(e.right)})"
    if isinstance(e, A.AddressOfExpr):   return f"(addr {show_expr(e.operand)})"
    if isinstance(e, A.DerefExpr):       return f"(deref {show_expr(e.operand)})"
    if isinstance(e, A.CastExpr):        return f"(cast {_type_str(e.target_type)} {show_expr(e.expr)})"
    if isinstance(e, A.CallExpr):        return f"(call {e.name}{_targs(e.type_args)} {_args(e.args)})"
    if isinstance(e, A.IndirectCallExpr):return f"(icall {show_expr(e.callee)} {_args(e.args)})"
    if isinstance(e, A.MethodCallExpr):
        sep = "->" if e.is_arrow else "."
        return f"(mcall {sep}{e.method} {show_expr(e.object)} {_args(e.args)})"
    if isinstance(e, A.NewExpr):         return f"(new {e.class_name}{_targs(e.type_args)} {_args(e.args)})"
    if isinstance(e, A.DeleteExpr):      return f"(delete {show_expr(e.operand)})"
    if isinstance(e, A.AllocExpr):
        cs = show_expr(e.count) if e.count is not None else "_"
        return f"(alloc {_type_str(e.type)} {cs})"
    if isinstance(e, A.FreeExpr):        return f"(free {show_expr(e.operand)})"
    if isinstance(e, A.FieldAccessExpr): return f"(field {e.field_name} {show_expr(e.object)})"
    if isinstance(e, A.ArrowAccessExpr): return f"(arrow {e.field_name} {show_expr(e.pointer)})"
    if isinstance(e, A.IndexExpr):       return f"(index {show_expr(e.array)} {show_expr(e.index)})"
    if isinstance(e, A.ClosureExpr):
        return f"(closure {_params(e.params)} {_type_str(e.return_type)} {show_stmt(e.body)})"
    raise AssertionError(f"unhandled expr {type(e).__name__}")


def _pattern(p) -> str:
    if isinstance(p, A.WildcardPattern):
        return "(pat _)"
    return f"(pat {p.union_name}.{p.variant_name} [{' '.join(p.bindings)}])"


def show_stmt(s) -> str:
    if isinstance(s, A.Expr):            return f"(expr {show_expr(s)})"
    if isinstance(s, A.Block):           return f"(block [{' '.join(show_stmt(x) for x in s.stmts)}])"
    if isinstance(s, A.VarDecl):
        pre = "const " if s.is_const else ""
        return f"(var {pre}{s.name} {_type_str(s.type)} {show_expr(s.initializer)})"
    if isinstance(s, A.AssignStmt):      return f"(assign {s.op} {show_expr(s.target)} {show_expr(s.value)})"
    if isinstance(s, A.IfStmt):
        els = show_stmt(s.else_branch) if s.else_branch is not None else "_"
        return f"(if {show_expr(s.condition)} {show_stmt(s.then_branch)} {els})"
    if isinstance(s, A.WhileStmt):       return f"(while {show_expr(s.condition)} {show_stmt(s.body)})"
    if isinstance(s, A.DoWhileStmt):     return f"(do {show_stmt(s.body)} {show_expr(s.condition)})"
    if isinstance(s, A.ForStmt):
        return f"(for {show_stmt(s.init)} {show_expr(s.condition)} {show_stmt(s.post)} {show_stmt(s.body)})"
    if isinstance(s, A.ForeachStmt):
        pre = "const " if s.is_const else ""
        return f"(foreach {pre}{_type_str(s.var_type)} {s.var_name} {show_expr(s.iterable)} {show_stmt(s.body)})"
    if isinstance(s, A.UsingStmt):       return f"(using {show_stmt(s.decl)} {show_stmt(s.body)})"
    if isinstance(s, A.BreakStmt):       return "(break)"
    if isinstance(s, A.ContinueStmt):    return "(continue)"
    if isinstance(s, A.ReturnStmt):
        return f"(return {show_expr(s.value) if s.value is not None else '_'})"
    if isinstance(s, A.ThrowStmt):       return f"(throw {show_expr(s.value)})"
    if isinstance(s, A.TryCatchStmt):
        cs = " ".join(f"(catch {_type_str(c.catch_type)} {c.var_name} {show_stmt(c.body)})" for c in s.catches)
        return f"(try {show_stmt(s.body)} [{cs}])"
    if isinstance(s, A.MatchStmt):
        arms = " ".join(f"(arm {_pattern(a.pattern)} {show_stmt(a.body)})" for a in s.arms)
        return f"(match {show_expr(s.scrutinee)} [{arms}])"
    raise AssertionError(f"unhandled stmt {type(s).__name__}")


STMTS = [
    "int x = 1 + 2;",
    "const float pi = 3.14;",
    "var n = compute();",
    "List<int> xs = makeList();",
    "Map<string, int> m = Map<string, int>();",
    "Dog* d = new Dog();",
    "ns::Color c = pick();",
    "x = 5;", "x += 1;", "arr[i] = v;", "obj.field = y;", "p->next = q;",
    "foo();", "obj.method(1, 2);", "a + b;",
    "if (a) { f(); }",
    "if (a > b) { return a; } else { return b; }",
    "if (a) { x(); } else if (b) { y(); } else { z(); }",
    "while (go) { tick(); }",
    "do { step(); } while (more);",
    "for (int i = 0; i < n; ++i) { sum += i; }",
    "foreach (Item it in items) { use(it); }",
    "foreach (const int v in xs) { total += v; }",
    "return;", "return x + 1;",
    "break;", "continue;",
    "throw new Error(msg);",
    "try { risky(); } catch (IOError* e) { handle(e); }",
    "try { a(); } catch (FooError* e) { b(); } catch (BarError* e) { c(); }",
    "using (File* f = open(path)) { read(f); }",
    "match (*e) { Expr.Num(v) => { return v; } Expr.Add(l, r) => { return l; } _ => { return 0; } }",
    "match (x) { Color.Red => { paint(); } }",
    "{ int a = 1; int b = 2; swap(); }",
    "fn(int) -> int g = (int x) -> int { return x * x; };",
    "fn(int, int) -> int h = (const int a, int b) -> int { return a + b; };",
]


def py_stmt(src: str) -> str:
    toks = Lexer(src).tokenize()
    s = TokenStream(toks)
    tp = TypeParser(s)
    ep = ExprParser(s, tp)
    sp = StmtParser(s, tp, ep)
    ep.set_stmt_parser(sp)
    return show_stmt(sp.parse_statement())


def glang_stmt(src: str) -> str:
    proc = subprocess.run(
        [sys.executable, "bootstrap/main.py", "run", "Toolchain/compiler/stmt_dump.lang"],
        input=src.encode("utf-8"), capture_output=True, cwd=_ROOT,
    )
    return proc.stdout.decode("utf-8").strip()


@pytest.mark.parametrize("src", STMTS)
def test_stmt_matches_python(src):
    assert glang_stmt(src) == py_stmt(src)
