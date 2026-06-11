"""Generics by monomorphization.

A Program → Program rewrite that runs after parsing and before Pass1. Generic
class/function *templates* (those with type parameters) are pulled out of the
program; every concrete use — ``List<int>``, ``Map<string, List<int>>``,
``identity<int>(x)`` — is turned into a distinct concrete declaration whose name
is *mangled* from the template name and the concrete type arguments
(``"List<int>"``). Use-sites are rewritten to reference the mangled names.

After this pass the program contains no ``GenericType`` nodes and no templates,
so Pass1, Pass2, and the interpreter run completely unaware of generics — each
instantiation is just an ordinary class/function.

The transform is driven by a single recursive substituter parameterised by a
``mapping`` from type-parameter name to concrete ``TypeNode``. Rewriting the
non-generic parts of the program uses an empty mapping; instantiating a template
uses ``{param: arg, ...}``. Discovered instantiations are processed via a
worklist, so transitive and nested instantiations are handled.
"""

from __future__ import annotations

import copy
from typing import Dict, List, Optional, Tuple

from parser.ast_nodes import (
    Program, Decl, Expr, FunctionDecl, ClassDecl, FieldDecl, StaticFieldDecl,
    ConstructorDecl, DestructorDecl, MethodDecl,
    TypeNode, NamedType, PointerType, ArrayType, FunctionPointerType, GenericType,
    Block, VarDecl, AssignStmt, IfStmt, WhileStmt, DoWhileStmt, ForStmt,
    ForeachStmt, ReturnStmt, UsingStmt,
    BinaryExpr, UnaryExpr, CastExpr, CallExpr, IndirectCallExpr, ClosureExpr,
    MethodCallExpr, NewExpr, DeleteExpr, AllocExpr, FreeExpr,
    FieldAccessExpr, ArrowAccessExpr, IndexExpr, AddressOfExpr, DerefExpr,
)
from analyser.type_utils import type_str
from errors.errors import TypeError


def mangle(name: str, args: List[TypeNode]) -> str:
    """The concrete instantiation name, e.g. ``List<int>`` / ``Map<string,int>``."""
    return f"{name}<{','.join(type_str(a) for a in args)}>"


class Monomorphizer:
    def __init__(self) -> None:
        self._class_templates: Dict[str, ClassDecl] = {}
        self._func_templates: Dict[str, FunctionDecl] = {}
        # Mangled name → concrete decl (None marks "enqueued, not yet built").
        self._instances: Dict[str, Optional[Decl]] = {}
        # Pending instantiations: (kind, base_name, concrete_args, mangled_name).
        self._worklist: List[Tuple[str, str, List[TypeNode], str]] = []
        self._new_decls: List[Decl] = []

    def run(self, program: Program) -> Program:
        kept: List[Decl] = []
        for d in program.declarations:
            if isinstance(d, ClassDecl) and d.type_params:
                self._class_templates[d.name] = d
            elif isinstance(d, FunctionDecl) and d.type_params:
                self._func_templates[d.name] = d
            else:
                kept.append(d)

        # Rewrite the non-generic program; this discovers root instantiations.
        for d in kept:
            self._t_decl(d, {})

        # Build each instantiation; building may discover further ones.
        while self._worklist:
            kind, base, args, mangled = self._worklist.pop(0)
            self._instances[mangled] = self._build_instance(kind, base, args, mangled)

        program.declarations = kept + self._new_decls
        return program

    # ------------------------------------------------------------------
    # Instantiation
    # ------------------------------------------------------------------

    def _register(self, kind: str, base: str, args: List[TypeNode],
                  line: int, col: int) -> str:
        """Validate an instantiation, enqueue it if new, and return its mangled
        name."""
        if kind == "class":
            template = self._class_templates.get(base)
        else:
            template = self._func_templates.get(base)
        if template is None:
            raise TypeError(f"'{base}' is not a generic {kind}", line, col)
        if len(template.type_params) != len(args):
            raise TypeError(
                f"'{base}' expects {len(template.type_params)} type "
                f"argument(s), got {len(args)}",
                line, col,
            )
        name = mangle(base, args)
        if name not in self._instances:
            self._instances[name] = None
            self._worklist.append((kind, base, args, name))
        return name

    def _build_instance(self, kind: str, base: str, args: List[TypeNode],
                        mangled: str) -> Decl:
        template = (self._class_templates if kind == "class"
                    else self._func_templates)[base]
        mapping = dict(zip(template.type_params, args))
        clone = copy.deepcopy(template)
        clone.name = mangled
        clone.type_params = []
        self._t_decl(clone, mapping)
        self._new_decls.append(clone)
        return clone

    # ------------------------------------------------------------------
    # Type substitution
    # ------------------------------------------------------------------

    def _t_type(self, t: TypeNode, m: Dict[str, TypeNode]) -> TypeNode:
        if isinstance(t, NamedType):
            if t.name in m:
                return copy.deepcopy(m[t.name])
            return t
        if isinstance(t, PointerType):
            t.base = self._t_type(t.base, m)
            return t
        if isinstance(t, ArrayType):
            t.base = self._t_type(t.base, m)
            return t
        if isinstance(t, FunctionPointerType):
            t.param_types = [self._t_type(p, m) for p in t.param_types]
            t.return_type = self._t_type(t.return_type, m)
            return t
        if isinstance(t, GenericType):
            concrete = [self._t_type(a, m) for a in t.type_args]
            name = self._register("class", t.name, concrete, t.line, t.col)
            return NamedType(name=name, line=t.line, col=t.col)
        return t

    # ------------------------------------------------------------------
    # Declarations (mutated in place)
    # ------------------------------------------------------------------

    def _t_decl(self, d: Decl, m: Dict[str, TypeNode]) -> None:
        if isinstance(d, FunctionDecl):
            d.return_type = self._t_type(d.return_type, m)
            self._t_params(d.params, m)
            self._t_block(d.body, m)
        elif isinstance(d, ClassDecl):
            for fd in d.fields:
                fd.type = self._t_type(fd.type, m)
            for sfd in d.static_fields:
                sfd.type = self._t_type(sfd.type, m)
                self._t_expr(sfd.initializer, m)
            if d.constructor is not None:
                self._t_decl(d.constructor, m)
            if d.destructor is not None:
                self._t_decl(d.destructor, m)
            for md in d.methods:
                self._t_decl(md, m)
        elif isinstance(d, MethodDecl):
            d.return_type = self._t_type(d.return_type, m)
            self._t_params(d.params, m)
            if d.body is not None:
                self._t_block(d.body, m)
        elif isinstance(d, ConstructorDecl):
            self._t_params(d.params, m)
            if d.super_args:
                for a in d.super_args:
                    self._t_expr(a, m)
            self._t_block(d.body, m)
        elif isinstance(d, DestructorDecl):
            self._t_block(d.body, m)

    def _t_params(self, params, m: Dict[str, TypeNode]) -> None:
        for p in params:
            p.type = self._t_type(p.type, m)

    # ------------------------------------------------------------------
    # Statements (mutated in place)
    # ------------------------------------------------------------------

    def _t_block(self, block: Block, m: Dict[str, TypeNode]) -> None:
        for s in block.stmts:
            self._t_stmt(s, m)

    def _t_stmt(self, s, m: Dict[str, TypeNode]) -> None:
        if isinstance(s, Block):
            self._t_block(s, m)
        elif isinstance(s, VarDecl):
            s.type = self._t_type(s.type, m)
            self._t_expr(s.initializer, m)
        elif isinstance(s, AssignStmt):
            self._t_expr(s.target, m)
            self._t_expr(s.value, m)
        elif isinstance(s, IfStmt):
            self._t_expr(s.condition, m)
            self._t_stmt(s.then_branch, m)
            if s.else_branch is not None:
                self._t_stmt(s.else_branch, m)
        elif isinstance(s, WhileStmt):
            self._t_expr(s.condition, m)
            self._t_block(s.body, m)
        elif isinstance(s, DoWhileStmt):
            self._t_block(s.body, m)
            self._t_expr(s.condition, m)
        elif isinstance(s, ForStmt):
            self._t_stmt(s.init, m)
            self._t_expr(s.condition, m)
            self._t_post(s.post, m)
            self._t_block(s.body, m)
        elif isinstance(s, ForeachStmt):
            s.var_type = self._t_type(s.var_type, m)
            self._t_expr(s.iterable, m)
            self._t_block(s.body, m)
        elif isinstance(s, UsingStmt):
            self._t_stmt(s.decl, m)
            self._t_block(s.body, m)
        elif isinstance(s, ReturnStmt):
            if s.value is not None:
                self._t_expr(s.value, m)
        elif isinstance(s, Expr):
            # A bare expression statement (e.g. `foo();`, `x.bar();`).
            self._t_expr(s, m)
        # BreakStmt / ContinueStmt carry nothing.

    def _t_post(self, post, m: Dict[str, TypeNode]) -> None:
        if isinstance(post, AssignStmt):
            self._t_stmt(post, m)
        else:
            self._t_expr(post, m)

    # ------------------------------------------------------------------
    # Expressions (mutated in place)
    # ------------------------------------------------------------------

    def _t_expr(self, e, m: Dict[str, TypeNode]) -> None:
        if isinstance(e, BinaryExpr):
            self._t_expr(e.left, m)
            self._t_expr(e.right, m)
        elif isinstance(e, UnaryExpr):
            self._t_expr(e.operand, m)
        elif isinstance(e, CastExpr):
            e.target_type = self._t_type(e.target_type, m)
            self._t_expr(e.expr, m)
        elif isinstance(e, CallExpr):
            for a in e.args:
                self._t_expr(a, m)
            self._t_call(e, m)
        elif isinstance(e, IndirectCallExpr):
            self._t_expr(e.callee, m)
            for a in e.args:
                self._t_expr(a, m)
        elif isinstance(e, ClosureExpr):
            self._t_params(e.params, m)
            e.return_type = self._t_type(e.return_type, m)
            self._t_block(e.body, m)
        elif isinstance(e, MethodCallExpr):
            self._t_expr(e.object, m)
            for a in e.args:
                self._t_expr(a, m)
        elif isinstance(e, NewExpr):
            for a in e.args:
                self._t_expr(a, m)
            self._t_new(e, m)
        elif isinstance(e, DeleteExpr):
            self._t_expr(e.operand, m)
        elif isinstance(e, AllocExpr):
            e.type = self._t_type(e.type, m)
            if e.count is not None:
                self._t_expr(e.count, m)
        elif isinstance(e, FreeExpr):
            self._t_expr(e.operand, m)
        elif isinstance(e, FieldAccessExpr):
            self._t_expr(e.object, m)
        elif isinstance(e, ArrowAccessExpr):
            self._t_expr(e.pointer, m)
        elif isinstance(e, IndexExpr):
            self._t_expr(e.array, m)
            self._t_expr(e.index, m)
        elif isinstance(e, AddressOfExpr):
            self._t_expr(e.operand, m)
        elif isinstance(e, DerefExpr):
            self._t_expr(e.operand, m)
        # Identifier / Literal / Null / This / Super carry nothing.

    def _t_call(self, e: CallExpr, m: Dict[str, TypeNode]) -> None:
        if e.type_args:
            concrete = [self._t_type(a, m) for a in e.type_args]
            kind = "func" if e.name in self._func_templates else "class"
            e.name = self._register(kind, e.name, concrete, e.line, e.col)
            e.type_args = []
        elif e.name in m and isinstance(m[e.name], NamedType):
            # Stack construction through a type parameter: `T(args)`.
            e.name = m[e.name].name

    def _t_new(self, e: NewExpr, m: Dict[str, TypeNode]) -> None:
        if e.type_args:
            concrete = [self._t_type(a, m) for a in e.type_args]
            e.class_name = self._register("class", e.class_name, concrete,
                                          e.line, e.col)
            e.type_args = []
        elif e.class_name in m and isinstance(m[e.class_name], NamedType):
            # `new T(args)` inside a template body.
            e.class_name = m[e.class_name].name
