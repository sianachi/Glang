from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from parser.ast_nodes import (
    Program, Stmt, Expr, TypeNode,
    FunctionDecl, ClassDecl, InterfaceDecl, EnumDecl, ModifierDecl, UnionDecl,
    Block, VarDecl, AssignStmt, IfStmt, WhileStmt, DoWhileStmt, ForStmt,
    ForeachStmt, ReturnStmt, BreakStmt, ContinueStmt, UsingStmt, ThrowStmt, TryCatchStmt, CatchClause,
    MatchStmt, MatchArm, VariantPattern, WildcardPattern,
    BinaryExpr, UnaryExpr, CastExpr, CallExpr, IndirectCallExpr, ClosureExpr,
    MethodCallExpr,
    NewExpr, DeleteExpr, AllocExpr, FreeExpr,
    FieldAccessExpr, ArrowAccessExpr, IndexExpr,
    AddressOfExpr, DerefExpr,
    IdentifierExpr, LiteralExpr, NullExpr, ThisExpr, SuperExpr,
    NamedType, PointerType, ManagedHandleType, FunctionPointerType, NullableType,
)
from errors.errors import TypeError
from analyser.symbol_table import GlobalEnv, ClassInfo, SymbolTable
from analyser.type_utils import (
    NULL_TYPE, is_assignable, is_integer, is_byte, is_bool,
    is_pointer, is_array, is_string, is_nullable, pointer_base, type_str,
    is_lvalue, binary_result_type, unary_result_type,
    superclass_chain, types_equal,
)
from analyser.return_checker import always_returns


_BINARY_OPERATOR_OVERLOADS = {"+", "-", "*", "/", "%", "==", "!=", "<", "<=", ">", ">="}
_COMPARISON_OPERATOR_OVERLOADS = {"==", "!=", "<", "<=", ">", ">="}
_ALL_OPERATOR_OVERLOADS = _BINARY_OPERATOR_OVERLOADS | {"[]"}


@dataclass
class ClosureContext:
    root: SymbolTable
    captures: Dict[str, TypeNode] = field(default_factory=dict)


class Pass2Checker:
    def __init__(self, env: GlobalEnv) -> None:
        self._env = env
        self._scope: SymbolTable = SymbolTable()
        self._return_type: Optional[TypeNode] = None
        self._current_class: Optional[ClassInfo] = None
        self._modifier_target_type: Optional[TypeNode] = None
        self._in_loop: bool = False
        self._in_static_method: bool = False
        self._in_constructor: bool = False
        self._closure_stack: List[ClosureContext] = []

    def check_program(self, program: Program) -> None:
        for decl in program.declarations:
            if isinstance(decl, FunctionDecl):
                self._check_function(decl)
            elif isinstance(decl, ClassDecl):
                info = self._env.classes[decl.name]
                self._check_class(decl, info)
            elif isinstance(decl, InterfaceDecl):
                self._check_interface(decl)
            elif isinstance(decl, EnumDecl):
                pass  # validated in pass1
            elif isinstance(decl, UnionDecl):
                pass  # validated in pass1
            elif isinstance(decl, ModifierDecl):
                self._check_modifier(decl)

    # ------------------------------------------------------------------
    # Declarations
    # ------------------------------------------------------------------

    def _check_function(self, fn: FunctionDecl) -> None:
        saved_scope = self._scope
        saved_return = self._return_type

        self._scope = self._scope.child()
        for p in fn.params:
            self._scope.define(p.name, p.type, p.line, p.col, p.is_const)
        self._return_type = fn.return_type

        self._check_block(fn.body)

        rt_name = fn.return_type.name if isinstance(fn.return_type, NamedType) else None
        if rt_name != "void":
            if not always_returns(fn.body.stmts):
                raise TypeError(
                    "not all code paths return a value", fn.line, fn.col
                )

        self._scope = saved_scope
        self._return_type = saved_return

    def _check_class(self, cls: ClassDecl, info: ClassInfo) -> None:
        saved_class = self._current_class
        saved_static = self._in_static_method
        self._current_class = info

        # Static field initializers
        for sfd in cls.static_fields:
            init_t = self._check_expr(sfd.initializer)
            if not self._assignable(init_t, sfd.type, sfd.initializer):
                raise TypeError(
                    f"cannot initialise '{type_str(sfd.type)}' with '{type_str(init_t)}'",
                    sfd.line, sfd.col,
                )

        # Constructor
        if cls.constructor:
            ctor = cls.constructor
            saved_scope = self._scope
            saved_return = self._return_type
            saved_ctor = self._in_constructor
            self._scope = self._scope.child()
            for p in ctor.params:
                self._scope.define(p.name, p.type, p.line, p.col, p.is_const)
            self._return_type = NamedType("void")
            self._in_static_method = False
            self._in_constructor = True

            if info.superclass is not None:
                if ctor.super_args is None:
                    raise TypeError(
                        "subclass constructor must call super(...)",
                        ctor.line, ctor.col,
                    )
                parent_info = self._env.classes[info.superclass]
                if parent_info.constructor is not None:
                    expected = len(parent_info.constructor.params)
                    got = len(ctor.super_args)
                    if expected != got:
                        raise TypeError(
                            f"super(...) expects {expected} arguments, got {got}",
                            ctor.line, ctor.col,
                        )
                    for arg, param in zip(ctor.super_args, parent_info.constructor.params):
                        arg_t = self._check_expr(arg)
                        if not self._assignable(arg_t, param.type, arg):
                            raise TypeError(
                                f"cannot assign '{type_str(arg_t)}' to '{type_str(param.type)}'",
                                ctor.line, ctor.col,
                            )
                else:
                    if ctor.super_args:
                        raise TypeError(
                            f"super(...) expects 0 arguments, got {len(ctor.super_args)}",
                            ctor.line, ctor.col,
                        )
            else:
                if ctor.super_args is not None:
                    raise TypeError(
                        "super() used in a class with no superclass",
                        ctor.line, ctor.col,
                    )

            self._check_block(ctor.body)
            self._scope = saved_scope
            self._return_type = saved_return
            self._in_constructor = saved_ctor

        # Destructor
        if cls.destructor:
            dtor = cls.destructor
            saved_scope = self._scope
            saved_return = self._return_type
            self._scope = self._scope.child()
            self._return_type = NamedType("void")
            self._in_static_method = False
            self._check_block(dtor.body)
            self._scope = saved_scope
            self._return_type = saved_return

        # Methods
        for md in cls.methods:
            saved_scope = self._scope
            saved_return = self._return_type
            self._scope = self._scope.child()
            for p in md.params:
                self._scope.define(p.name, p.type, p.line, p.col, p.is_const)
            self._return_type = md.return_type
            self._in_static_method = md.is_static

            self._check_operator_method_decl(md)
            self._check_block(md.body)

            rt_name = md.return_type.name if isinstance(md.return_type, NamedType) else None
            if rt_name != "void":
                if not always_returns(md.body.stmts):
                    raise TypeError(
                        "not all code paths return a value", md.line, md.col
                    )

            self._scope = saved_scope
            self._return_type = saved_return

        self._current_class = saved_class
        self._in_static_method = saved_static

    def _check_interface(self, iface: InterfaceDecl) -> None:
        pass  # signatures already validated in pass1

    def _check_modifier(self, decl: ModifierDecl) -> None:
        from analyser.type_utils import type_str as _type_str
        target_name = _type_str(decl.target)
        saved_class = self._current_class
        saved_modifier_target = self._modifier_target_type
        saved_static = self._in_static_method
        self._in_static_method = False

        class_info = self._env.classes.get(target_name)
        if class_info is not None:
            self._current_class = class_info
            self._modifier_target_type = None
        else:
            self._current_class = None
            self._modifier_target_type = decl.target

        for md in decl.methods:
            saved_scope = self._scope
            saved_return = self._return_type
            self._scope = self._scope.child()
            for p in md.params:
                self._scope.define(p.name, p.type, p.line, p.col, p.is_const)
            self._return_type = md.return_type
            self._check_block(md.body)
            rt_name = md.return_type.name if isinstance(md.return_type, NamedType) else None
            if rt_name != "void":
                from analyser.return_checker import always_returns
                if not always_returns(md.body.stmts):
                    raise TypeError(
                        "not all code paths return a value", md.line, md.col
                    )
            self._scope = saved_scope
            self._return_type = saved_return

        self._current_class = saved_class
        self._modifier_target_type = saved_modifier_target
        self._in_static_method = saved_static

    # ------------------------------------------------------------------
    # Statements
    # ------------------------------------------------------------------

    def _check_block(self, block: Block) -> None:
        saved = self._scope
        self._scope = self._scope.child()
        for stmt in block.stmts:
            self._check_stmt(stmt)
        self._scope = saved

    def _check_stmt(self, stmt: Stmt) -> None:
        if isinstance(stmt, Block):
            self._check_block(stmt)

        elif isinstance(stmt, VarDecl):
            init_t = self._check_expr(stmt.initializer)
            if self._is_var_type(stmt.type):
                if self._is_null_type(init_t):
                    raise TypeError(
                        "cannot infer type of 'var' from null",
                        stmt.line, stmt.col,
                    )
                if isinstance(init_t, NamedType) and init_t.name == "void":
                    raise TypeError(
                        "cannot infer type of 'var' from void",
                        stmt.line, stmt.col,
                    )
                stmt.type = init_t
            else:
                self._env.resolve_type(stmt.type)
                self._check_class_access(stmt.type, stmt.line, stmt.col)
            if not self._assignable(init_t, stmt.type, stmt.initializer):
                raise TypeError(
                    f"cannot initialise '{type_str(stmt.type)}' with '{type_str(init_t)}'",
                    stmt.line, stmt.col,
                )
            self._scope.define(stmt.name, stmt.type, stmt.line, stmt.col, stmt.is_const)

        elif isinstance(stmt, AssignStmt):
            if not is_lvalue(stmt.target):
                raise TypeError(
                    f"left-hand side of '=' is not assignable", stmt.line, stmt.col
                )
            if self._is_static_method_ref(stmt.target):
                raise TypeError(
                    f"left-hand side of '=' is not assignable", stmt.line, stmt.col
                )
            target_t = self._check_assignable_target(stmt.target)
            value_t = self._check_expr(stmt.value)

            if stmt.op != "=":
                # Compound assignment: validate the op makes sense for target_t
                op_symbol = stmt.op[:-1]  # e.g. "+=" → "+"
                lhs_t, rhs_t = self._coerce_byte_literals(
                    target_t, value_t, stmt.target, stmt.value
                )
                value_t = self._check_binary_operation_type(
                    op_symbol, lhs_t, rhs_t, stmt.line, stmt.col
                )

            if not self._assignable(value_t, target_t, stmt.value):
                raise TypeError(
                    f"cannot assign '{type_str(value_t)}' to '{type_str(target_t)}'",
                    stmt.line, stmt.col,
                )

            # const check
            if isinstance(stmt.target, IdentifierExpr):
                if self._scope.is_const_var(stmt.target.name):
                    raise TypeError(
                        f"cannot assign to const '{stmt.target.name}'",
                        stmt.line, stmt.col,
                    )
            elif isinstance(stmt.target, (FieldAccessExpr, ArrowAccessExpr)):
                field_name = stmt.target.field_name
                class_info = self._resolve_target_class_info(stmt.target)
                if class_info:
                    # Instance field const check
                    fd = class_info.fields.get(field_name)
                    if fd and fd.is_const:
                        receiver = (stmt.target.object
                                    if isinstance(stmt.target, FieldAccessExpr)
                                    else None)
                        receiver_is_this = isinstance(receiver, ThisExpr)
                        if not (self._in_constructor and receiver_is_this):
                            raise TypeError(
                                f"cannot assign to const field '{field_name}'",
                                stmt.line, stmt.col,
                            )
                    # Static field const check
                    sfd = class_info.static_fields.get(field_name)
                    if sfd and sfd.is_const:
                        raise TypeError(
                            f"cannot assign to const field '{field_name}'",
                            stmt.line, stmt.col,
                        )

        elif isinstance(stmt, IfStmt):
            cond_t = self._check_expr(stmt.condition)
            if not is_bool(cond_t):
                raise TypeError(
                    f"condition must be bool, got '{type_str(cond_t)}'",
                    stmt.line, stmt.col,
                )
            self._check_block(stmt.then_branch)
            if stmt.else_branch is not None:
                if isinstance(stmt.else_branch, IfStmt):
                    self._check_stmt(stmt.else_branch)
                else:
                    self._check_block(stmt.else_branch)

        elif isinstance(stmt, WhileStmt):
            cond_t = self._check_expr(stmt.condition)
            if not is_bool(cond_t):
                raise TypeError(
                    f"condition must be bool, got '{type_str(cond_t)}'",
                    stmt.line, stmt.col,
                )
            saved_loop = self._in_loop
            self._in_loop = True
            self._check_block(stmt.body)
            self._in_loop = saved_loop

        elif isinstance(stmt, DoWhileStmt):
            saved_loop = self._in_loop
            self._in_loop = True
            self._check_block(stmt.body)
            self._in_loop = saved_loop
            cond_t = self._check_expr(stmt.condition)
            if not is_bool(cond_t):
                raise TypeError(
                    f"condition must be bool, got '{type_str(cond_t)}'",
                    stmt.line, stmt.col,
                )

        elif isinstance(stmt, ForStmt):
            saved_scope = self._scope
            self._scope = self._scope.child()
            self._check_stmt(stmt.init)
            cond_t = self._check_expr(stmt.condition)
            if not is_bool(cond_t):
                raise TypeError(
                    f"condition must be bool, got '{type_str(cond_t)}'",
                    stmt.line, stmt.col,
                )
            self._check_stmt(stmt.post)
            saved_loop = self._in_loop
            self._in_loop = True
            self._check_block(stmt.body)
            self._in_loop = saved_loop
            self._scope = saved_scope

        elif isinstance(stmt, ForeachStmt):
            iterable_t = self._check_expr(stmt.iterable)
            elem_t = self._foreach_element_type(iterable_t, stmt.line, stmt.col)
            if self._is_var_type(stmt.var_type):
                stmt.var_type = elem_t
            else:
                self._env.resolve_type(stmt.var_type)
                self._check_class_access(stmt.var_type, stmt.line, stmt.col)
            if not is_assignable(elem_t, stmt.var_type, self._env):
                raise TypeError(
                    f"cannot iterate '{type_str(iterable_t)}' as '{type_str(stmt.var_type)}'",
                    stmt.line, stmt.col,
                )
            saved_scope = self._scope
            self._scope = self._scope.child()
            self._scope.define(
                stmt.var_name,
                stmt.var_type,
                stmt.line,
                stmt.col,
                stmt.is_const,
            )
            saved_loop = self._in_loop
            self._in_loop = True
            self._check_block(stmt.body)
            self._in_loop = saved_loop
            self._scope = saved_scope

        elif isinstance(stmt, UsingStmt):
            saved_scope = self._scope
            self._scope = self._scope.child()
            self._check_stmt(stmt.decl)
            self._validate_disposable(stmt.decl.type, stmt.line, stmt.col)
            self._check_block(stmt.body)
            self._scope = saved_scope

        elif isinstance(stmt, ReturnStmt):
            rt = self._return_type
            rt_name = rt.name if isinstance(rt, NamedType) else None
            if rt_name == "void":
                if stmt.value is not None:
                    raise TypeError(
                        "void function must not return a value",
                        stmt.line, stmt.col,
                    )
            else:
                if stmt.value is None:
                    raise TypeError(
                        "non-void function must return a value",
                        stmt.line, stmt.col,
                    )
                val_t = self._check_expr(stmt.value)
                if not self._assignable(val_t, rt, stmt.value):
                    raise TypeError(
                        f"cannot assign '{type_str(val_t)}' to '{type_str(rt)}'",
                        stmt.line, stmt.col,
                    )

        elif isinstance(stmt, BreakStmt):
            if not self._in_loop:
                raise TypeError("'break' outside a loop", stmt.line, stmt.col)

        elif isinstance(stmt, ContinueStmt):
            if not self._in_loop:
                raise TypeError("'continue' outside a loop", stmt.line, stmt.col)

        elif isinstance(stmt, ThrowStmt):
            val_t = self._check_expr(stmt.value)
            if not isinstance(val_t, PointerType):
                raise TypeError(
                    f"'throw' requires a pointer to an Exception subclass, got '{type_str(val_t)}'",
                    stmt.line, stmt.col,
                )
            base = val_t.base
            if not (isinstance(base, NamedType) and self._env.is_class(base.name)):
                raise TypeError(
                    f"'throw' requires a pointer to a class, got '{type_str(val_t)}'",
                    stmt.line, stmt.col,
                )
            chain = superclass_chain(base.name, self._env)
            if "Exception" not in chain:
                raise TypeError(
                    f"'{base.name}' does not extend Exception",
                    stmt.line, stmt.col,
                )

        elif isinstance(stmt, TryCatchStmt):
            self._check_block(stmt.body)
            for clause in stmt.catches:
                ct = clause.catch_type
                if not isinstance(ct, PointerType):
                    raise TypeError(
                        f"catch type must be a pointer to an Exception subclass, got '{type_str(ct)}'",
                        clause.line, clause.col,
                    )
                base = ct.base
                if not (isinstance(base, NamedType) and self._env.is_class(base.name)):
                    raise TypeError(
                        f"catch type must be a pointer to a class, got '{type_str(ct)}'",
                        clause.line, clause.col,
                    )
                chain = superclass_chain(base.name, self._env)
                if "Exception" not in chain:
                    raise TypeError(
                        f"'{base.name}' does not extend Exception",
                        clause.line, clause.col,
                    )
                saved_scope = self._scope
                self._scope = self._scope.child()
                self._scope.define(clause.var_name, ct, clause.line, clause.col, False)
                self._check_block(clause.body)
                self._scope = saved_scope

        elif isinstance(stmt, MatchStmt):
            self._check_match(stmt)

        else:
            # bare expression statement
            self._check_expr(stmt)

    def _validate_disposable(self, t: TypeNode, line: int, col: int) -> None:
        """A `using` resource must have a deterministic release action:
        pointers are deleted/freed; class values need a dispose() method."""
        if isinstance(t, PointerType):
            return
        if isinstance(t, NamedType) and self._env.is_class(t.name):
            info = self._env.classes[t.name]
            dispose = info.instance_methods.get("dispose")
            if dispose is not None and len(dispose.params) == 0:
                return
            raise TypeError(
                f"'using' value of class '{t.name}' needs a zero-argument "
                f"dispose() method",
                line, col,
            )
        raise TypeError(
            f"'using' requires a pointer or a class value with dispose(), "
            f"got '{type_str(t)}'",
            line, col,
        )

    def _check_match(self, stmt: MatchStmt) -> None:
        scrutinee_t = self._check_expr(stmt.scrutinee)
        # Allow pointer-to-union: auto-unwrap.
        if isinstance(scrutinee_t, PointerType) and isinstance(scrutinee_t.base, NamedType):
            scrutinee_t = scrutinee_t.base
        if not (isinstance(scrutinee_t, NamedType) and self._env.is_union(scrutinee_t.name)):
            raise TypeError(
                f"match scrutinee must be a union type, got '{type_str(scrutinee_t)}'",
                stmt.line, stmt.col,
            )
        union_info = self._env.unions[scrutinee_t.name]
        covered = set()
        has_wildcard = False
        for arm in stmt.arms:
            if isinstance(arm.pattern, WildcardPattern):
                has_wildcard = True
                self._check_block(arm.body)
            else:
                p = arm.pattern
                if p.union_name != scrutinee_t.name:
                    raise TypeError(
                        f"pattern union '{p.union_name}' does not match "
                        f"scrutinee type '{scrutinee_t.name}'",
                        arm.line, arm.col,
                    )
                variant = union_info.variants.get(p.variant_name)
                if variant is None:
                    raise TypeError(
                        f"'{scrutinee_t.name}' has no variant '{p.variant_name}'",
                        arm.line, arm.col,
                    )
                if len(p.bindings) != len(variant.fields):
                    raise TypeError(
                        f"variant '{p.variant_name}' has {len(variant.fields)} field(s), "
                        f"but pattern binds {len(p.bindings)}",
                        arm.line, arm.col,
                    )
                covered.add(p.variant_name)
                saved_scope = self._scope
                self._scope = self._scope.child()
                for binding, fd in zip(p.bindings, variant.fields):
                    self._scope.define(binding, fd.type, arm.line, arm.col, False)
                self._check_block(arm.body)
                self._scope = saved_scope
        if not has_wildcard:
            missing = set(union_info.variants.keys()) - covered
            if missing:
                raise TypeError(
                    f"non-exhaustive match: missing variants {sorted(missing)}",
                    stmt.line, stmt.col,
                )

    # ------------------------------------------------------------------
    # Expressions
    # ------------------------------------------------------------------

    def _check_expr(self, expr: Expr) -> TypeNode:
        if isinstance(expr, LiteralExpr):
            return NamedType(expr.kind)

        if isinstance(expr, NullExpr):
            return NULL_TYPE

        if isinstance(expr, ClosureExpr):
            return self._check_closure(expr)

        if isinstance(expr, IdentifierExpr):
            defining_scope = self._scope.find_scope(expr.name)
            if defining_scope is not None:
                entry = defining_scope.entry(expr.name)
                self._record_capture(expr.name, defining_scope)
                return entry[0]
            fn_info = self._env.functions.get(expr.name)
            if fn_info is not None:
                return self._function_type_from_params(
                    fn_info.params, fn_info.return_type,
                    line=expr.line, col=expr.col,
                )
            raise TypeError(
                f"undefined variable '{expr.name}'", expr.line, expr.col
            )

        if isinstance(expr, ThisExpr):
            if self._in_static_method:
                raise TypeError(
                    "'this' is not available in a static method",
                    expr.line, expr.col,
                )
            if self._modifier_target_type is not None:
                # Primitive modifier: 'this' is the target value itself.
                return self._modifier_target_type
            if self._current_class is None:
                raise TypeError(
                    "'this' used outside of a class or modifier",
                    expr.line, expr.col,
                )
            if self._current_class.is_managed:
                return ManagedHandleType(NamedType(self._current_class.name))
            return PointerType(NamedType(self._current_class.name))

        if isinstance(expr, SuperExpr):
            if self._current_class is None or self._current_class.superclass is None:
                raise TypeError(
                    "'super' used in a class with no superclass",
                    expr.line, expr.col,
                )
            return PointerType(NamedType(self._current_class.superclass))

        if isinstance(expr, UnaryExpr):
            operand_t = self._check_expr(expr.operand)
            if expr.op in ("++", "--"):
                if not is_lvalue(expr.operand):
                    raise TypeError(
                        f"operand of '{expr.op}' must be an lvalue",
                        expr.line, expr.col,
                    )
            return unary_result_type(expr.op, operand_t)

        if isinstance(expr, AddressOfExpr):
            if not is_lvalue(expr.operand):
                raise TypeError(
                    "operand of '&' must be an lvalue", expr.line, expr.col
                )
            t = self._check_assignable_target(expr.operand)
            return PointerType(t)

        if isinstance(expr, DerefExpr):
            t = self._check_expr(expr.operand)
            if not is_pointer(t):
                raise TypeError(
                    f"'*' requires a pointer, got '{type_str(t)}'",
                    expr.line, expr.col,
                )
            return pointer_base(t)

        if isinstance(expr, CastExpr):
            self._env.resolve_type(expr.target_type)
            src_t = self._check_expr(expr.expr)
            self._validate_cast(src_t, expr.target_type, expr.line, expr.col)
            return expr.target_type

        if isinstance(expr, BinaryExpr):
            left_t = self._check_expr(expr.left)
            right_t = self._check_expr(expr.right)
            left_t, right_t = self._coerce_byte_literals(
                left_t, right_t, expr.left, expr.right
            )
            return self._check_binary_operation_type(
                expr.op, left_t, right_t, expr.line, expr.col
            )

        if isinstance(expr, CallExpr):
            defining_scope = self._scope.find_scope(expr.name)
            if defining_scope is not None:
                entry = defining_scope.entry(expr.name)
                callee_t = entry[0]
                if not isinstance(callee_t, FunctionPointerType):
                    raise TypeError(
                        f"'{expr.name}' is not callable", expr.line, expr.col
                    )
                return self._check_callable_args(
                    expr.name, expr.args, callee_t.param_types,
                    callee_t.return_type, expr.line, expr.col,
                )

            builtin_t = self._check_builtin_call(expr)
            if builtin_t is not None:
                return builtin_t

            fn_info = self._env.functions.get(expr.name)
            if fn_info is not None:
                return self._check_callable_args(
                    expr.name, expr.args, [p.type for p in fn_info.params],
                    fn_info.return_type, expr.line, expr.col,
                )

            # Stack constructor call: Dog("Rex") where Dog is a class name
            class_info = self._env.classes.get(expr.name)
            if class_info is not None:
                ctor = class_info.constructor
                if ctor is not None:
                    expected = len(ctor.params)
                    got = len(expr.args)
                    if expected != got:
                        raise TypeError(
                            f"'{expr.name}' expects {expected} arguments, got {got}",
                            expr.line, expr.col,
                        )
                    for arg, param in zip(expr.args, ctor.params):
                        arg_t = self._check_expr(arg)
                        if not self._assignable(arg_t, param.type, arg):
                            raise TypeError(
                                f"cannot assign '{type_str(arg_t)}' to '{type_str(param.type)}'",
                                expr.line, expr.col,
                            )
                else:
                    if expr.args:
                        raise TypeError(
                            f"'{expr.name}' expects 0 arguments, got {len(expr.args)}",
                            expr.line, expr.col,
                        )
                return NamedType(expr.name)

            raise TypeError(
                f"undefined function '{expr.name}'", expr.line, expr.col
            )

        if isinstance(expr, IndirectCallExpr):
            callee_t = self._check_expr(expr.callee)
            if not isinstance(callee_t, FunctionPointerType):
                raise TypeError(
                    f"'{type_str(callee_t)}' is not callable",
                    expr.line, expr.col,
                )
            return self._check_callable_args(
                "function pointer", expr.args, callee_t.param_types,
                callee_t.return_type, expr.line, expr.col,
            )

        if isinstance(expr, MethodCallExpr):
            # Union variant constructor: Expr.Number(42)
            if (
                not expr.is_arrow
                and isinstance(expr.object, IdentifierExpr)
                and self._env.is_union(expr.object.name)
                and self._scope._find(expr.object.name) is None
            ):
                union_info = self._env.unions[expr.object.name]
                variant = union_info.variants.get(expr.method)
                if variant is None:
                    raise TypeError(
                        f"'{expr.object.name}' has no variant '{expr.method}'",
                        expr.line, expr.col,
                    )
                if len(expr.args) != len(variant.fields):
                    raise TypeError(
                        f"variant '{expr.method}' expects {len(variant.fields)} "
                        f"argument(s), got {len(expr.args)}",
                        expr.line, expr.col,
                    )
                for arg, fd in zip(expr.args, variant.fields):
                    arg_t = self._check_expr(arg)
                    if not self._assignable(arg_t, fd.type, arg):
                        raise TypeError(
                            f"cannot assign '{type_str(arg_t)}' to '{type_str(fd.type)}'",
                            expr.line, expr.col,
                        )
                return NamedType(expr.object.name)

            # Static method call: ClassName.method(args)
            if (
                not expr.is_arrow
                and isinstance(expr.object, IdentifierExpr)
                and self._env.is_class(expr.object.name)
                and self._scope._find(expr.object.name) is None
            ):
                class_info = self._env.classes[expr.object.name]
                method = class_info.static_methods.get(expr.method)
                if method is None:
                    raise TypeError(
                        f"'{expr.object.name}' has no method '{expr.method}'",
                        expr.line, expr.col,
                    )
                expected = len(method.params)
                got = len(expr.args)
                if expected != got:
                    raise TypeError(
                        f"'{expr.method}' expects {expected} arguments, got {got}",
                        expr.line, expr.col,
                    )
                for arg, param in zip(expr.args, method.params):
                    arg_t = self._check_expr(arg)
                    if not self._assignable(arg_t, param.type, arg):
                        raise TypeError(
                            f"cannot assign '{type_str(arg_t)}' to '{type_str(param.type)}'",
                            expr.line, expr.col,
                        )
                return method.return_type

            obj_t = self._check_expr(expr.object)
            if expr.is_arrow:
                if not is_pointer(obj_t):
                    raise TypeError(
                        f"'->' requires a pointer, got '{type_str(obj_t)}'",
                        expr.line, expr.col,
                    )
                class_t = pointer_base(obj_t)
            elif isinstance(obj_t, ManagedHandleType) and isinstance(obj_t.base, NamedType):
                # Managed handles use dot access like a class reference.
                class_t = obj_t.base
            elif isinstance(obj_t, PointerType) and isinstance(obj_t.base, NamedType):
                # Auto-deref: this.method() / super.method() via dot notation
                class_t = obj_t.base
            else:
                class_t = obj_t

            if not isinstance(class_t, NamedType):
                raise TypeError(
                    f"'{type_str(obj_t)}' has no method '{expr.method}'",
                    expr.line, expr.col,
                )
            class_info = self._env.classes.get(class_t.name)
            if class_info is None:
                # Primitive type or unrecognised — check modifier methods.
                method = self._env.modifier_methods.get(class_t.name, {}).get(expr.method)
                if method is None:
                    raise TypeError(
                        f"'{class_t.name}' has no method '{expr.method}'",
                        expr.line, expr.col,
                    )
            else:
                method = class_info.instance_methods.get(expr.method)
                if method is None:
                    method = self._env.modifier_methods.get(class_t.name, {}).get(expr.method)
                if method is None:
                    raise TypeError(
                        f"'{class_t.name}' has no method '{expr.method}'",
                        expr.line, expr.col,
                    )
                if method in class_info.instance_methods.values():
                    self._check_access(class_t.name, method.access, expr.method,
                                       expr.line, expr.col)
            expected = len(method.params)
            got = len(expr.args)
            if expected != got:
                raise TypeError(
                    f"'{expr.method}' expects {expected} arguments, got {got}",
                    expr.line, expr.col,
                )
            for arg, param in zip(expr.args, method.params):
                arg_t = self._check_expr(arg)
                if not self._assignable(arg_t, param.type, arg):
                    raise TypeError(
                        f"cannot assign '{type_str(arg_t)}' to '{type_str(param.type)}'",
                        expr.line, expr.col,
                    )
            return method.return_type

        if isinstance(expr, FieldAccessExpr):
            # Union no-field variant access: Expr.Nil
            if (
                isinstance(expr.object, IdentifierExpr)
                and self._env.is_union(expr.object.name)
                and self._scope._find(expr.object.name) is None
            ):
                union_info = self._env.unions[expr.object.name]
                variant = union_info.variants.get(expr.field_name)
                if variant is None:
                    raise TypeError(
                        f"'{expr.object.name}' has no variant '{expr.field_name}'",
                        expr.line, expr.col,
                    )
                if variant.fields:
                    raise TypeError(
                        f"variant '{expr.field_name}' has fields; "
                        f"use '{expr.object.name}.{expr.field_name}(...)' to construct it",
                        expr.line, expr.col,
                    )
                return NamedType(expr.object.name)

            # Enum variant access: Color.RED
            if (
                isinstance(expr.object, IdentifierExpr)
                and self._env.is_enum(expr.object.name)
                and self._scope._find(expr.object.name) is None
            ):
                enum_info = self._env.enums[expr.object.name]
                if expr.field_name not in enum_info.variants:
                    raise TypeError(
                        f"'{expr.object.name}' has no variant '{expr.field_name}'",
                        expr.line, expr.col,
                    )
                return NamedType(expr.object.name)

            # Static field access: ClassName.field
            if (
                isinstance(expr.object, IdentifierExpr)
                and self._env.is_class(expr.object.name)
                and self._scope._find(expr.object.name) is None
            ):
                class_info = self._env.classes[expr.object.name]
                sfd = class_info.static_fields.get(expr.field_name)
                if sfd is not None:
                    self._check_access(expr.object.name, sfd.access, expr.field_name,
                                       expr.line, expr.col)
                    return sfd.type
                method = class_info.static_methods.get(expr.field_name)
                if method is not None:
                    self._check_access(expr.object.name, method.access,
                                       expr.field_name, expr.line, expr.col)
                    return self._function_type_from_params(
                        method.params, method.return_type,
                        line=expr.line, col=expr.col,
                    )
                raise TypeError(
                    f"'{expr.object.name}' has no field '{expr.field_name}'",
                    expr.line, expr.col,
                )

            obj_t = self._check_expr(expr.object)
            # Auto-deref: `this.field` uses FieldAccessExpr with a pointer receiver;
            # managed handles use dot access like a class reference.
            if isinstance(obj_t, (PointerType, ManagedHandleType)) and isinstance(obj_t.base, NamedType):
                class_t = obj_t.base
            elif isinstance(obj_t, NamedType):
                class_t = obj_t
            else:
                raise TypeError(
                    f"'{type_str(obj_t)}' has no field '{expr.field_name}'",
                    expr.line, expr.col,
                )
            class_info = self._env.classes.get(class_t.name)
            if class_info is None:
                raise TypeError(
                    f"'{class_t.name}' has no field '{expr.field_name}'",
                    expr.line, expr.col,
                )
            fd = class_info.fields.get(expr.field_name)
            if fd is None:
                raise TypeError(
                    f"'{class_t.name}' has no field '{expr.field_name}'",
                    expr.line, expr.col,
                )
            defining = self._field_declaring_class(class_t.name, expr.field_name)
            self._check_access(defining, fd.access, expr.field_name, expr.line, expr.col)
            return fd.type

        if isinstance(expr, ArrowAccessExpr):
            ptr_t = self._check_expr(expr.pointer)
            if not is_pointer(ptr_t):
                raise TypeError(
                    f"'->' requires a pointer, got '{type_str(ptr_t)}'",
                    expr.line, expr.col,
                )
            class_t = pointer_base(ptr_t)
            if not isinstance(class_t, NamedType):
                raise TypeError(
                    f"'{type_str(ptr_t)}' has no field '{expr.field_name}'",
                    expr.line, expr.col,
                )
            class_info = self._env.classes.get(class_t.name)
            if class_info is None:
                raise TypeError(
                    f"'{class_t.name}' has no field '{expr.field_name}'",
                    expr.line, expr.col,
                )
            fd = class_info.fields.get(expr.field_name)
            if fd is None:
                raise TypeError(
                    f"'{class_t.name}' has no field '{expr.field_name}'",
                    expr.line, expr.col,
                )
            defining = self._field_declaring_class(class_t.name, expr.field_name)
            self._check_access(defining, fd.access, expr.field_name, expr.line, expr.col)
            return fd.type

        if isinstance(expr, IndexExpr):
            return self._check_index_expr(expr)

        if isinstance(expr, NewExpr):
            # Union variant heap allocation: new Shape.Circle(args) → Shape*
            if "." in expr.class_name:
                union_name, variant_name = expr.class_name.split(".", 1)
                if not self._env.is_union(union_name):
                    raise TypeError(
                        f"unknown union '{union_name}'", expr.line, expr.col
                    )
                union_info = self._env.unions[union_name]
                variant = union_info.variants.get(variant_name)
                if variant is None:
                    raise TypeError(
                        f"'{union_name}' has no variant '{variant_name}'",
                        expr.line, expr.col,
                    )
                if len(expr.args) != len(variant.fields):
                    raise TypeError(
                        f"variant '{variant_name}' expects {len(variant.fields)} "
                        f"argument(s), got {len(expr.args)}",
                        expr.line, expr.col,
                    )
                for arg, fd in zip(expr.args, variant.fields):
                    arg_t = self._check_expr(arg)
                    if not self._assignable(arg_t, fd.type, arg):
                        raise TypeError(
                            f"cannot assign '{type_str(arg_t)}' to '{type_str(fd.type)}'",
                            expr.line, expr.col,
                        )
                return PointerType(NamedType(union_name))

            if expr.class_name not in self._env.classes:
                raise TypeError(
                    f"unknown class '{expr.class_name}'", expr.line, expr.col
                )
            class_info = self._env.classes[expr.class_name]
            self._check_class_access(NamedType(expr.class_name,
                                               line=expr.line, col=expr.col),
                                     expr.line, expr.col)
            if class_info.constructor is not None:
                expected = len(class_info.constructor.params)
                got = len(expr.args)
                if expected != got:
                    raise TypeError(
                        f"'{expr.class_name}' expects {expected} arguments, got {got}",
                        expr.line, expr.col,
                    )
                for arg, param in zip(expr.args, class_info.constructor.params):
                    arg_t = self._check_expr(arg)
                    if not self._assignable(arg_t, param.type, arg):
                        raise TypeError(
                            f"cannot assign '{type_str(arg_t)}' to '{type_str(param.type)}'",
                            expr.line, expr.col,
                        )
            else:
                if expr.args:
                    raise TypeError(
                        f"'{expr.class_name}' expects 0 arguments, got {len(expr.args)}",
                        expr.line, expr.col,
                    )
            # `new` on a managed class yields a managed handle (T@), which the
            # runtime reclaims automatically; on a regular class it yields T*.
            if class_info.is_managed:
                return ManagedHandleType(NamedType(expr.class_name))
            return PointerType(NamedType(expr.class_name))

        if isinstance(expr, DeleteExpr):
            t = self._check_expr(expr.operand)
            if isinstance(t, ManagedHandleType):
                raise TypeError(
                    "'delete' cannot be used on a managed handle; managed "
                    "objects are reclaimed automatically",
                    expr.line, expr.col,
                )
            if not is_pointer(t):
                raise TypeError(
                    "'delete' requires a pointer to a class",
                    expr.line, expr.col,
                )
            base = pointer_base(t)
            is_deletable = (
                isinstance(base, NamedType)
                and (self._env.is_class(base.name) or self._env.is_union(base.name))
            )
            if not is_deletable:
                raise TypeError(
                    "'delete' requires a pointer to a class or union",
                    expr.line, expr.col,
                )
            return NamedType("void")

        if isinstance(expr, AllocExpr):
            self._env.resolve_type(expr.type)
            if isinstance(expr.type, NamedType) and expr.type.name == "void":
                raise TypeError("cannot alloc void", expr.line, expr.col)
            if expr.count is not None:
                count_t = self._check_expr(expr.count)
                if not is_integer(count_t):
                    raise TypeError(
                        f"alloc count must be int, got '{type_str(count_t)}'",
                        expr.line, expr.col,
                    )
            return PointerType(expr.type)

        if isinstance(expr, FreeExpr):
            t = self._check_expr(expr.operand)
            if not is_pointer(t):
                raise TypeError(
                    f"'free' requires a pointer", expr.line, expr.col
                )
            return NamedType("void")

        raise TypeError(
            f"unknown expression type '{type(expr).__name__}'", 0, 0
        )

    def _check_builtin_call(self, expr: CallExpr) -> Optional[TypeNode]:
        if expr.name == "print":
            if len(expr.args) != 1:
                raise TypeError(
                    f"'print' expects 1 argument, got {len(expr.args)}",
                    expr.line, expr.col,
                )
            arg_t = self._check_expr(expr.args[0])
            if not self._is_primitive_value_type(arg_t):
                raise TypeError(
                    f"'print' requires a primitive argument, got '{type_str(arg_t)}'",
                    expr.line, expr.col,
                )
            return NamedType("void")

        if expr.name == "printErr":
            if len(expr.args) != 1:
                raise TypeError(
                    f"'printErr' expects 1 argument, got {len(expr.args)}",
                    expr.line, expr.col,
                )
            arg_t = self._check_expr(expr.args[0])
            if not self._is_primitive_value_type(arg_t):
                raise TypeError(
                    f"'printErr' requires a primitive argument, got '{type_str(arg_t)}'",
                    expr.line, expr.col,
                )
            return NamedType("void")

        if expr.name == "len":
            if len(expr.args) != 1:
                raise TypeError(
                    f"'len' expects 1 argument, got {len(expr.args)}",
                    expr.line, expr.col,
                )
            arg_t = self._check_expr(expr.args[0])
            if not (is_string(arg_t) or is_array(arg_t)):
                raise TypeError(
                    f"'len' requires string or array, got '{type_str(arg_t)}'",
                    expr.line, expr.col,
                )
            return NamedType("int")

        if expr.name == "toString":
            if len(expr.args) != 1:
                raise TypeError(
                    f"'toString' expects 1 argument, got {len(expr.args)}",
                    expr.line, expr.col,
                )
            arg_t = self._check_expr(expr.args[0])
            if not self._is_primitive_value_type(arg_t):
                raise TypeError(
                    f"'toString' requires a primitive argument, got '{type_str(arg_t)}'",
                    expr.line, expr.col,
                )
            return NamedType("string")

        fixed = {
            "substr": (
                [NamedType("string"), NamedType("int"), NamedType("int")],
                NamedType("string"),
            ),
            "parseInt": ([NamedType("string")], NamedType("int")),
            "parseFloat": ([NamedType("string")], NamedType("float")),
            "startsWith": (
                [NamedType("string"), NamedType("string")],
                NamedType("bool"),
            ),
            "endsWith": (
                [NamedType("string"), NamedType("string")],
                NamedType("bool"),
            ),
            "contains": (
                [NamedType("string"), NamedType("string")],
                NamedType("bool"),
            ),
            "indexOf": (
                [NamedType("string"), NamedType("string")],
                NamedType("int"),
            ),
            "readFile": ([NamedType("string")], NamedType("string")),
            "writeFile": (
                [NamedType("string"), NamedType("string")],
                NamedType("void"),
            ),
            "fileExists": ([NamedType("string")], NamedType("bool")),
            "bytesFromString": (
                [NamedType("string")],
                PointerType(NamedType("byte")),
            ),
            "stringFromBytes": (
                [PointerType(NamedType("byte")), NamedType("int")],
                NamedType("string"),
            ),
            "getArgCount": ([], NamedType("int")),
            "getArg": ([NamedType("int")], NamedType("string")),
            "exit": ([NamedType("int")], NamedType("void")),
            "intToStr": ([NamedType("int")], NamedType("string")),
            "readStdin": ([], NamedType("string")),
        }
        signature = fixed.get(expr.name)
        if signature is None:
            return None
        param_types, return_type = signature
        return self._check_callable_args(
            expr.name, expr.args, param_types, return_type,
            expr.line, expr.col,
        )

    def _is_primitive_value_type(self, t: TypeNode) -> bool:
        return (
            isinstance(t, NamedType)
            and t.name in ("int", "float", "bool", "char", "byte", "string")
        )

    def _is_byte_literal(self, e: Expr) -> bool:
        """True if `e` is an integer literal usable as a byte (0..255).
        Raises on an out-of-range literal."""
        if isinstance(e, LiteralExpr) and e.kind == "int":
            val = int(e.value)
            if val < 0 or val > 255:
                raise TypeError(
                    f"byte literal out of range 0..255: {val}", e.line, e.col
                )
            return True
        return False

    def _coerce_byte_literals(
        self, left_t: TypeNode, right_t: TypeNode, left_e: Expr, right_e: Expr
    ) -> tuple:
        """For a binary op mixing a `byte` operand with an integer *literal*,
        treat the literal as `byte` so idioms like `b & 0x0F` and `b << 1`
        type-check (a byte never meets a non-literal int — that needs a cast)."""
        if is_byte(left_t) and not is_byte(right_t) and self._is_byte_literal(right_e):
            return left_t, NamedType("byte")
        if is_byte(right_t) and not is_byte(left_t) and self._is_byte_literal(left_e):
            return NamedType("byte"), right_t
        return left_t, right_t

    def _assignable(self, from_t: TypeNode, to_t: TypeNode, from_expr: Expr) -> bool:
        """Like ``is_assignable``, but also accepts an integer *literal* in the
        range 0..255 where a ``byte`` is expected (implicit byte-literal
        coercion). An out-of-range literal is a compile-time error; an ``int``
        *variable* still needs an explicit ``(byte)`` cast."""
        if is_assignable(from_t, to_t, self._env):
            return True
        if (
            is_byte(to_t)
            and isinstance(from_expr, LiteralExpr)
            and from_expr.kind == "int"
        ):
            val = int(from_expr.value)
            if val < 0 or val > 255:
                raise TypeError(
                    f"byte literal out of range 0..255: {val}",
                    from_expr.line, from_expr.col,
                )
            return True
        return False

    def _check_assignable_target(self, expr: Expr) -> TypeNode:
        if isinstance(expr, IndexExpr):
            return self._check_index_expr(expr, require_lvalue=True)
        return self._check_expr(expr)

    def _check_index_expr(
        self,
        expr: IndexExpr,
        *,
        require_lvalue: bool = False,
    ) -> TypeNode:
        container_t = self._check_expr(expr.array)
        idx_t = self._check_expr(expr.index)

        if is_array(container_t):
            if not is_integer(idx_t):
                raise TypeError(
                    f"array index must be int, got '{type_str(idx_t)}'",
                    expr.line, expr.col,
                )
            return container_t.base

        if is_pointer(container_t):
            if not is_integer(idx_t):
                raise TypeError(
                    f"pointer index must be int, got '{type_str(idx_t)}'",
                    expr.line, expr.col,
                )
            return pointer_base(container_t)

        if is_string(container_t):
            if not is_integer(idx_t):
                raise TypeError(
                    f"string index must be int, got '{type_str(idx_t)}'",
                    expr.line, expr.col,
                )
            if require_lvalue:
                raise TypeError("string index is not assignable", expr.line, expr.col)
            return NamedType("char")

        class_name = self._class_value_name(container_t)
        if class_name is not None:
            if require_lvalue:
                raise TypeError("operator[] result is not assignable", expr.line, expr.col)
            method, defining = self._find_instance_method(class_name, "operator[]")
            if method is None:
                raise TypeError(
                    f"'{class_name}' has no operator[]",
                    expr.line, expr.col,
                )
            self._check_access(defining, method.access, method.name,
                               expr.line, expr.col)
            return self._check_callable_args(
                method.name, [expr.index], [method.params[0].type],
                method.return_type, expr.line, expr.col,
            )

        raise TypeError(
            f"'[]' requires an array or string, got '{type_str(container_t)}'",
            expr.line, expr.col,
        )

    def _check_binary_operation_type(
        self,
        op: str,
        left_t: TypeNode,
        right_t: TypeNode,
        line: int,
        col: int,
    ) -> TypeNode:
        overload_t = self._check_binary_operator_overload(
            op, left_t, right_t, line, col
        )
        if overload_t is not None:
            return overload_t
        try:
            return binary_result_type(op, left_t, right_t)
        except TypeError as e:
            raise TypeError(e.msg, line, col) from None

    def _check_binary_operator_overload(
        self,
        op: str,
        left_t: TypeNode,
        right_t: TypeNode,
        line: int,
        col: int,
    ) -> Optional[TypeNode]:
        if op not in _BINARY_OPERATOR_OVERLOADS:
            return None
        class_name = self._class_value_name(left_t)
        if class_name is None:
            return None
        if not types_equal(left_t, right_t):
            return None

        method_name = f"operator{op}"
        method, defining = self._find_instance_method(class_name, method_name)
        if method is None and op == "!=":
            method, defining = self._find_instance_method(class_name, "operator==")
            if method is None:
                return None
            self._check_access(defining, method.access, method.name, line, col)
            return NamedType("bool")

        if method is None:
            return None
        self._check_access(defining, method.access, method.name, line, col)
        return method.return_type

    def _class_value_name(self, t: TypeNode) -> Optional[str]:
        if isinstance(t, NamedType) and self._env.is_class(t.name):
            return t.name
        return None

    def _find_instance_method(self, class_name: str, method_name: str):
        info = self._env.classes.get(class_name)
        if info is None:
            return None, class_name
        method = info.instance_methods.get(method_name)
        if method is None:
            return None, class_name
        return method, self._method_declaring_class(class_name, method_name)

    def _foreach_element_type(self, iterable_t: TypeNode, line: int, col: int) -> TypeNode:
        if is_array(iterable_t):
            return iterable_t.base
        if is_string(iterable_t):
            return NamedType("char")

        class_name = self._iterable_class_name(iterable_t)
        if class_name is None:
            raise TypeError(
                f"foreach requires an array, string, or iterable class, got '{type_str(iterable_t)}'",
                line, col,
            )

        length_method, length_defining = self._find_instance_method(class_name, "length")
        get_method, get_defining = self._find_instance_method(class_name, "get")
        if (
            length_method is None
            or len(length_method.params) != 0
            or not is_integer(length_method.return_type)
            or get_method is None
            or len(get_method.params) != 1
            or not is_integer(get_method.params[0].type)
        ):
            raise TypeError(
                f"foreach requires '{class_name}' to define length() and get(int)",
                line, col,
            )
        self._check_access(length_defining, length_method.access, "length", line, col)
        self._check_access(get_defining, get_method.access, "get", line, col)
        return get_method.return_type

    def _iterable_class_name(self, t: TypeNode) -> Optional[str]:
        if isinstance(t, PointerType):
            t = t.base
        if isinstance(t, NamedType) and self._env.is_class(t.name):
            return t.name
        return None

    def _is_var_type(self, t: TypeNode) -> bool:
        return isinstance(t, NamedType) and t.name == "var"

    def _is_null_type(self, t: TypeNode) -> bool:
        return isinstance(t, NamedType) and t.name == "null"

    def _check_operator_method_decl(self, method) -> None:
        if not method.name.startswith("operator"):
            return
        op = method.name[len("operator"):]
        if op not in _ALL_OPERATOR_OVERLOADS:
            raise TypeError(
                f"unsupported operator overload '{method.name}'",
                method.line, method.col,
            )
        if method.is_static:
            raise TypeError(
                "operator overloads must be instance methods",
                method.line, method.col,
            )
        if len(method.params) != 1:
            raise TypeError(
                f"'{method.name}' expects exactly 1 parameter",
                method.line, method.col,
            )
        if isinstance(method.return_type, NamedType) and method.return_type.name == "void":
            raise TypeError(
                f"'{method.name}' must return a value",
                method.line, method.col,
            )
        if op in _COMPARISON_OPERATOR_OVERLOADS and not is_bool(method.return_type):
            raise TypeError(
                f"'{method.name}' must return bool",
                method.line, method.col,
            )
        if op != "[]" and self._current_class is not None:
            expected = NamedType(self._current_class.name)
            if not types_equal(method.params[0].type, expected):
                raise TypeError(
                    f"'{method.name}' parameter must be '{self._current_class.name}'",
                    method.params[0].line, method.params[0].col,
                )

    def _check_closure(self, expr: ClosureExpr) -> FunctionPointerType:
        self._env.resolve_type(expr.return_type)
        self._check_class_access(expr.return_type, expr.line, expr.col)
        for p in expr.params:
            self._env.resolve_type(p.type)
            self._check_class_access(p.type, p.line, p.col)

        saved_scope = self._scope
        saved_return = self._return_type
        saved_loop = self._in_loop
        saved_ctor = self._in_constructor

        closure_scope = self._scope.child()
        ctx = ClosureContext(root=closure_scope)
        self._scope = closure_scope
        for p in expr.params:
            self._scope.define(p.name, p.type, p.line, p.col, p.is_const)
        self._return_type = expr.return_type
        self._in_loop = False
        self._in_constructor = False
        self._closure_stack.append(ctx)
        try:
            self._check_block(expr.body)
            rt_name = (
                expr.return_type.name
                if isinstance(expr.return_type, NamedType) else None
            )
            if rt_name != "void" and not always_returns(expr.body.stmts):
                raise TypeError(
                    "not all code paths return a value", expr.line, expr.col
                )
        finally:
            self._closure_stack.pop()
            self._scope = saved_scope
            self._return_type = saved_return
            self._in_loop = saved_loop
            self._in_constructor = saved_ctor

        expr.captures = list(ctx.captures.keys())
        return self._function_type_from_params(
            expr.params, expr.return_type, line=expr.line, col=expr.col,
        )

    def _record_capture(self, name: str, defining_scope: SymbolTable) -> None:
        if not self._closure_stack:
            return
        entry = defining_scope.entry(name)
        if entry is None:
            return
        for ctx in self._closure_stack:
            if not defining_scope.is_descendant_of(ctx.root):
                ctx.captures.setdefault(name, entry[0])

    def _function_type_from_params(
        self,
        params,
        return_type: TypeNode,
        *,
        line: int = 0,
        col: int = 0,
    ) -> FunctionPointerType:
        return FunctionPointerType(
            param_types=[p.type for p in params],
            return_type=return_type,
            line=line,
            col=col,
        )

    def _check_callable_args(
        self,
        name: str,
        args,
        param_types,
        return_type: TypeNode,
        line: int,
        col: int,
    ) -> TypeNode:
        expected = len(param_types)
        got = len(args)
        if expected != got:
            raise TypeError(
                f"'{name}' expects {expected} arguments, got {got}", line, col
            )
        for arg, param_t in zip(args, param_types):
            arg_t = self._check_expr(arg)
            if not self._assignable(arg_t, param_t, arg):
                raise TypeError(
                    f"cannot assign '{type_str(arg_t)}' to '{type_str(param_t)}'",
                    line, col,
                )
        return return_type

    # ------------------------------------------------------------------
    # Access / const helpers
    # ------------------------------------------------------------------

    def _check_access(self, defining_class: str, access: str,
                      member: str, line: int, col: int) -> None:
        if access == "public":
            return
        accessor = self._current_class.name if self._current_class else None
        if access == "private":
            if accessor != defining_class:
                raise TypeError(
                    f"'{member}' is private to '{defining_class}'", line, col
                )
        elif access == "protected":
            chain = superclass_chain(accessor, self._env) if accessor else []
            if defining_class not in chain:
                raise TypeError(
                    f"'{member}' is protected in '{defining_class}'", line, col
                )

    def _check_class_access(self, type_node: TypeNode, line: int, col: int) -> None:
        from parser.ast_nodes import (
            PointerType as PT, ArrayType as AT, FunctionPointerType as FPT,
        )
        if isinstance(type_node, NamedType):
            ci = self._env.classes.get(type_node.name)
            if ci and ci.access != "public" and self._current_class is None:
                raise TypeError(
                    f"class '{type_node.name}' is {ci.access} "
                    f"and cannot be used outside a class body",
                    line, col,
                )
        elif isinstance(type_node, PT):
            self._check_class_access(type_node.base, line, col)
        elif isinstance(type_node, AT):
            self._check_class_access(type_node.base, line, col)
        elif isinstance(type_node, FPT):
            for p in type_node.param_types:
                self._check_class_access(p, line, col)
            self._check_class_access(type_node.return_type, line, col)

    def _field_declaring_class(self, class_name: str, field_name: str) -> str:
        for cls in superclass_chain(class_name, self._env):
            info = self._env.classes.get(cls)
            if info and any(fd.name == field_name for fd in info.decl.fields):
                return cls
        return class_name

    def _method_declaring_class(self, class_name: str, method_name: str) -> str:
        for cls in superclass_chain(class_name, self._env):
            info = self._env.classes.get(cls)
            if info and any(md.name == method_name for md in info.decl.methods):
                return cls
        return class_name

    def _resolve_target_class_info(self, target):
        """Resolve the ClassInfo for a field-access assignment target without
        re-invoking _check_expr (which would fail for class-name receivers)."""
        if isinstance(target, FieldAccessExpr):
            obj = target.object
            # Static field: ClassName.field
            if (isinstance(obj, IdentifierExpr)
                    and self._env.is_class(obj.name)
                    and self._scope._find(obj.name) is None):
                return self._env.classes[obj.name]
            # this.field
            if isinstance(obj, ThisExpr):
                return self._current_class
            # variable.field — look up from scope
            if isinstance(obj, IdentifierExpr):
                entry = self._scope._find(obj.name)
                if entry:
                    t = entry[0]
                    if isinstance(t, (PointerType, ManagedHandleType)) and isinstance(t.base, NamedType):
                        return self._env.classes.get(t.base.name)
                    if isinstance(t, NamedType):
                        return self._env.classes.get(t.name)
        elif isinstance(target, ArrowAccessExpr):
            ptr = target.pointer
            if isinstance(ptr, ThisExpr):
                return self._current_class
            if isinstance(ptr, IdentifierExpr):
                entry = self._scope._find(ptr.name)
                if entry:
                    t = entry[0]
                    if is_pointer(t):
                        base = pointer_base(t)
                        if isinstance(base, NamedType):
                            return self._env.classes.get(base.name)
        return None

    def _is_static_method_ref(self, expr: Expr) -> bool:
        if not isinstance(expr, FieldAccessExpr):
            return False
        obj = expr.object
        if (
            isinstance(obj, IdentifierExpr)
            and self._env.is_class(obj.name)
            and self._scope._find(obj.name) is None
        ):
            class_info = self._env.classes[obj.name]
            return (
                expr.field_name not in class_info.static_fields
                and expr.field_name in class_info.static_methods
            )
        return False

    # ------------------------------------------------------------------
    # Cast validation
    # ------------------------------------------------------------------

    def _validate_cast(
        self,
        src: TypeNode,
        dst: TypeNode,
        line: int,
        col: int,
    ) -> None:
        src_s = type_str(src)
        dst_s = type_str(dst)

        # Enum ↔ int casts
        if isinstance(src, NamedType) and isinstance(dst, NamedType):
            if dst.name == "int" and self._env.is_enum(src.name):
                return
            if self._env.is_enum(dst.name) and src.name == "int":
                return

        numeric_pairs = {
            ("int", "float"), ("float", "int"),
            ("int", "char"), ("char", "int"),
            ("int", "byte"), ("byte", "int"),
            ("char", "byte"), ("byte", "char"),
        }
        if (
            isinstance(src, NamedType)
            and isinstance(dst, NamedType)
            and (src.name, dst.name) in numeric_pairs
        ):
            return

        if is_pointer(src) and is_pointer(dst):
            # any pointer → void*
            if isinstance(dst.base, NamedType) and dst.base.name == "void":
                return
            # void* → any pointer
            if isinstance(src.base, NamedType) and src.base.name == "void":
                return
            # pointer-to-class A → pointer-to-class B (unsafe, allowed by spec)
            if (
                isinstance(src.base, NamedType)
                and isinstance(dst.base, NamedType)
            ):
                return

        raise TypeError(
            f"invalid cast from '{src_s}' to '{dst_s}'", line, col
        )
