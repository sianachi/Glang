"""Python canonical serializers mirroring compiler/ast.lang's show* functions.

Used by the parser differential tests: parse with the Python parser, serialise
with these, and compare against the Glang parser's output (showProgram etc.).
Kept in one module so expr/stmt/decl forms stay consistent.
"""

from parser import ast_nodes as A
from compiler.ast_serializer import _type_str

show_type = _type_str


def _targs(ta):
    return "" if not ta else "<" + ",".join(_type_str(t) for t in ta) + ">"


def _args(args):
    return "[" + " ".join(show_expr(a) for a in args) + "]"


def _params(ps):
    out = []
    for p in ps:
        pre = "const " if p.is_const else ""
        out.append(f"{pre}{_type_str(p.type)} {p.name}")
    return "[" + " ".join(out) + "]"


def show_expr(e) -> str:
    if isinstance(e, A.LiteralExpr):     return f"lit:{e.kind}:{e.value}"
    if isinstance(e, A.IdentifierExpr):  return f"id:{e.name}"
    if isinstance(e, A.NullExpr):        return "null"
    if isinstance(e, A.ThisExpr):        return "this"
    if isinstance(e, A.SuperExpr):       return "super"
    if isinstance(e, A.UnaryExpr):       return f"(u {e.op} {show_expr(e.operand)})"
    if isinstance(e, A.BinaryExpr):      return f"(b {e.op} {show_expr(e.left)} {show_expr(e.right)})"
    if isinstance(e, A.TernaryExpr):     return f"(?: {show_expr(e.cond)} {show_expr(e.then_expr)} {show_expr(e.else_expr)})"
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
        fin = f" (finally {show_stmt(s.finally_block)})" if s.finally_block is not None else ""
        return f"(try {show_stmt(s.body)} [{cs}]{fin})"
    if isinstance(s, A.MatchStmt):
        arms = " ".join(f"(arm {_pattern(a.pattern)} {show_stmt(a.body)})" for a in s.arms)
        return f"(match {show_expr(s.scrutinee)} [{arms}])"
    raise AssertionError(f"unhandled stmt {type(s).__name__}")


def _str_list(xs):
    return "[" + " ".join(xs) + "]"


def _type_params(tps, bounds):
    parts = []
    for tp in tps:
        if tp in bounds:
            joined = "&".join(_type_str(b) for b in bounds[tp])
            parts.append(f"{tp}:{joined}")
        else:
            parts.append(tp)
    return "[" + " ".join(parts) + "]"


def _field(f):
    c = "const " if f.is_const else ""
    return f"(field {f.access} {c}{f.name} {_type_str(f.type)})"


def _sfield(f):
    c = "const " if f.is_const else ""
    return f"(sfield {f.access} {c}{f.name} {_type_str(f.type)} {show_expr(f.initializer)})"


def _method(m):
    st = " static" if m.is_static else ""
    body = show_stmt(m.body) if m.body is not None else "_"
    return f"(method {m.access}{st} {m.name} {_params(m.params)} {_type_str(m.return_type)} {body})"


def _ctor(c):
    sup = "_"
    if c.super_args is not None:
        sup = "super" + _args(c.super_args)
    return f"(ctor {_params(c.params)} {sup} {show_stmt(c.body)})"


def _evar(v):
    return f"(evar {v.name}{'=' + str(v.value) if v.value is not None else ''})"


def _uvar(v):
    return f"(uvar {v.name} [{' '.join(_field(f) for f in v.fields)}])"


def show_decl(d) -> str:
    if isinstance(d, A.ImportDecl):
        return f"(import {d.path})"
    if isinstance(d, A.FunctionDecl):
        return (f"(fn {d.name} {_type_params(d.type_params, d.type_param_bounds)} "
                f"{_params(d.params)} {_type_str(d.return_type)} {show_stmt(d.body)})")
    if isinstance(d, A.ClassDecl):
        ext = d.superclass if d.superclass else "_"
        ctor = _ctor(d.constructor) if d.constructor is not None else "_"
        dtor = f"(dtor {show_stmt(d.destructor.body)})" if d.destructor is not None else "_"
        mgd = "yes" if d.is_managed else "no"
        return (f"(class {d.access} mgd:{mgd} {d.name} {_type_params(d.type_params, d.type_param_bounds)} "
                f"ext:{ext} impl:{_str_list(d.interfaces)} "
                f"sf:[{' '.join(_sfield(f) for f in d.static_fields)}] "
                f"f:[{' '.join(_field(f) for f in d.fields)}] "
                f"ctor:{ctor} dtor:{dtor} "
                f"m:[{' '.join(_method(m) for m in d.methods)}])")
    if isinstance(d, A.InterfaceDecl):
        return f"(interface {d.name} [{' '.join(_method(m) for m in d.methods)}])"
    if isinstance(d, A.EnumDecl):
        return f"(enum {d.name} [{' '.join(_evar(v) for v in d.variants)}])"
    if isinstance(d, A.UsingDecl):
        pfx = "namespace " if d.is_namespace else ""
        return f"(using {pfx}{d.name})"
    if isinstance(d, A.NamespaceDecl):
        return f"(namespace {d.name} [{' '.join(show_decl(x) for x in d.declarations)}])"
    if isinstance(d, A.ModifierDecl):
        return (f"(modifier {_str_list(d.type_params)} for {_type_str(d.target)} "
                f"[{' '.join(_method(m) for m in d.methods)}])")
    if isinstance(d, A.UnionDecl):
        return (f"(uniondecl {d.name} {_str_list(d.type_params)} "
                f"[{' '.join(_uvar(v) for v in d.variants)}])")
    raise AssertionError(f"unhandled decl {type(d).__name__}")


def show_program(p) -> str:
    imports = " ".join(show_decl(d) for d in p.imports)
    decls = " ".join(show_decl(d) for d in p.declarations)
    return f"(program [{imports}] [{decls}])"
