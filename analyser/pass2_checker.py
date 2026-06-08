from __future__ import annotations
from typing import Optional

from parser.ast_nodes import (
    Program, Stmt, Expr, TypeNode,
    FunctionDecl, ClassDecl, InterfaceDecl, EnumDecl,
    Block, VarDecl, AssignStmt, IfStmt, WhileStmt, ForStmt,
    ReturnStmt, BreakStmt, ContinueStmt,
    BinaryExpr, UnaryExpr, CastExpr, CallExpr, MethodCallExpr,
    NewExpr, DeleteExpr, AllocExpr, FreeExpr,
    FieldAccessExpr, ArrowAccessExpr, IndexExpr,
    AddressOfExpr, DerefExpr,
    IdentifierExpr, LiteralExpr, NullExpr, ThisExpr, SuperExpr,
    NamedType, PointerType,
)
from errors.errors import TypeError
from analyser.symbol_table import GlobalEnv, ClassInfo, SymbolTable
from analyser.type_utils import (
    NULL_TYPE, is_assignable, is_integer, is_bool,
    is_pointer, is_array, pointer_base, type_str,
    is_lvalue, binary_result_type, unary_result_type,
    superclass_chain,
)
from analyser.return_checker import always_returns


class Pass2Checker:
    def __init__(self, env: GlobalEnv) -> None:
        self._env = env
        self._scope: SymbolTable = SymbolTable()
        self._return_type: Optional[TypeNode] = None
        self._current_class: Optional[ClassInfo] = None
        self._in_loop: bool = False
        self._in_static_method: bool = False
        self._in_constructor: bool = False

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
            if not is_assignable(init_t, sfd.type, self._env):
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
                        if not is_assignable(arg_t, param.type, self._env):
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
            self._env.resolve_type(stmt.type)
            self._check_class_access(stmt.type, stmt.line, stmt.col)
            init_t = self._check_expr(stmt.initializer)
            if not is_assignable(init_t, stmt.type, self._env):
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
            target_t = self._check_expr(stmt.target)
            value_t = self._check_expr(stmt.value)

            if stmt.op != "=":
                # Compound assignment: validate the op makes sense for target_t
                op_symbol = stmt.op[:-1]  # e.g. "+=" → "+"
                binary_result_type(op_symbol, target_t, value_t)

            if not is_assignable(value_t, target_t, self._env):
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
                if not is_assignable(val_t, rt, self._env):
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

        else:
            # bare expression statement
            self._check_expr(stmt)

    # ------------------------------------------------------------------
    # Expressions
    # ------------------------------------------------------------------

    def _check_expr(self, expr: Expr) -> TypeNode:
        if isinstance(expr, LiteralExpr):
            return NamedType(expr.kind)

        if isinstance(expr, NullExpr):
            return NULL_TYPE

        if isinstance(expr, IdentifierExpr):
            t = self._scope._find(expr.name)
            if t is not None:
                return t[0]
            raise TypeError(
                f"undefined variable '{expr.name}'", expr.line, expr.col
            )

        if isinstance(expr, ThisExpr):
            if self._in_static_method or self._current_class is None:
                raise TypeError(
                    "'this' is not available in a static method",
                    expr.line, expr.col,
                )
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
            t = self._check_expr(expr.operand)
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
            try:
                return binary_result_type(expr.op, left_t, right_t)
            except TypeError as e:
                raise TypeError(e.msg, expr.line, expr.col) from None

        if isinstance(expr, CallExpr):
            # Built-in print(x): accepts one primitive argument, returns void.
            # (Not part of the spec; provided so program output is observable.)
            if expr.name == "print":
                if len(expr.args) != 1:
                    raise TypeError(
                        f"'print' expects 1 argument, got {len(expr.args)}",
                        expr.line, expr.col,
                    )
                arg_t = self._check_expr(expr.args[0])
                if not (isinstance(arg_t, NamedType)
                        and arg_t.name in ("int", "float", "bool", "char", "string")):
                    raise TypeError(
                        f"'print' requires a primitive argument, got '{type_str(arg_t)}'",
                        expr.line, expr.col,
                    )
                return NamedType("void")

            fn_info = self._env.functions.get(expr.name)
            if fn_info is not None:
                expected = len(fn_info.params)
                got = len(expr.args)
                if expected != got:
                    raise TypeError(
                        f"'{expr.name}' expects {expected} arguments, got {got}",
                        expr.line, expr.col,
                    )
                for arg, param in zip(expr.args, fn_info.params):
                    arg_t = self._check_expr(arg)
                    if not is_assignable(arg_t, param.type, self._env):
                        raise TypeError(
                            f"cannot assign '{type_str(arg_t)}' to '{type_str(param.type)}'",
                            expr.line, expr.col,
                        )
                return fn_info.return_type

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
                        if not is_assignable(arg_t, param.type, self._env):
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

        if isinstance(expr, MethodCallExpr):
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
                    if not is_assignable(arg_t, param.type, self._env):
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
                raise TypeError(
                    f"'{class_t.name}' has no method '{expr.method}'",
                    expr.line, expr.col,
                )
            method = class_info.instance_methods.get(expr.method)
            if method is None:
                raise TypeError(
                    f"'{class_t.name}' has no method '{expr.method}'",
                    expr.line, expr.col,
                )
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
                if not is_assignable(arg_t, param.type, self._env):
                    raise TypeError(
                        f"cannot assign '{type_str(arg_t)}' to '{type_str(param.type)}'",
                        expr.line, expr.col,
                    )
            return method.return_type

        if isinstance(expr, FieldAccessExpr):
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
                if sfd is None:
                    raise TypeError(
                        f"'{expr.object.name}' has no field '{expr.field_name}'",
                        expr.line, expr.col,
                    )
                self._check_access(expr.object.name, sfd.access, expr.field_name,
                                   expr.line, expr.col)
                return sfd.type

            obj_t = self._check_expr(expr.object)
            # Auto-deref: `this.field` uses FieldAccessExpr with a pointer receiver
            if isinstance(obj_t, PointerType) and isinstance(obj_t.base, NamedType):
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
            arr_t = self._check_expr(expr.array)
            if not is_array(arr_t):
                raise TypeError(
                    f"'[]' requires an array, got '{type_str(arr_t)}'",
                    expr.line, expr.col,
                )
            idx_t = self._check_expr(expr.index)
            if not is_integer(idx_t):
                raise TypeError(
                    f"array index must be int, got '{type_str(idx_t)}'",
                    expr.line, expr.col,
                )
            return arr_t.base

        if isinstance(expr, NewExpr):
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
                    if not is_assignable(arg_t, param.type, self._env):
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
            return PointerType(NamedType(expr.class_name))

        if isinstance(expr, DeleteExpr):
            t = self._check_expr(expr.operand)
            if not is_pointer(t):
                raise TypeError(
                    "'delete' requires a pointer to a class",
                    expr.line, expr.col,
                )
            base = pointer_base(t)
            if not (isinstance(base, NamedType) and self._env.is_class(base.name)):
                raise TypeError(
                    "'delete' requires a pointer to a class",
                    expr.line, expr.col,
                )
            return NamedType("void")

        if isinstance(expr, AllocExpr):
            self._env.resolve_type(expr.type)
            if isinstance(expr.type, NamedType) and expr.type.name == "void":
                raise TypeError("cannot alloc void", expr.line, expr.col)
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
        from parser.ast_nodes import PointerType as PT, ArrayType as AT
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

    def _field_declaring_class(self, class_name: str, field_name: str) -> str:
        for cls in superclass_chain(class_name, self._env):
            info = self._env.classes.get(cls)
            if info and any(fd.name == field_name for fd in info.decl.fields):
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
                    if isinstance(t, PointerType) and isinstance(t.base, NamedType):
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
