"""Phase 5 — tree-walking interpreter with a simulated memory model.

Consumes a type-checked ``Program`` plus the ``GlobalEnv`` produced by the
analyser and executes it. Memory is modelled explicitly:

  * every addressable storage location is a mutable :class:`Box`;
  * :class:`Pointer` aliases a box (``None`` target means ``null``);
  * :class:`Heap` tracks heap-allocated boxes for ``free``/``delete`` and
    detects double-free / use-after-free;
  * objects are :class:`ObjectInstance` records whose fields are boxes.

Method dispatch is virtual: an instance method is resolved against the
*runtime* class of the receiver walking the superclass chain (the same result
as the analyser-built vtable), so overrides are honoured even through a
base-class or interface pointer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from parser.ast_nodes import (
    Program, Stmt, Expr,
    FunctionDecl, ClassDecl, StaticFieldDecl,
    MethodDecl, ConstructorDecl, DestructorDecl,
    Block, VarDecl, AssignStmt, IfStmt, WhileStmt, ForStmt,
    ReturnStmt, BreakStmt, ContinueStmt,
    BinaryExpr, UnaryExpr, CastExpr, CallExpr, MethodCallExpr,
    NewExpr, DeleteExpr, AllocExpr, FreeExpr,
    FieldAccessExpr, ArrowAccessExpr, IndexExpr,
    AddressOfExpr, DerefExpr,
    IdentifierExpr, LiteralExpr, NullExpr, ThisExpr, SuperExpr,
    TypeNode, NamedType, PointerType, ArrayType,
)
from errors.errors import RuntimeError as GlangRuntimeError
from analyser.symbol_table import GlobalEnv
from analyser.type_utils import superclass_chain


# ---------------------------------------------------------------------------
# Runtime values & memory primitives
# ---------------------------------------------------------------------------

@dataclass
class Value:
    """A runtime value: a static type plus its Python-level representation."""
    type: TypeNode
    raw: Any


@dataclass
class Box:
    """A mutable storage cell — the unit that pointers point at.

    Locals, parameters, object fields, array elements, and heap allocations
    are all boxes, so address-of, dereference, out-parameters, and indexing
    work uniformly.
    """
    value: Value
    addr: int = 0
    on_heap: bool = False
    freed: bool = False


@dataclass
class Pointer:
    """A pointer value; ``target is None`` represents ``null``."""
    target: Optional[Box] = None


@dataclass
class ObjectInstance:
    """A heap-allocated class instance."""
    class_name: str
    fields: Dict[str, Box]


class Heap:
    """Tracks heap-allocated boxes and validates free/delete."""

    def __init__(self) -> None:
        self._next_addr = 1
        self._live: set[int] = set()

    def alloc(self, value: Value) -> Box:
        box = Box(value=value, addr=self._next_addr, on_heap=True)
        self._next_addr += 1
        self._live.add(box.addr)
        return box

    def free(self, box: Box) -> None:
        if not box.on_heap:
            raise GlangRuntimeError("free of a non-heap pointer", 0, 0)
        if box.freed:
            raise GlangRuntimeError("double free", 0, 0)
        box.freed = True
        self._live.discard(box.addr)


class Frame:
    """A call frame: a stack of lexical scopes plus call context."""

    def __init__(self, this_val: Optional[Value], current_class: Optional[str]) -> None:
        self.scopes: List[Dict[str, Box]] = [{}]
        self.this_val = this_val
        self.current_class = current_class

    def push_scope(self) -> None:
        self.scopes.append({})

    def pop_scope(self) -> None:
        self.scopes.pop()

    def define(self, name: str, box: Box) -> None:
        self.scopes[-1][name] = box

    def lookup(self, name: str) -> Optional[Box]:
        for scope in reversed(self.scopes):
            if name in scope:
                return scope[name]
        return None


# ---------------------------------------------------------------------------
# Non-local control flow signals
# ---------------------------------------------------------------------------

class BreakSignal(Exception):
    pass


class ContinueSignal(Exception):
    pass


class ReturnSignal(Exception):
    def __init__(self, value: Value) -> None:
        super().__init__()
        self.value = value


# ---------------------------------------------------------------------------
# Interpreter
# ---------------------------------------------------------------------------

VOID = Value(NamedType("void"), None)


class Interpreter:
    def __init__(self, env: GlobalEnv, out=None) -> None:
        self._env = env
        self._heap = Heap()
        self._frames: List[Frame] = []
        self._statics: Dict[Tuple[str, str], Box] = {}
        # `print` always records lines in self.output (for tests); when an
        # `out` stream is supplied (e.g. sys.stdout from the CLI) lines are
        # also written to it live, so output survives a mid-run error.
        self.output: List[str] = []
        self._out = out
        self._stack_addr = -1  # negative addresses for non-heap boxes

    # -- public entry ----------------------------------------------------

    def run(self, program: Program) -> int:
        self._init_statics(program)
        main = self._env.functions.get("main")
        if main is None:
            raise GlangRuntimeError("no 'main' function", 0, 0)
        result = self._call_function(main.decl, [])
        if isinstance(result.raw, int) and not isinstance(result.raw, bool):
            return result.raw
        return 0

    # -- setup -----------------------------------------------------------

    def _init_statics(self, program: Program) -> None:
        frame = Frame(this_val=None, current_class=None)
        self._frames.append(frame)
        try:
            for decl in program.declarations:
                if isinstance(decl, ClassDecl):
                    for sfd in decl.static_fields:
                        val = self._eval(sfd.initializer)
                        box = self._new_box(Value(sfd.type, val.raw))
                        self._statics[(decl.name, sfd.name)] = box
        finally:
            self._frames.pop()

    # -- frame / scope helpers -------------------------------------------

    @property
    def _frame(self) -> Frame:
        return self._frames[-1]

    def _new_box(self, value: Value, *, on_heap: bool = False) -> Box:
        if on_heap:
            return self._heap.alloc(value)
        box = Box(value=value, addr=self._stack_addr)
        self._stack_addr -= 1
        return box

    # -- function / method invocation ------------------------------------

    def _call_function(self, fn: FunctionDecl, args: List[Value]) -> Value:
        frame = Frame(this_val=None, current_class=None)
        for param, arg in zip(fn.params, args):
            frame.define(param.name, self._new_box(Value(param.type, arg.raw)))
        return self._run_body(frame, fn.body, fn.return_type)

    def _call_method(
        self,
        method: MethodDecl,
        defining_class: Optional[str],
        this_val: Optional[Value],
        args: List[Value],
    ) -> Value:
        frame = Frame(this_val=this_val, current_class=defining_class)
        for param, arg in zip(method.params, args):
            frame.define(param.name, self._new_box(Value(param.type, arg.raw)))
        return self._run_body(frame, method.body, method.return_type)

    def _run_body(self, frame: Frame, body: Block, return_type: TypeNode) -> Value:
        self._frames.append(frame)
        try:
            for stmt in body.stmts:
                self._exec_stmt(stmt)
        except ReturnSignal as ret:
            return ret.value
        finally:
            self._frames.pop()
        return VOID

    # -- statements ------------------------------------------------------

    def _exec_block(self, block: Block) -> None:
        self._frame.push_scope()
        try:
            for stmt in block.stmts:
                self._exec_stmt(stmt)
        finally:
            self._frame.pop_scope()

    def _exec_stmt(self, stmt: Stmt) -> None:
        if isinstance(stmt, Block):
            self._exec_block(stmt)

        elif isinstance(stmt, VarDecl):
            init = self._eval(stmt.initializer)
            self._frame.define(stmt.name, self._new_box(Value(stmt.type, init.raw)))

        elif isinstance(stmt, AssignStmt):
            box = self._resolve_lvalue(stmt.target)
            if stmt.op == "=":
                rhs = self._eval(stmt.value)
            else:
                cur = box.value
                rhs = self._apply_binary(
                    stmt.op[:-1], cur, self._eval(stmt.value), stmt.line, stmt.col
                )
            self._store(box, rhs)

        elif isinstance(stmt, IfStmt):
            if self._eval(stmt.condition).raw:
                self._exec_block(stmt.then_branch)
            elif stmt.else_branch is not None:
                if isinstance(stmt.else_branch, IfStmt):
                    self._exec_stmt(stmt.else_branch)
                else:
                    self._exec_block(stmt.else_branch)

        elif isinstance(stmt, WhileStmt):
            while self._eval(stmt.condition).raw:
                try:
                    self._exec_block(stmt.body)
                except BreakSignal:
                    break
                except ContinueSignal:
                    continue

        elif isinstance(stmt, ForStmt):
            self._frame.push_scope()
            try:
                self._exec_stmt(stmt.init)
                while self._eval(stmt.condition).raw:
                    try:
                        self._exec_block(stmt.body)
                    except BreakSignal:
                        break
                    except ContinueSignal:
                        pass
                    if isinstance(stmt.post, AssignStmt):
                        self._exec_stmt(stmt.post)
                    else:
                        self._eval(stmt.post)
            finally:
                self._frame.pop_scope()

        elif isinstance(stmt, ReturnStmt):
            value = self._eval(stmt.value) if stmt.value is not None else VOID
            raise ReturnSignal(value)

        elif isinstance(stmt, BreakStmt):
            raise BreakSignal()

        elif isinstance(stmt, ContinueStmt):
            raise ContinueSignal()

        else:
            self._eval(stmt)  # bare expression statement

    # -- expressions -----------------------------------------------------

    def _eval(self, expr: Expr) -> Value:
        if isinstance(expr, LiteralExpr):
            return self._eval_literal(expr)

        if isinstance(expr, NullExpr):
            return Value(NamedType("null"), Pointer(None))

        if isinstance(expr, IdentifierExpr):
            box = self._frame.lookup(expr.name)
            if box is None:
                raise GlangRuntimeError(
                    f"undefined variable '{expr.name}'", expr.line, expr.col
                )
            return box.value

        if isinstance(expr, ThisExpr):
            return self._frame.this_val

        if isinstance(expr, SuperExpr):
            return self._frame.this_val

        if isinstance(expr, BinaryExpr):
            return self._eval_binary(expr)

        if isinstance(expr, UnaryExpr):
            return self._eval_unary(expr)

        if isinstance(expr, CastExpr):
            return self._eval_cast(expr)

        if isinstance(expr, AddressOfExpr):
            box = self._resolve_lvalue(expr.operand)
            return Value(PointerType(box.value.type), Pointer(box))

        if isinstance(expr, DerefExpr):
            box = self._deref(self._eval(expr.operand), expr.line, expr.col)
            return box.value

        if isinstance(expr, AllocExpr):
            zero = self._zero_value(expr.type)
            box = self._heap.alloc(zero)
            return Value(PointerType(expr.type), Pointer(box))

        if isinstance(expr, FreeExpr):
            ptr = self._eval(expr.operand).raw
            if isinstance(ptr, Pointer) and ptr.target is not None:
                self._heap.free(ptr.target)
            return VOID

        if isinstance(expr, CallExpr):
            return self._eval_call(expr)

        if isinstance(expr, MethodCallExpr):
            return self._eval_method_call(expr)

        if isinstance(expr, NewExpr):
            return self._eval_new(expr)

        if isinstance(expr, DeleteExpr):
            return self._eval_delete(expr)

        if isinstance(expr, (FieldAccessExpr, ArrowAccessExpr, IndexExpr)):
            return self._resolve_lvalue(expr).value

        raise GlangRuntimeError(
            f"cannot evaluate '{type(expr).__name__}'", 0, 0
        )

    def _eval_literal(self, expr: LiteralExpr) -> Value:
        kind = expr.kind
        if kind == "int":
            return Value(NamedType("int"), int(expr.value))
        if kind == "float":
            return Value(NamedType("float"), float(expr.value))
        if kind == "bool":
            return Value(NamedType("bool"), expr.value == "true")
        if kind == "char":
            return Value(NamedType("char"), expr.value)
        return Value(NamedType("string"), expr.value)

    def _eval_binary(self, expr: BinaryExpr) -> Value:
        if expr.op == "&&":
            left = self._eval(expr.left)
            if not left.raw:
                return Value(NamedType("bool"), False)
            return Value(NamedType("bool"), bool(self._eval(expr.right).raw))
        if expr.op == "||":
            left = self._eval(expr.left)
            if left.raw:
                return Value(NamedType("bool"), True)
            return Value(NamedType("bool"), bool(self._eval(expr.right).raw))
        left = self._eval(expr.left)
        right = self._eval(expr.right)
        return self._apply_binary(expr.op, left, right, expr.line, expr.col)

    def _apply_binary(
        self, op: str, left: Value, right: Value, line: int, col: int
    ) -> Value:
        l, r = left.raw, right.raw

        if op in ("==", "!="):
            eq = self._values_equal(left, right)
            return Value(NamedType("bool"), eq if op == "==" else not eq)

        if op in ("<", ">", "<=", ">="):
            res = {
                "<": l < r, ">": l > r, "<=": l <= r, ">=": l >= r,
            }[op]
            return Value(NamedType("bool"), res)

        l_int = self._is(left, "int")
        r_int = self._is(right, "int")

        if op == "+":
            if self._is(left, "string"):
                return Value(NamedType("string"), l + r)
            if l_int and r_int:
                return Value(NamedType("int"), l + r)
            return Value(NamedType("float"), l + r)
        if op == "-":
            t = "int" if (l_int and r_int) else "float"
            return Value(NamedType(t), l - r)
        if op == "*":
            t = "int" if (l_int and r_int) else "float"
            return Value(NamedType(t), l * r)
        if op == "/":
            if l_int and r_int:
                return Value(NamedType("int"), self._cdiv(l, r, line, col))
            return Value(NamedType("float"), l / r)
        if op == "%":
            return Value(NamedType("int"), self._cmod(l, r, line, col))

        if op == "&":
            return Value(NamedType("int"), l & r)
        if op == "|":
            return Value(NamedType("int"), l | r)
        if op == "^":
            return Value(NamedType("int"), l ^ r)
        if op == "<<":
            return Value(NamedType("int"), l << r)
        if op == ">>":
            return Value(NamedType("int"), l >> r)

        raise GlangRuntimeError(f"unknown operator '{op}'", line, col)

    def _values_equal(self, left: Value, right: Value) -> bool:
        if isinstance(left.raw, Pointer) or isinstance(right.raw, Pointer):
            lt = left.raw.target if isinstance(left.raw, Pointer) else None
            rt = right.raw.target if isinstance(right.raw, Pointer) else None
            return lt is rt
        return left.raw == right.raw

    def _eval_unary(self, expr: UnaryExpr) -> Value:
        if expr.op in ("++", "--"):
            box = self._resolve_lvalue(expr.operand)
            new = box.value.raw + (1 if expr.op == "++" else -1)
            self._store(box, Value(NamedType("int"), new))
            return Value(NamedType("int"), new)

        operand = self._eval(expr.operand)
        if expr.op == "!":
            return Value(NamedType("bool"), not operand.raw)
        if expr.op == "~":
            return Value(NamedType("int"), ~operand.raw)
        if expr.op == "-":
            t = "int" if self._is(operand, "int") else "float"
            return Value(NamedType(t), -operand.raw)
        if expr.op == "+":
            return operand
        raise GlangRuntimeError(f"unknown unary operator '{expr.op}'", expr.line, expr.col)

    def _eval_cast(self, expr: CastExpr) -> Value:
        src = self._eval(expr.expr)
        target = expr.target_type
        if isinstance(target, NamedType):
            if target.name == "int":
                if self._is(src, "char"):
                    return Value(target, ord(src.raw))
                return Value(target, int(src.raw))
            if target.name == "float":
                return Value(target, float(src.raw))
            if target.name == "char":
                if self._is(src, "int"):
                    return Value(target, chr(src.raw & 0xFF))
                return Value(target, src.raw)
        # pointer reinterpret-cast: keep the raw pointer, retag the type
        return Value(target, src.raw)

    def _eval_call(self, expr: CallExpr) -> Value:
        if expr.name == "print":
            self._do_print(self._eval(expr.args[0]))
            return VOID

        fn = self._env.functions.get(expr.name)
        if fn is not None:
            args = [self._eval(a) for a in expr.args]
            return self._call_function(fn.decl, args)

        # Stack constructor call: ClassName(args) -> object value.
        if self._env.is_class(expr.name):
            args = [self._eval(a) for a in expr.args]
            this_val = self._instantiate(expr.name, on_heap=False)
            self._run_constructor(expr.name, this_val, args)
            return self._deref(this_val, expr.line, expr.col).value

        raise GlangRuntimeError(f"undefined function '{expr.name}'", expr.line, expr.col)

    def _eval_method_call(self, expr: MethodCallExpr) -> Value:
        # Static method call: ClassName.method(args)
        if (
            not expr.is_arrow
            and isinstance(expr.object, IdentifierExpr)
            and self._env.is_class(expr.object.name)
            and self._frame.lookup(expr.object.name) is None
        ):
            cls = expr.object.name
            info = self._env.classes[cls]
            method = info.static_methods[expr.method]
            args = [self._eval(a) for a in expr.args]
            return self._call_method(method, cls, None, args)

        args = [self._eval(a) for a in expr.args]

        # super.method(): static dispatch starting at the parent class.
        if isinstance(expr.object, SuperExpr):
            start = self._env.classes[self._frame.current_class].superclass
            method, defining = self._resolve_virtual(start, expr.method)
            return self._call_method(method, defining, self._frame.this_val, args)

        receiver = self._eval(expr.object)
        instance, this_val = self._receiver(receiver, expr.line, expr.col)
        method, defining = self._resolve_virtual(instance.class_name, expr.method)
        return self._call_method(method, defining, this_val, args)

    def _eval_new(self, expr: NewExpr) -> Value:
        this_val = self._instantiate(expr.class_name, on_heap=True)
        args = [self._eval(a) for a in expr.args]
        self._run_constructor(expr.class_name, this_val, args)
        return this_val

    def _eval_delete(self, expr: DeleteExpr) -> Value:
        ptr = self._eval(expr.operand).raw
        if not isinstance(ptr, Pointer) or ptr.target is None:
            return VOID  # delete null is a no-op
        box = ptr.target
        if box.freed:
            raise GlangRuntimeError("delete of a freed pointer", expr.line, expr.col)
        instance = box.value.raw
        # Destructor chain: most-derived class first, up to the base.
        for cls in superclass_chain(instance.class_name, self._env):
            info = self._env.classes.get(cls)
            if info is not None and info.destructor is not None:
                self._call_method(
                    _as_method(info.destructor), cls, self._eval(expr.operand), []
                )
        self._heap.free(box)
        return VOID

    # -- object construction / dispatch ----------------------------------

    def _instantiate(self, class_name: str, *, on_heap: bool) -> Value:
        fields: Dict[str, Box] = {}
        # Collect fields base-first so derived classes can override order;
        # all are zero-initialised before any constructor runs.
        for cls in reversed(superclass_chain(class_name, self._env)):
            info = self._env.classes[cls]
            for fname, ftype in info.fields.items():
                fields[fname] = self._new_box(self._zero_value(ftype))
        instance = ObjectInstance(class_name=class_name, fields=fields)
        obj_value = Value(NamedType(class_name), instance)
        box = self._new_box(obj_value, on_heap=on_heap)
        return Value(PointerType(NamedType(class_name)), Pointer(box))

    def _run_constructor(self, class_name: str, this_val: Value, args: List[Value]) -> None:
        info = self._env.classes[class_name]
        ctor = info.constructor
        frame = Frame(this_val=this_val, current_class=class_name)
        if ctor is not None:
            for param, arg in zip(ctor.params, args):
                frame.define(param.name, self._new_box(Value(param.type, arg.raw)))

        self._frames.append(frame)
        try:
            # Run the parent constructor first (super(...) is the first stmt).
            if ctor is not None and ctor.super_args is not None:
                super_args = [self._eval(a) for a in ctor.super_args]
                self._run_constructor(info.superclass, this_val, super_args)
            elif info.superclass is not None:
                self._run_constructor(info.superclass, this_val, [])

            if ctor is not None:
                try:
                    for stmt in ctor.body.stmts:
                        self._exec_stmt(stmt)
                except ReturnSignal:
                    pass
        finally:
            self._frames.pop()

    def _resolve_virtual(self, class_name: Optional[str], method: str) -> Tuple[MethodDecl, str]:
        """Virtual dispatch: first definition found walking derived -> base."""
        for cls in superclass_chain(class_name, self._env):
            info = self._env.classes.get(cls)
            if info is not None and method in info.instance_methods:
                return info.instance_methods[method], cls
        raise GlangRuntimeError(
            f"'{class_name}' has no method '{method}'", 0, 0
        )

    def _receiver(self, value: Value, line: int, col: int) -> Tuple[ObjectInstance, Value]:
        """Return (instance, this-pointer) for a method receiver."""
        if isinstance(value.raw, Pointer):
            box = self._deref(value, line, col)
            return box.value.raw, value
        if isinstance(value.raw, ObjectInstance):
            box = self._new_box(value)
            this_val = Value(PointerType(NamedType(value.raw.class_name)), Pointer(box))
            return value.raw, this_val
        raise GlangRuntimeError("receiver is not an object", line, col)

    # -- lvalues ---------------------------------------------------------

    def _resolve_lvalue(self, expr: Expr) -> Box:
        if isinstance(expr, IdentifierExpr):
            box = self._frame.lookup(expr.name)
            if box is None:
                raise GlangRuntimeError(
                    f"undefined variable '{expr.name}'", expr.line, expr.col
                )
            return box

        if isinstance(expr, DerefExpr):
            return self._deref(self._eval(expr.operand), expr.line, expr.col)

        if isinstance(expr, ArrowAccessExpr):
            box = self._deref(self._eval(expr.pointer), expr.line, expr.col)
            return self._field_box(box.value.raw, expr.field_name, expr.line, expr.col)

        if isinstance(expr, FieldAccessExpr):
            # Static field: ClassName.field
            if (
                isinstance(expr.object, IdentifierExpr)
                and self._env.is_class(expr.object.name)
                and self._frame.lookup(expr.object.name) is None
            ):
                return self._static_box(expr.object.name, expr.field_name, expr.line, expr.col)
            obj = self._eval(expr.object)
            if isinstance(obj.raw, Pointer):
                obj = self._deref(obj, expr.line, expr.col).value
            return self._field_box(obj.raw, expr.field_name, expr.line, expr.col)

        if isinstance(expr, IndexExpr):
            arr = self._eval(expr.array)
            idx = self._eval(expr.index).raw
            elements = arr.raw
            if not isinstance(elements, list) or idx < 0 or idx >= len(elements):
                raise GlangRuntimeError(
                    "array index out of bounds", expr.line, expr.col
                )
            return elements[idx]

        raise GlangRuntimeError(
            f"'{type(expr).__name__}' is not an lvalue", 0, 0
        )

    def _field_box(self, instance: Any, name: str, line: int, col: int) -> Box:
        if not isinstance(instance, ObjectInstance) or name not in instance.fields:
            raise GlangRuntimeError(f"no field '{name}'", line, col)
        return instance.fields[name]

    def _static_box(self, cls: str, name: str, line: int, col: int) -> Box:
        for c in superclass_chain(cls, self._env):
            key = (c, name)
            if key in self._statics:
                return self._statics[key]
        raise GlangRuntimeError(f"'{cls}' has no static field '{name}'", line, col)

    # -- helpers ---------------------------------------------------------

    def _deref(self, value: Value, line: int, col: int) -> Box:
        ptr = value.raw
        if not isinstance(ptr, Pointer):
            raise GlangRuntimeError("dereference of a non-pointer", line, col)
        if ptr.target is None:
            raise GlangRuntimeError("null pointer dereference", line, col)
        if ptr.target.freed:
            raise GlangRuntimeError("use after free", line, col)
        return ptr.target

    def _store(self, box: Box, value: Value) -> None:
        box.value = Value(box.value.type, value.raw)

    def _is(self, value: Value, name: str) -> bool:
        return isinstance(value.type, NamedType) and value.type.name == name

    def _zero_value(self, t: TypeNode) -> Value:
        if isinstance(t, PointerType):
            return Value(t, Pointer(None))
        if isinstance(t, ArrayType):
            return Value(t, [self._new_box(self._zero_value(t.base)) for _ in range(t.size)])
        if isinstance(t, NamedType):
            if t.name == "int":
                return Value(t, 0)
            if t.name == "float":
                return Value(t, 0.0)
            if t.name == "bool":
                return Value(t, False)
            if t.name == "char":
                return Value(t, "\0")
            if t.name == "string":
                return Value(t, "")
            # class-typed field with no pointer: treat as null reference
            return Value(t, Pointer(None))
        return Value(t, None)

    def _cdiv(self, a: int, b: int, line: int, col: int) -> int:
        if b == 0:
            raise GlangRuntimeError("division by zero", line, col)
        q = abs(a) // abs(b)
        return -q if (a < 0) != (b < 0) else q

    def _cmod(self, a: int, b: int, line: int, col: int) -> int:
        if b == 0:
            raise GlangRuntimeError("modulo by zero", line, col)
        r = abs(a) % abs(b)
        return -r if a < 0 else r

    def _do_print(self, value: Value) -> None:
        raw = value.raw
        if self._is(value, "bool"):
            text = "true" if raw else "false"
        else:
            text = str(raw)
        self.output.append(text)
        if self._out is not None:
            self._out.write(text + "\n")


def _as_method(dtor: DestructorDecl) -> MethodDecl:
    """Adapt a destructor to the MethodDecl shape used by _call_method."""
    return MethodDecl(
        name="~", params=[], return_type=NamedType("void"), body=dtor.body,
    )


# ---------------------------------------------------------------------------
# Module-level convenience entry point
# ---------------------------------------------------------------------------

def interpret(program: Program, env: GlobalEnv) -> int:
    """Run ``program`` and return ``main``'s exit code."""
    return Interpreter(env).run(program)
