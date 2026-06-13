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
from contextlib import contextmanager
from typing import Dict, List, Optional, Tuple

from parser.ast_nodes import (
    Program, Decl, Expr, FunctionDecl, ClassDecl, FieldDecl, StaticFieldDecl,
    ConstructorDecl, DestructorDecl, MethodDecl, ModifierDecl,
    TypeNode, NamedType, PointerType, ArrayType, FunctionPointerType, GenericType,
    NullableType,
    Block, VarDecl, AssignStmt, IfStmt, WhileStmt, DoWhileStmt, ForStmt,
    ForeachStmt, ReturnStmt, UsingStmt, ThrowStmt, TryCatchStmt, CatchClause,
    BinaryExpr, UnaryExpr, CastExpr, CallExpr, IndirectCallExpr, ClosureExpr,
    MethodCallExpr, NewExpr, DeleteExpr, AllocExpr, FreeExpr,
    FieldAccessExpr, ArrowAccessExpr, IndexExpr, AddressOfExpr, DerefExpr,
    IdentifierExpr, LiteralExpr, NullExpr,
)
from analyser.type_utils import (
    binary_result_type, type_str, types_equal, unary_result_type,
)
from errors.errors import TypeError


PRIMITIVES = {"int", "float", "bool", "char", "byte", "string", "void", "null"}


def mangle(name: str, args: List[TypeNode]) -> str:
    """The concrete instantiation name, e.g. ``List<int>`` / ``Map<string,int>``."""
    return f"{name}<{','.join(type_str(a) for a in args)}>"


class Monomorphizer:
    def __init__(self) -> None:
        self._class_templates: Dict[str, ClassDecl] = {}
        self._func_templates: Dict[str, FunctionDecl] = {}
        self._class_names: set[str] = set()
        self._interface_names: set[str] = set()
        self._enum_names: set[str] = set()
        self._class_supers: Dict[str, Optional[str]] = {}
        self._class_interfaces: Dict[str, List[str]] = {}
        self._class_instance_args: Dict[str, Tuple[str, List[TypeNode]]] = {}
        self._function_returns: Dict[str, TypeNode] = {}
        self._scopes: List[Dict[str, TypeNode]] = []
        # Mangled name → concrete decl (None marks "enqueued, not yet built").
        self._instances: Dict[str, Optional[Decl]] = {}
        # Pending instantiations: (kind, base_name, concrete_args, mangled_name).
        self._worklist: List[Tuple[str, str, List[TypeNode], str]] = []
        self._new_decls: List[Decl] = []
        # Generic modifier templates: base class name → list of ModifierDecl templates.
        self._modifier_templates: Dict[str, List[ModifierDecl]] = {}

    def run(self, program: Program) -> Program:
        self._collect_known_decls(program.declarations)
        kept: List[Decl] = []
        for d in program.declarations:
            if isinstance(d, ClassDecl) and d.type_params:
                self._class_templates[d.name] = d
            elif isinstance(d, FunctionDecl) and d.type_params:
                self._func_templates[d.name] = d
            elif isinstance(d, ModifierDecl) and d.type_params:
                # Generic modifier — collect by the base name of its target.
                # target is always a GenericType like List<T> for generic modifiers.
                if isinstance(d.target, GenericType):
                    base = d.target.name
                else:
                    base = type_str(d.target)
                self._modifier_templates.setdefault(base, []).append(d)
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

    def _collect_known_decls(self, decls: List[Decl]) -> None:
        from parser.ast_nodes import InterfaceDecl, EnumDecl

        for d in decls:
            if isinstance(d, ClassDecl):
                self._class_names.add(d.name)
                self._class_supers[d.name] = d.superclass
                self._class_interfaces[d.name] = list(d.interfaces)
            elif isinstance(d, InterfaceDecl):
                self._interface_names.add(d.name)
            elif isinstance(d, EnumDecl):
                self._enum_names.add(d.name)
            elif isinstance(d, FunctionDecl) and not d.type_params:
                self._function_returns[d.name] = d.return_type

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
        self._check_type_arg_bounds(template, args, line, col)
        name = mangle(base, args)
        if name not in self._instances:
            self._instances[name] = None
            self._worklist.append((kind, base, args, name))
            if kind == "class":
                self._register_class_instance_metadata(base, args, name)
            else:
                self._register_function_instance_metadata(base, args, name)
        return name

    def _build_instance(self, kind: str, base: str, args: List[TypeNode],
                        mangled: str) -> Decl:
        template = (self._class_templates if kind == "class"
                    else self._func_templates)[base]
        mapping = dict(zip(template.type_params, args))
        clone = copy.deepcopy(template)
        clone.name = mangled
        clone.type_params = []
        clone.type_param_bounds = {}
        self._t_decl(clone, mapping)
        self._new_decls.append(clone)
        return clone

    def _register_class_instance_metadata(
        self, base: str, args: List[TypeNode], mangled: str
    ) -> None:
        template = self._class_templates[base]
        mapping = dict(zip(template.type_params, args))
        self._class_names.add(mangled)
        self._class_instance_args[mangled] = (base, copy.deepcopy(args))
        superclass = template.superclass
        if superclass in mapping and isinstance(mapping[superclass], NamedType):
            superclass = mapping[superclass].name
        self._class_supers[mangled] = superclass
        interfaces = []
        for iface in template.interfaces:
            if iface in mapping and isinstance(mapping[iface], NamedType):
                interfaces.append(mapping[iface].name)
            else:
                interfaces.append(iface)
        self._class_interfaces[mangled] = interfaces
        # Instantiate any modifier templates that target this base class.
        for tmpl in self._modifier_templates.get(base, []):
            if len(tmpl.type_params) == len(args):
                self._build_modifier_instance(tmpl, args, mangled)

    def _build_modifier_instance(
        self, tmpl: ModifierDecl, args: List[TypeNode], target_mangled: str
    ) -> None:
        mapping = dict(zip(tmpl.type_params, args))
        clone = copy.deepcopy(tmpl)
        clone.type_params = []
        clone.target = NamedType(target_mangled)
        self._t_decl(clone, mapping)
        self._new_decls.append(clone)

    def _register_function_instance_metadata(
        self, base: str, args: List[TypeNode], mangled: str
    ) -> None:
        template = self._func_templates[base]
        mapping = dict(zip(template.type_params, args))
        self._function_returns[mangled] = self._t_type(
            copy.deepcopy(template.return_type), mapping
        )

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
        if isinstance(t, NullableType):
            t.base = self._t_type(t.base, m)
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
            if not d.type_params:
                self._function_returns[d.name] = d.return_type
            with self._scope():
                for p in d.params:
                    self._define_var(p.name, p.type)
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
                with self._scope():
                    for p in d.params:
                        self._define_var(p.name, p.type)
                    self._t_block(d.body, m)
        elif isinstance(d, ConstructorDecl):
            self._t_params(d.params, m)
            if d.super_args:
                for a in d.super_args:
                    self._t_expr(a, m)
            with self._scope():
                for p in d.params:
                    self._define_var(p.name, p.type)
                self._t_block(d.body, m)
        elif isinstance(d, DestructorDecl):
            self._t_block(d.body, m)
        elif isinstance(d, ModifierDecl):
            d.target = self._t_type(d.target, m)
            for md in d.methods:
                self._t_decl(md, m)

    def _t_params(self, params, m: Dict[str, TypeNode]) -> None:
        for p in params:
            p.type = self._t_type(p.type, m)

    # ------------------------------------------------------------------
    # Statements (mutated in place)
    # ------------------------------------------------------------------

    def _t_block(self, block: Block, m: Dict[str, TypeNode]) -> None:
        with self._scope():
            for s in block.stmts:
                self._t_stmt(s, m)

    def _t_stmt(self, s, m: Dict[str, TypeNode]) -> None:
        if isinstance(s, Block):
            self._t_block(s, m)
        elif isinstance(s, VarDecl):
            self._t_expr(s.initializer, m)
            if self._is_var_type(s.type):
                inferred = self._infer_expr_type(s.initializer)
                if (
                    inferred is not None
                    and not self._is_null_type(inferred)
                    and not self._is_void_type(inferred)
                ):
                    s.type = copy.deepcopy(inferred)
            else:
                s.type = self._t_type(s.type, m)
            self._define_var(s.name, s.type)
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
            with self._scope():
                self._t_stmt(s.init, m)
                self._t_expr(s.condition, m)
                self._t_post(s.post, m)
                self._t_block(s.body, m)
        elif isinstance(s, ForeachStmt):
            s.var_type = self._t_type(s.var_type, m)
            self._t_expr(s.iterable, m)
            if self._is_var_type(s.var_type):
                iterable_t = self._infer_expr_type(s.iterable)
                elem_t = self._infer_foreach_element_type(iterable_t)
                if elem_t is not None:
                    s.var_type = elem_t
            with self._scope():
                self._define_var(s.var_name, s.var_type)
                self._t_block(s.body, m)
        elif isinstance(s, UsingStmt):
            with self._scope():
                self._t_stmt(s.decl, m)
                self._t_block(s.body, m)
        elif isinstance(s, ReturnStmt):
            if s.value is not None:
                self._t_expr(s.value, m)
        elif isinstance(s, ThrowStmt):
            self._t_expr(s.value, m)
        elif isinstance(s, TryCatchStmt):
            self._t_block(s.body, m)
            for clause in s.catches:
                clause.catch_type = self._t_type(clause.catch_type, m)
                with self._scope():
                    self._t_block(clause.body, m)
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
        elif e.name in self._func_templates:
            concrete = self._infer_instantiation("func", e.name, e.args, e.line, e.col)
            e.name = self._register("func", e.name, concrete, e.line, e.col)
        elif e.name in self._class_templates:
            concrete = self._infer_instantiation("class", e.name, e.args, e.line, e.col)
            e.name = self._register("class", e.name, concrete, e.line, e.col)
        elif e.name in m and isinstance(m[e.name], NamedType):
            # Stack construction through a type parameter: `T(args)`.
            e.name = m[e.name].name

    def _t_new(self, e: NewExpr, m: Dict[str, TypeNode]) -> None:
        if e.type_args:
            concrete = [self._t_type(a, m) for a in e.type_args]
            e.class_name = self._register("class", e.class_name, concrete,
                                          e.line, e.col)
            e.type_args = []
        elif e.class_name in self._class_templates:
            concrete = self._infer_instantiation("class", e.class_name, e.args, e.line, e.col)
            e.class_name = self._register("class", e.class_name, concrete,
                                          e.line, e.col)
        elif e.class_name in m and isinstance(m[e.class_name], NamedType):
            # `new T(args)` inside a template body.
            e.class_name = m[e.class_name].name

    # ------------------------------------------------------------------
    # Generic inference and bounds
    # ------------------------------------------------------------------

    def _infer_instantiation(
        self, kind: str, base: str, args: List[Expr], line: int, col: int
    ) -> List[TypeNode]:
        template = (self._func_templates if kind == "func"
                    else self._class_templates)[base]
        params = template.params if kind == "func" else (
            template.constructor.params if template.constructor is not None else []
        )
        if len(params) != len(args):
            raise TypeError(
                f"cannot infer type arguments for '{base}': expected "
                f"{len(params)} argument(s), got {len(args)}",
                line, col,
            )

        mapping: Dict[str, TypeNode] = {}
        type_param_set = set(template.type_params)
        for param, arg in zip(params, args):
            arg_t = self._infer_expr_type(arg)
            if arg_t is None:
                raise TypeError(
                    f"cannot infer type arguments for '{base}'",
                    line, col,
                )
            self._unify_type_args(param.type, arg_t, type_param_set, mapping, line, col)

        concrete: List[TypeNode] = []
        for type_param in template.type_params:
            if type_param not in mapping:
                raise TypeError(
                    f"cannot infer type argument '{type_param}' for '{base}'",
                    line, col,
                )
            concrete.append(mapping[type_param])
        return concrete

    def _unify_type_args(
        self,
        pattern: TypeNode,
        actual: TypeNode,
        type_params: set[str],
        mapping: Dict[str, TypeNode],
        line: int,
        col: int,
    ) -> None:
        if isinstance(pattern, NamedType) and pattern.name in type_params:
            previous = mapping.get(pattern.name)
            if previous is not None and not types_equal(previous, actual):
                raise TypeError(
                    f"cannot infer type argument '{pattern.name}' from "
                    f"both '{type_str(previous)}' and '{type_str(actual)}'",
                    line, col,
                )
            mapping[pattern.name] = copy.deepcopy(actual)
            return

        if isinstance(pattern, PointerType) and isinstance(actual, PointerType):
            self._unify_type_args(pattern.base, actual.base, type_params, mapping, line, col)
            return
        if isinstance(pattern, ArrayType) and isinstance(actual, ArrayType):
            self._unify_type_args(pattern.base, actual.base, type_params, mapping, line, col)
            return
        if isinstance(pattern, FunctionPointerType) and isinstance(actual, FunctionPointerType):
            for pp, ap in zip(pattern.param_types, actual.param_types):
                self._unify_type_args(pp, ap, type_params, mapping, line, col)
            self._unify_type_args(pattern.return_type, actual.return_type,
                                  type_params, mapping, line, col)
            return
        if isinstance(pattern, GenericType):
            actual_args = self._generic_actual_args(pattern.name, actual)
            if actual_args is None or len(actual_args) != len(pattern.type_args):
                return
            for pp, ap in zip(pattern.type_args, actual_args):
                self._unify_type_args(pp, ap, type_params, mapping, line, col)

    def _generic_actual_args(
        self, base: str, actual: TypeNode
    ) -> Optional[List[TypeNode]]:
        if isinstance(actual, GenericType) and actual.name == base:
            return actual.type_args
        if isinstance(actual, NamedType):
            info = self._class_instance_args.get(actual.name)
            if info is not None and info[0] == base:
                return info[1]
        return None

    def _check_type_arg_bounds(
        self, template, args: List[TypeNode], line: int, col: int
    ) -> None:
        mapping = dict(zip(template.type_params, args))
        for type_param, arg in zip(template.type_params, args):
            bound = template.type_param_bounds.get(type_param)
            if bound is None:
                continue
            concrete_bound = self._t_type(copy.deepcopy(bound), mapping)
            if not self._type_satisfies_bound(arg, concrete_bound):
                raise TypeError(
                    f"type argument '{type_str(arg)}' does not satisfy "
                    f"bound '{type_str(concrete_bound)}' for '{type_param}'",
                    line, col,
                )

    def _type_satisfies_bound(self, arg: TypeNode, bound: TypeNode) -> bool:
        if types_equal(arg, bound):
            return True
        if isinstance(arg, PointerType) and isinstance(bound, PointerType):
            return self._type_satisfies_bound(arg.base, bound.base)
        if isinstance(arg, NamedType) and isinstance(bound, NamedType):
            if bound.name in PRIMITIVES or bound.name in self._enum_names:
                return arg.name == bound.name
            if bound.name in self._interface_names:
                return self._class_implements(arg.name, bound.name)
            if bound.name in self._class_names:
                return self._class_extends(arg.name, bound.name)
            raise TypeError(f"unknown bound type '{bound.name}'", bound.line, bound.col)
        return False

    def _class_extends(self, class_name: str, bound_name: str) -> bool:
        current: Optional[str] = class_name
        while current is not None:
            if current == bound_name:
                return True
            current = self._class_supers.get(current)
        return False

    def _class_implements(self, class_name: str, iface: str) -> bool:
        current: Optional[str] = class_name
        while current is not None:
            if iface in self._class_interfaces.get(current, []):
                return True
            current = self._class_supers.get(current)
        return False

    # ------------------------------------------------------------------
    # Lightweight type inference for monomorphization
    # ------------------------------------------------------------------

    @contextmanager
    def _scope(self):
        self._scopes.append({})
        try:
            yield
        finally:
            self._scopes.pop()

    def _define_var(self, name: str, t: TypeNode) -> None:
        if self._scopes:
            self._scopes[-1][name] = t

    def _lookup_var(self, name: str) -> Optional[TypeNode]:
        for scope in reversed(self._scopes):
            if name in scope:
                return scope[name]
        return None

    def _is_var_type(self, t: TypeNode) -> bool:
        return isinstance(t, NamedType) and t.name == "var"

    def _is_null_type(self, t: TypeNode) -> bool:
        return isinstance(t, NamedType) and t.name == "null"

    def _is_void_type(self, t: TypeNode) -> bool:
        return isinstance(t, NamedType) and t.name == "void"

    def _infer_expr_type(self, e) -> Optional[TypeNode]:
        if isinstance(e, LiteralExpr):
            return NamedType(e.kind)
        if isinstance(e, NullExpr):
            return NamedType("null")
        if isinstance(e, IdentifierExpr):
            return self._lookup_var(e.name)
        if isinstance(e, CallExpr):
            if e.name in self._function_returns:
                return self._function_returns[e.name]
            if e.name in self._class_names:
                return NamedType(e.name)
            return None
        if isinstance(e, NewExpr):
            return PointerType(NamedType(e.class_name))
        if isinstance(e, CastExpr):
            return e.target_type
        if isinstance(e, IndexExpr):
            container_t = self._infer_expr_type(e.array)
            if isinstance(container_t, ArrayType):
                return container_t.base
            if isinstance(container_t, PointerType):
                return container_t.base
            if isinstance(container_t, NamedType) and container_t.name == "string":
                return NamedType("char")
            return None
        if isinstance(e, BinaryExpr):
            left_t = self._infer_expr_type(e.left)
            right_t = self._infer_expr_type(e.right)
            if left_t is None or right_t is None:
                return None
            try:
                return binary_result_type(e.op, left_t, right_t)
            except TypeError:
                return None
        if isinstance(e, UnaryExpr):
            operand_t = self._infer_expr_type(e.operand)
            if operand_t is None:
                return None
            try:
                return unary_result_type(e.op, operand_t)
            except TypeError:
                return None
        if isinstance(e, AddressOfExpr):
            operand_t = self._infer_expr_type(e.operand)
            return PointerType(operand_t) if operand_t is not None else None
        if isinstance(e, DerefExpr):
            operand_t = self._infer_expr_type(e.operand)
            return operand_t.base if isinstance(operand_t, PointerType) else None
        return None

    def _infer_foreach_element_type(self, iterable_t: Optional[TypeNode]) -> Optional[TypeNode]:
        if isinstance(iterable_t, ArrayType):
            return iterable_t.base
        if isinstance(iterable_t, NamedType) and iterable_t.name == "string":
            return NamedType("char")
        return None
