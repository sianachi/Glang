"""Namespace resolution.

A Program → Program rewrite that runs before monomorphization. Every
``namespace ns { ... }`` block is flattened away: its member declarations
become ordinary top-level declarations whose names carry the namespace path
(``math::abs``), and references *inside* the namespace are qualified to match.

Reference resolution searches enclosing namespaces innermost-first, so a
member of ``a::b`` may refer to ``foo`` declared in ``a::b`` or in ``a``
without qualification; anything else needs the explicit ``a::b::foo`` form.
Local variables and parameters shadow namespace members, and a name that
resolves to no namespace member is left untouched (it is a global, a builtin,
or an error for Pass2 to report).

After this pass no ``NamespaceDecl`` remains, so the monomorphizer, Pass1,
Pass2, and the interpreter run completely unaware of namespaces — a qualified
name is just an ordinary name that happens to contain ``::``.

Re-declaring a namespace (in the same or another file) extends it: flattening
simply concatenates the members, and Pass1 still rejects genuine duplicates.
"""

from __future__ import annotations

from typing import List, Set, Tuple

from parser.ast_nodes import (
    Program, Decl, Expr, NamespaceDecl,
    FunctionDecl, ClassDecl, InterfaceDecl, EnumDecl,
    StaticFieldDecl, ConstructorDecl, DestructorDecl, MethodDecl, Param,
    TypeNode, NamedType, PointerType, ArrayType, FunctionPointerType, GenericType,
    Block, VarDecl, AssignStmt, IfStmt, WhileStmt, ForStmt, ReturnStmt,
    BinaryExpr, UnaryExpr, CastExpr, CallExpr, IndirectCallExpr, ClosureExpr,
    MethodCallExpr, NewExpr, DeleteExpr, AllocExpr, FreeExpr,
    FieldAccessExpr, ArrowAccessExpr, IndexExpr, AddressOfExpr, DerefExpr,
    IdentifierExpr,
)


class NamespaceResolver:
    def __init__(self) -> None:
        # Every namespaced top-level name after flattening ("math::abs").
        self._declared: Set[str] = set()
        # Local-variable scope stack used while rewriting one declaration.
        self._scopes: List[Set[str]] = []
        # Generic type parameters of the declaration being rewritten; these
        # shadow namespace members in type position.
        self._type_params: Set[str] = set()

    def run(self, program: Program) -> Program:
        # (decl, prefixes) pairs; prefixes is the enclosing-namespace search
        # list, innermost first — e.g. ["a::b", "a"] inside `namespace a::b`.
        flattened: List[Tuple[Decl, List[str]]] = []
        for d in program.declarations:
            self._flatten(d, [], flattened)
        program.declarations = [d for d, _ in flattened]

        for d, prefixes in flattened:
            if prefixes:
                self._r_decl(d, prefixes)
        return program

    # ------------------------------------------------------------------
    # Flattening
    # ------------------------------------------------------------------

    def _flatten(self, d: Decl, chain: List[str],
                 out: List[Tuple[Decl, List[str]]]) -> None:
        if isinstance(d, NamespaceDecl):
            new_chain = chain + d.name.split("::")
            for member in d.declarations:
                self._flatten(member, new_chain, out)
            return
        if chain:
            d.name = "::".join(chain) + "::" + d.name
            self._declared.add(d.name)
        prefixes = ["::".join(chain[:i]) for i in range(len(chain), 0, -1)]
        out.append((d, prefixes))

    # ------------------------------------------------------------------
    # Name resolution
    # ------------------------------------------------------------------

    def _resolve_type_name(self, name: str, prefixes: List[str]) -> str:
        if name in self._type_params:
            return name
        for prefix in prefixes:
            candidate = f"{prefix}::{name}"
            if candidate in self._declared:
                return candidate
        return name

    def _resolve_value_name(self, name: str, prefixes: List[str]) -> str:
        if "::" not in name and self._is_local(name):
            return name
        return self._resolve_type_name(name, prefixes)

    def _is_local(self, name: str) -> bool:
        return any(name in scope for scope in self._scopes)

    # ------------------------------------------------------------------
    # Declarations
    # ------------------------------------------------------------------

    def _r_decl(self, d: Decl, p: List[str]) -> None:
        if isinstance(d, FunctionDecl):
            self._type_params = set(d.type_params)
            self._r_type(d.return_type, p)
            self._r_params(d.params, p)
            self._scopes = [{prm.name for prm in d.params}]
            self._r_block_stmts(d.body, p)
            self._scopes = []
            self._type_params = set()
        elif isinstance(d, ClassDecl):
            self._type_params = set(d.type_params)
            if d.superclass is not None:
                d.superclass = self._resolve_type_name(d.superclass, p)
            d.interfaces = [self._resolve_type_name(i, p) for i in d.interfaces]
            for fd in d.fields:
                self._r_type(fd.type, p)
            for sfd in d.static_fields:
                self._r_type(sfd.type, p)
                self._scopes = [set()]
                self._r_expr(sfd.initializer, p)
                self._scopes = []
            if d.constructor is not None:
                self._r_ctor(d.constructor, p)
            if d.destructor is not None:
                self._scopes = [set()]
                self._r_block_stmts(d.destructor.body, p)
                self._scopes = []
            for md in d.methods:
                self._r_type(md.return_type, p)
                self._r_params(md.params, p)
                if md.body is not None:
                    self._scopes = [{prm.name for prm in md.params}]
                    self._r_block_stmts(md.body, p)
                    self._scopes = []
            self._type_params = set()
        elif isinstance(d, InterfaceDecl):
            for md in d.methods:
                self._r_type(md.return_type, p)
                self._r_params(md.params, p)
        # EnumDecl carries only integer variants — nothing to rewrite.

    def _r_ctor(self, ctor: ConstructorDecl, p: List[str]) -> None:
        self._r_params(ctor.params, p)
        self._scopes = [{prm.name for prm in ctor.params}]
        if ctor.super_args:
            for a in ctor.super_args:
                self._r_expr(a, p)
        self._r_block_stmts(ctor.body, p)
        self._scopes = []

    def _r_params(self, params: List[Param], p: List[str]) -> None:
        for prm in params:
            self._r_type(prm.type, p)

    # ------------------------------------------------------------------
    # Types (mutated in place)
    # ------------------------------------------------------------------

    def _r_type(self, t: TypeNode, p: List[str]) -> None:
        if isinstance(t, NamedType):
            t.name = self._resolve_type_name(t.name, p)
        elif isinstance(t, (PointerType, ArrayType)):
            self._r_type(t.base, p)
        elif isinstance(t, FunctionPointerType):
            for pt in t.param_types:
                self._r_type(pt, p)
            self._r_type(t.return_type, p)
        elif isinstance(t, GenericType):
            t.name = self._resolve_type_name(t.name, p)
            for a in t.type_args:
                self._r_type(a, p)

    # ------------------------------------------------------------------
    # Statements
    # ------------------------------------------------------------------

    def _r_block_stmts(self, block: Block, p: List[str]) -> None:
        for s in block.stmts:
            self._r_stmt(s, p)

    def _r_block(self, block: Block, p: List[str]) -> None:
        self._scopes.append(set())
        self._r_block_stmts(block, p)
        self._scopes.pop()

    def _r_stmt(self, s, p: List[str]) -> None:
        if isinstance(s, Block):
            self._r_block(s, p)
        elif isinstance(s, VarDecl):
            self._r_type(s.type, p)
            self._r_expr(s.initializer, p)
            self._scopes[-1].add(s.name)
        elif isinstance(s, AssignStmt):
            self._r_expr(s.target, p)
            self._r_expr(s.value, p)
        elif isinstance(s, IfStmt):
            self._r_expr(s.condition, p)
            self._r_stmt(s.then_branch, p)
            if s.else_branch is not None:
                self._r_stmt(s.else_branch, p)
        elif isinstance(s, WhileStmt):
            self._r_expr(s.condition, p)
            self._r_block(s.body, p)
        elif isinstance(s, ForStmt):
            self._scopes.append(set())
            self._r_stmt(s.init, p)
            self._r_expr(s.condition, p)
            self._r_post(s.post, p)
            self._r_block(s.body, p)
            self._scopes.pop()
        elif isinstance(s, ReturnStmt):
            if s.value is not None:
                self._r_expr(s.value, p)
        elif isinstance(s, Expr):
            self._r_expr(s, p)
        # BreakStmt / ContinueStmt carry nothing.

    def _r_post(self, post, p: List[str]) -> None:
        if isinstance(post, AssignStmt):
            self._r_stmt(post, p)
        else:
            self._r_expr(post, p)

    # ------------------------------------------------------------------
    # Expressions
    # ------------------------------------------------------------------

    def _r_expr(self, e, p: List[str]) -> None:
        if isinstance(e, IdentifierExpr):
            e.name = self._resolve_value_name(e.name, p)
        elif isinstance(e, BinaryExpr):
            self._r_expr(e.left, p)
            self._r_expr(e.right, p)
        elif isinstance(e, UnaryExpr):
            self._r_expr(e.operand, p)
        elif isinstance(e, CastExpr):
            self._r_type(e.target_type, p)
            self._r_expr(e.expr, p)
        elif isinstance(e, CallExpr):
            e.name = self._resolve_value_name(e.name, p)
            for a in e.type_args:
                self._r_type(a, p)
            for a in e.args:
                self._r_expr(a, p)
        elif isinstance(e, IndirectCallExpr):
            self._r_expr(e.callee, p)
            for a in e.args:
                self._r_expr(a, p)
        elif isinstance(e, ClosureExpr):
            self._r_params(e.params, p)
            self._r_type(e.return_type, p)
            self._scopes.append({prm.name for prm in e.params})
            self._r_block_stmts(e.body, p)
            self._scopes.pop()
        elif isinstance(e, MethodCallExpr):
            self._r_expr(e.object, p)
            for a in e.args:
                self._r_expr(a, p)
        elif isinstance(e, NewExpr):
            e.class_name = self._resolve_type_name(e.class_name, p)
            for a in e.type_args:
                self._r_type(a, p)
            for a in e.args:
                self._r_expr(a, p)
        elif isinstance(e, DeleteExpr):
            self._r_expr(e.operand, p)
        elif isinstance(e, AllocExpr):
            self._r_type(e.type, p)
            if e.count is not None:
                self._r_expr(e.count, p)
        elif isinstance(e, FreeExpr):
            self._r_expr(e.operand, p)
        elif isinstance(e, FieldAccessExpr):
            self._r_expr(e.object, p)
        elif isinstance(e, ArrowAccessExpr):
            self._r_expr(e.pointer, p)
        elif isinstance(e, IndexExpr):
            self._r_expr(e.array, p)
            self._r_expr(e.index, p)
        elif isinstance(e, AddressOfExpr):
            self._r_expr(e.operand, p)
        elif isinstance(e, DerefExpr):
            self._r_expr(e.operand, p)
        # Literal / Null / This / Super carry nothing.
