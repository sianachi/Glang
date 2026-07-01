"""Namespace resolution.

A Program → Program rewrite that runs before monomorphization. Every
``namespace ns { ... }`` block is flattened away: its member declarations
become ordinary top-level declarations whose names carry the namespace path
(``math::abs``), and references *inside* the namespace are qualified to match.

Reference resolution searches enclosing namespaces innermost-first, so a
member of ``a::b`` may refer to ``foo`` declared in ``a::b`` or in ``a``
without qualification. Outside the declaring namespace a member is reached
with its qualified name, or unqualified under a ``using`` declaration:

- ``using namespace math;`` opens every member of ``math``
- ``using math::abs;`` imports the single member ``abs``

``using`` is file-scoped: it applies from its position to the end of the file
it appears in (declaration origins are tagged by the loader), so a library's
``using`` never leaks into the files that import it. An unqualified name is
resolved in this order: local variables, enclosing namespaces (innermost
first), explicit top-level declarations, single-member ``using`` imports,
then opened namespaces — where a name found in two opened namespaces is an
ambiguity error. A name that resolves to nothing is left untouched (it is a
builtin or an error for Pass2 to report).

After this pass no ``NamespaceDecl`` or ``UsingDecl`` remains, so the
monomorphizer, Pass1, Pass2, and the interpreter run completely unaware of
namespaces — a qualified name is just an ordinary name that happens to
contain ``::``.

Re-declaring a namespace (in the same or another file) extends it: flattening
simply concatenates the members, and Pass1 still rejects genuine duplicates.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Set, Tuple

from parser.ast_nodes import (
    Program, Decl, Expr, NamespaceDecl, UsingDecl,
    FunctionDecl, ClassDecl, InterfaceDecl, EnumDecl, ModifierDecl, UnionDecl,
    StaticFieldDecl, ConstructorDecl, DestructorDecl, MethodDecl, Param,
    TypeNode, NamedType, PointerType, ArrayType, FunctionPointerType, GenericType, NullableType,
    Block, VarDecl, AssignStmt, IfStmt, WhileStmt, DoWhileStmt, ForStmt,
    ForeachStmt, ReturnStmt, UsingStmt, ThrowStmt, TryCatchStmt,
    MatchStmt, VariantPattern,
    BinaryExpr, TernaryExpr, UnaryExpr, CastExpr, CallExpr, IndirectCallExpr, ClosureExpr,
    MethodCallExpr, NewExpr, DeleteExpr, AllocExpr, FreeExpr,
    FieldAccessExpr, ArrowAccessExpr, IndexExpr, AddressOfExpr, DerefExpr,
    IdentifierExpr,
)
from errors.errors import TypeError


class _UsingContext:
    """The `using` imports active for one source file."""

    def __init__(self) -> None:
        self.aliases: Dict[str, str] = {}  # last segment → qualified name
        self.opened: List[str] = []        # namespaces opened by directives

    def is_empty(self) -> bool:
        return not self.aliases and not self.opened


class NamespaceResolver:
    def __init__(self) -> None:
        # Every namespaced top-level name after flattening ("math::abs").
        self._declared: Set[str] = set()
        # Every namespace path that has at least one member ("a", "a::b").
        self._namespaces: Set[str] = set()
        # Every non-namespaced top-level name.
        self._globals: Set[str] = set()
        # Local-variable scope stack used while rewriting one declaration.
        self._scopes: List[Set[str]] = []
        # Generic type parameters of the declaration being rewritten; these
        # shadow namespace members in type position.
        self._type_params: Set[str] = set()
        # The `using` context of the file owning the declaration being
        # rewritten.
        self._ctx = _UsingContext()

    def run(self, program: Program) -> Program:
        # (decl, prefixes) pairs; prefixes is the enclosing-namespace search
        # list, innermost first — e.g. ["a::b", "a"] inside `namespace a::b`.
        flattened: List[Tuple[Decl, List[str]]] = []
        for d in program.declarations:
            self._flatten(d, [], flattened)

        kept: List[Decl] = []
        contexts: Dict[Optional[str], _UsingContext] = {}
        for d, prefixes in flattened:
            ctx = contexts.setdefault(getattr(d, "origin", None), _UsingContext())
            if isinstance(d, UsingDecl):
                self._register_using(d, ctx)
                continue
            kept.append(d)
            if prefixes or not ctx.is_empty():
                self._ctx = ctx
                self._r_decl(d, prefixes)
        program.declarations = kept
        return program

    # ------------------------------------------------------------------
    # Flattening
    # ------------------------------------------------------------------

    def _flatten(self, d: Decl, chain: List[str],
                 out: List[Tuple[Decl, List[str]]]) -> None:
        if isinstance(d, NamespaceDecl):
            new_chain = chain + d.name.split("::")
            for i in range(1, len(new_chain) + 1):
                self._namespaces.add("::".join(new_chain[:i]))
            for member in d.declarations:
                # Members inherit the namespace block's source file.
                member.origin = getattr(d, "origin", None)
                self._flatten(member, new_chain, out)
            return
        if chain:
            if not isinstance(d, ModifierDecl):
                d.name = "::".join(chain) + "::" + d.name
            self._declared.add(getattr(d, "name", ""))
        elif not isinstance(d, (UsingDecl, ModifierDecl)):
            self._globals.add(d.name)
        prefixes = ["::".join(chain[:i]) for i in range(len(chain), 0, -1)]
        out.append((d, prefixes))

    # ------------------------------------------------------------------
    # `using` registration
    # ------------------------------------------------------------------

    def _register_using(self, d: UsingDecl, ctx: _UsingContext) -> None:
        if d.is_namespace:
            if d.name not in self._namespaces:
                raise TypeError(f"unknown namespace '{d.name}'", d.line, d.col)
            if d.name not in ctx.opened:
                ctx.opened.append(d.name)
            return

        if d.name in self._namespaces:
            raise TypeError(
                f"'{d.name}' is a namespace; write 'using namespace {d.name};'",
                d.line, d.col,
            )
        if d.name not in self._declared:
            raise TypeError(
                f"'{d.name}' is not a namespace member", d.line, d.col
            )
        last = d.name.rsplit("::", 1)[1]
        if last in self._globals:
            raise TypeError(
                f"using declaration '{last}' conflicts with a global "
                f"declaration of the same name",
                d.line, d.col,
            )
        previous = ctx.aliases.get(last)
        if previous is not None and previous != d.name:
            raise TypeError(
                f"using declaration '{last}' conflicts with previous "
                f"'using {previous};'",
                d.line, d.col,
            )
        ctx.aliases[last] = d.name

    # ------------------------------------------------------------------
    # Name resolution
    # ------------------------------------------------------------------

    def _resolve_type_name(self, name: str, prefixes: List[str],
                           line: int, col: int) -> str:
        if name in self._type_params:
            return name
        for prefix in prefixes:
            candidate = f"{prefix}::{name}"
            if candidate in self._declared:
                return candidate
        if name in self._declared or name in self._globals:
            return name
        if "::" not in name:
            alias = self._ctx.aliases.get(name)
            if alias is not None:
                return alias
        matches: List[str] = []
        for ns in self._ctx.opened:
            candidate = f"{ns}::{name}"
            if candidate in self._declared and candidate not in matches:
                matches.append(candidate)
        if len(matches) > 1:
            raise TypeError(
                f"'{name}' is ambiguous: could be "
                + " or ".join(f"'{m}'" for m in matches),
                line, col,
            )
        if matches:
            return matches[0]
        return name

    def _resolve_value_name(self, name: str, prefixes: List[str],
                            line: int, col: int) -> str:
        if "::" not in name and self._is_local(name):
            return name
        return self._resolve_type_name(name, prefixes, line, col)

    def _is_local(self, name: str) -> bool:
        return any(name in scope for scope in self._scopes)

    # ------------------------------------------------------------------
    # Declarations
    # ------------------------------------------------------------------

    def _r_decl(self, d: Decl, p: List[str]) -> None:
        if isinstance(d, FunctionDecl):
            self._type_params = set(d.type_params)
            for name, bound in list(d.type_param_bounds.items()):
                self._r_type(bound, p)
            self._r_type(d.return_type, p)
            self._r_params(d.params, p)
            self._scopes = [{prm.name for prm in d.params}]
            self._r_block_stmts(d.body, p)
            self._scopes = []
            self._type_params = set()
        elif isinstance(d, ClassDecl):
            self._type_params = set(d.type_params)
            for name, bound in list(d.type_param_bounds.items()):
                self._r_type(bound, p)
            if d.superclass is not None:
                d.superclass = self._resolve_type_name(
                    d.superclass, p, d.line, d.col
                )
            d.interfaces = [
                self._resolve_type_name(i, p, d.line, d.col)
                for i in d.interfaces
            ]
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
        elif isinstance(d, ModifierDecl):
            self._type_params = set(d.type_params)
            self._r_type(d.target, p)
            for md in d.methods:
                self._r_type(md.return_type, p)
                self._r_params(md.params, p)
                if md.body is not None:
                    self._scopes = [{prm.name for prm in md.params}]
                    self._r_block_stmts(md.body, p)
                    self._scopes = []
            self._type_params = set()
        elif isinstance(d, UnionDecl):
            for v in d.variants:
                for fd in v.fields:
                    self._r_type(fd.type, p)
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
            if t.name == "var":
                return
            t.name = self._resolve_type_name(t.name, p, t.line, t.col)
        elif isinstance(t, (PointerType, ArrayType)):
            self._r_type(t.base, p)
        elif isinstance(t, FunctionPointerType):
            for pt in t.param_types:
                self._r_type(pt, p)
            self._r_type(t.return_type, p)
        elif isinstance(t, GenericType):
            t.name = self._resolve_type_name(t.name, p, t.line, t.col)
            for a in t.type_args:
                self._r_type(a, p)
        elif isinstance(t, NullableType):
            self._r_type(t.base, p)

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
        elif isinstance(s, DoWhileStmt):
            self._r_block(s.body, p)
            self._r_expr(s.condition, p)
        elif isinstance(s, ForStmt):
            self._scopes.append(set())
            self._r_stmt(s.init, p)
            self._r_expr(s.condition, p)
            self._r_post(s.post, p)
            self._r_block(s.body, p)
            self._scopes.pop()
        elif isinstance(s, ForeachStmt):
            self._r_type(s.var_type, p)
            self._r_expr(s.iterable, p)
            self._scopes.append({s.var_name})
            self._r_block(s.body, p)
            self._scopes.pop()
        elif isinstance(s, UsingStmt):
            self._scopes.append(set())
            self._r_stmt(s.decl, p)
            self._r_block(s.body, p)
            self._scopes.pop()
        elif isinstance(s, ReturnStmt):
            if s.value is not None:
                self._r_expr(s.value, p)
        elif isinstance(s, ThrowStmt):
            self._r_expr(s.value, p)
        elif isinstance(s, TryCatchStmt):
            self._r_block(s.body, p)
            for clause in s.catches:
                clause.catch_type = self._r_type(clause.catch_type, p)
                self._r_block(clause.body, p)
            if s.finally_block is not None:
                self._r_block(s.finally_block, p)
        elif isinstance(s, MatchStmt):
            self._r_expr(s.scrutinee, p)
            for arm in s.arms:
                bindings = arm.pattern.bindings if isinstance(arm.pattern, VariantPattern) else []
                self._scopes.append(set(bindings))
                self._r_block(arm.body, p)
                self._scopes.pop()
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
            e.name = self._resolve_value_name(e.name, p, e.line, e.col)
        elif isinstance(e, BinaryExpr):
            self._r_expr(e.left, p)
            self._r_expr(e.right, p)
        elif isinstance(e, TernaryExpr):
            self._r_expr(e.cond, p)
            self._r_expr(e.then_expr, p)
            self._r_expr(e.else_expr, p)
        elif isinstance(e, UnaryExpr):
            self._r_expr(e.operand, p)
        elif isinstance(e, CastExpr):
            self._r_type(e.target_type, p)
            self._r_expr(e.expr, p)
        elif isinstance(e, CallExpr):
            e.name = self._resolve_value_name(e.name, p, e.line, e.col)
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
            e.class_name = self._resolve_type_name(
                e.class_name, p, e.line, e.col
            )
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
