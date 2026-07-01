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

import os
from dataclasses import dataclass, field
from typing import Any, Dict, Iterator, List, Optional, Tuple

from parser.ast_nodes import (
    Program, Stmt, Expr,
    FunctionDecl, ClassDecl, StaticFieldDecl, EnumDecl,
    MethodDecl, ConstructorDecl, DestructorDecl,
    Block, VarDecl, AssignStmt, IfStmt, WhileStmt, DoWhileStmt, ForStmt,
    ForeachStmt, ReturnStmt, BreakStmt, ContinueStmt, UsingStmt, ThrowStmt, TryCatchStmt, CatchClause,
    MatchStmt, VariantPattern, WildcardPattern,
    BinaryExpr, UnaryExpr, CastExpr, CallExpr, IndirectCallExpr, ClosureExpr,
    MethodCallExpr,
    NewExpr, DeleteExpr, AllocExpr, FreeExpr,
    FieldAccessExpr, ArrowAccessExpr, IndexExpr,
    AddressOfExpr, DerefExpr,
    IdentifierExpr, LiteralExpr, NullExpr, ThisExpr, SuperExpr,
    TypeNode, NamedType, PointerType, ManagedHandleType, ArrayType,
    FunctionPointerType, NullableType,
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


@dataclass
class VariantInstance:
    """A tagged-union (ADT) value carrying one variant."""
    union_name: str
    variant_name: str
    fields: Dict[str, Box]


@dataclass
class CallableValue:
    """A callable stored in a function pointer value."""
    function: Optional[FunctionDecl] = None
    method: Optional[MethodDecl] = None
    defining_class: Optional[str] = None
    params: List[Any] = field(default_factory=list)
    return_type: Optional[TypeNode] = None
    body: Optional[Block] = None
    captures: Dict[str, Box] = field(default_factory=dict)
    this_val: Optional[Value] = None
    current_class: Optional[str] = None


class _NetConn:
    """A bidirectional in-memory pipe between two endpoints (a fake socket pair).

    The client writes to ``c2s`` and reads ``s2c``; the server does the reverse.
    Backs the net* builtins so a single-process loopback round-trip is
    deterministic — no real OS sockets (those stay a compiled-path capability).
    """

    __slots__ = ("c2s", "s2c", "client_open", "server_open")

    def __init__(self) -> None:
        self.c2s = bytearray()       # client -> server
        self.s2c = bytearray()       # server -> client
        self.client_open = True
        self.server_open = True


class _NetEndpoint:
    __slots__ = ("conn", "is_client")

    def __init__(self, conn: "_NetConn", is_client: bool) -> None:
        self.conn = conn
        self.is_client = is_client


class _NetListener:
    __slots__ = ("port", "backlog", "open")

    def __init__(self, port: int) -> None:
        self.port = port
        self.backlog: List[int] = []   # server-side fds awaiting accept()
        self.open = True


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


class GlangExitException(Exception):
    """Raised by the `exit(code)` builtin to unwind the call stack cleanly."""
    def __init__(self, code: int) -> None:
        self.code = code


class GlangThrowException(Exception):
    """Raised by `throw` statements; caught by `try`/`catch` or the top-level runner."""
    def __init__(self, value: 'Value', line: int, col: int) -> None:
        self.value = value   # Value wrapping an ObjectInstance (Exception subclass)
        self.line = line
        self.col = col


# ---------------------------------------------------------------------------
# Interpreter
# ---------------------------------------------------------------------------

VOID = Value(NamedType("void"), None)
_BINARY_OPERATOR_OVERLOADS = {"+", "-", "*", "/", "%", "==", "!=", "<", "<=", ">", ">="}


class Interpreter:
    def __init__(
        self,
        env: GlobalEnv,
        out=None,
        err=None,
        prog_args: Optional[List[str]] = None,
    ) -> None:
        self._env = env
        self._heap = Heap()
        self._frames: List[Frame] = []
        self._statics: Dict[Tuple[str, str], Box] = {}
        # `print` always records lines in self.output (for tests); when an
        # `out` stream is supplied (e.g. sys.stdout from the CLI) lines are
        # also written to it live, so output survives a mid-run error.
        self.output: List[str] = []
        self._out = out
        # `printErr` mirrors `print` but goes to stderr / self.err_output.
        self.err_output: List[str] = []
        self._err = err
        self._args: List[str] = prog_args if prog_args is not None else []
        self._stack_addr = -1  # negative addresses for non-heap boxes
        # In-memory socket model (see _NetConn): deterministic loopback so the
        # net* builtins run on the interpreter. Real OS sockets stay compiled-only.
        self._net_listeners: Dict[int, _NetListener] = {}   # listener fd -> listener
        self._net_by_port: Dict[int, int] = {}              # port -> listener fd
        self._net_endpoints: Dict[int, _NetEndpoint] = {}   # endpoint fd -> endpoint
        self._net_next_fd = 3                               # 0..2 reserved (std streams)
        self._net_next_eph = 40000                          # ephemeral port allocator
        self._net_would_block = False                       # last call hit a would-block
        self._net_errno = 0                                 # last call's errno-ish code

        # term* builtins: raw-mode lifecycle + signal flags (mirror the C runtime).
        self._term_saved = None                             # saved termios (raw mode off)
        self._term_raw_active = False
        self._term_winch = False                            # SIGWINCH since last poll
        self._term_intr = False                             # SIGINT since last poll
        self._term_handlers_installed = False

    # -- public entry ----------------------------------------------------

    def run(self, program: Program) -> int:
        self._init_statics(program)
        main = self._env.functions.get("main")
        if main is None:
            raise GlangRuntimeError("no 'main' function", 0, 0)
        try:
            result = self._call_function(main.decl, [])
        except GlangExitException as e:
            return e.code
        except GlangThrowException as e:
            import sys as _sys
            raw_msg = self._exception_message(e.value)
            class_name = self._exception_class(e.value)
            msg = f"Unhandled {class_name}: {raw_msg}"
            self.err_output.append(msg)
            if self._err is not None:
                self._err.write(msg + "\n")
            else:
                _sys.stderr.write(msg + "\n")
            return 1
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
                        box = self._new_box(self._coerce_value(val, sfd.type))
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
            frame.define(param.name, self._new_box(self._coerce_value(arg, param.type)))
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
            frame.define(param.name, self._new_box(self._coerce_value(arg, param.type)))
        return self._run_body(frame, method.body, method.return_type)

    def _run_body(self, frame: Frame, body: Block, return_type: TypeNode) -> Value:
        self._frames.append(frame)
        try:
            for stmt in body.stmts:
                self._exec_stmt(stmt)
        except ReturnSignal as ret:
            return self._coerce_value(ret.value, return_type)
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

    def _exec_match(self, stmt: MatchStmt) -> None:
        val = self._eval(stmt.scrutinee)
        # Auto-deref pointer-to-union.
        if isinstance(val.raw, Pointer):
            val = self._deref(val, stmt.line, stmt.col).value
        inst = val.raw
        if not isinstance(inst, VariantInstance):
            raise GlangRuntimeError(
                "match scrutinee is not a union value", stmt.line, stmt.col
            )
        for arm in stmt.arms:
            if isinstance(arm.pattern, WildcardPattern):
                self._exec_block(arm.body)
                return
            if arm.pattern.variant_name == inst.variant_name:
                self._frame.push_scope()
                try:
                    field_names = list(inst.fields.keys())
                    for binding, fname in zip(arm.pattern.bindings, field_names):
                        self._frame.define(binding, inst.fields[fname])
                    self._exec_block(arm.body)
                finally:
                    self._frame.pop_scope()
                return
        raise GlangRuntimeError(
            f"non-exhaustive match: no arm matched variant '{inst.variant_name}'",
            stmt.line, stmt.col,
        )

    def _exec_stmt(self, stmt: Stmt) -> None:
        if isinstance(stmt, Block):
            self._exec_block(stmt)

        elif isinstance(stmt, VarDecl):
            init = self._eval(stmt.initializer)
            self._frame.define(stmt.name, self._new_box(self._coerce_value(init, stmt.type)))

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

        elif isinstance(stmt, DoWhileStmt):
            while True:
                try:
                    self._exec_block(stmt.body)
                except BreakSignal:
                    break
                except ContinueSignal:
                    pass
                if not self._eval(stmt.condition).raw:
                    break

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

        elif isinstance(stmt, ForeachStmt):
            iterable = self._eval(stmt.iterable)
            self._frame.push_scope()
            try:
                box = self._new_box(self._zero_value(stmt.var_type))
                self._frame.define(stmt.var_name, box)
                for item in self._foreach_values(iterable, stmt.line, stmt.col):
                    self._store(box, item)
                    try:
                        self._exec_block(stmt.body)
                    except BreakSignal:
                        break
                    except ContinueSignal:
                        continue
            finally:
                self._frame.pop_scope()

        elif isinstance(stmt, UsingStmt):
            self._exec_using(stmt)

        elif isinstance(stmt, ReturnStmt):
            value = self._eval(stmt.value) if stmt.value is not None else VOID
            raise ReturnSignal(value)

        elif isinstance(stmt, BreakStmt):
            raise BreakSignal()

        elif isinstance(stmt, ContinueStmt):
            raise ContinueSignal()

        elif isinstance(stmt, ThrowStmt):
            exc_val = self._eval(stmt.value)
            raise GlangThrowException(exc_val, stmt.line, stmt.col)

        elif isinstance(stmt, TryCatchStmt):
            try:
                self._exec_block(stmt.body)
            except GlangThrowException as exc:
                thrown_class = self._exception_class(exc.value)
                chain = superclass_chain(thrown_class, self._env)
                handled = False
                for clause in stmt.catches:
                    catch_class = clause.catch_type.base.name
                    if catch_class in chain:
                        self._frame.push_scope()
                        try:
                            box = self._new_box(exc.value)
                            self._frame.define(clause.var_name, box)
                            self._exec_block(clause.body)
                        finally:
                            self._frame.pop_scope()
                        handled = True
                        break
                if not handled:
                    raise

        elif isinstance(stmt, MatchStmt):
            self._exec_match(stmt)

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
            if box is not None:
                return box.value
            fn = self._env.functions.get(expr.name)
            if fn is not None:
                return self._make_function_value(fn.decl)
            raise GlangRuntimeError(
                f"undefined variable '{expr.name}'", expr.line, expr.col
            )

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
            if expr.count is not None:
                n = self._eval(expr.count).raw
                if n < 0:
                    raise GlangRuntimeError(
                        "alloc count must be non-negative", expr.line, expr.col
                    )
                elements = [
                    self._new_box(self._zero_value(expr.type)) for _ in range(n)
                ]
                block = Value(ArrayType(expr.type, n), elements)
                box = self._heap.alloc(block)
                return Value(PointerType(expr.type), Pointer(box))
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

        if isinstance(expr, IndirectCallExpr):
            callee = self._eval(expr.callee)
            args = [self._eval(a) for a in expr.args]
            return self._call_callable(callee, args, expr.line, expr.col)

        if isinstance(expr, ClosureExpr):
            return self._eval_closure(expr)

        if isinstance(expr, MethodCallExpr):
            return self._eval_method_call(expr)

        if isinstance(expr, NewExpr):
            return self._eval_new(expr)

        if isinstance(expr, DeleteExpr):
            return self._eval_delete(expr)

        if isinstance(expr, FieldAccessExpr):
            method_ref = self._static_method_ref(expr)
            if method_ref is not None:
                return method_ref
            return self._resolve_lvalue(expr).value

        if isinstance(expr, IndexExpr):
            return self._eval_index(expr)

        if isinstance(expr, ArrowAccessExpr):
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
        if expr.op == "??":
            left = self._eval(expr.left)
            if left.raw is not None:
                base_t = left.type.base if isinstance(left.type, NullableType) else left.type
                return Value(base_t, left.raw)
            return self._eval(expr.right)
        left = self._eval(expr.left)
        right = self._eval(expr.right)
        return self._apply_binary(expr.op, left, right, expr.line, expr.col)

    def _apply_binary(
        self, op: str, left: Value, right: Value, line: int, col: int
    ) -> Value:
        l, r = left.raw, right.raw

        overloaded = self._try_apply_binary_operator(op, left, right, line, col)
        if overloaded is not None:
            return overloaded

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
        l_byte = self._is(left, "byte")
        r_byte = self._is(right, "byte")
        # A byte computes like int but stays byte, wrapping modulo 256. Pass2
        # guarantees a byte only ever meets a byte or an int *literal*, so any
        # byte/int pairing at runtime is a byte operation.
        byte_op = (l_byte or r_byte) and (l_byte or l_int) and (r_byte or r_int)
        both_int = l_int and r_int

        if op == "+":
            if self._is(left, "string"):
                return Value(NamedType("string"), l + r)
            if both_int:
                return Value(NamedType("int"), l + r)
            if byte_op:
                return Value(NamedType("byte"), (l + r) & 0xFF)
            return Value(NamedType("float"), l + r)
        if op == "-":
            if byte_op:
                return Value(NamedType("byte"), (l - r) & 0xFF)
            t = "int" if both_int else "float"
            return Value(NamedType(t), l - r)
        if op == "*":
            if byte_op:
                return Value(NamedType("byte"), (l * r) & 0xFF)
            t = "int" if both_int else "float"
            return Value(NamedType(t), l * r)
        if op == "/":
            if both_int:
                return Value(NamedType("int"), self._cdiv(l, r, line, col))
            if byte_op:
                return Value(NamedType("byte"), self._cdiv(l, r, line, col) & 0xFF)
            return Value(NamedType("float"), l / r)
        if op == "%":
            if byte_op:
                return Value(NamedType("byte"), self._cmod(l, r, line, col) & 0xFF)
            return Value(NamedType("int"), self._cmod(l, r, line, col))

        bit_t = "byte" if byte_op else "int"
        bit_mask = 0xFF if byte_op else None

        def _bit(v: int) -> Value:
            return Value(NamedType(bit_t), v & bit_mask if bit_mask is not None else v)

        if op == "&":
            return _bit(l & r)
        if op == "|":
            return _bit(l | r)
        if op == "^":
            return _bit(l ^ r)
        if op == "<<":
            return _bit(l << r)
        if op == ">>":
            return _bit(l >> r)

        raise GlangRuntimeError(f"unknown operator '{op}'", line, col)

    def _values_equal(self, left: Value, right: Value) -> bool:
        if isinstance(left.type, FunctionPointerType) or isinstance(right.type, FunctionPointerType):
            left_null = (
                left.raw is None
                or (isinstance(left.raw, Pointer) and left.raw.target is None)
            )
            right_null = (
                right.raw is None
                or (isinstance(right.raw, Pointer) and right.raw.target is None)
            )
            if left_null or right_null:
                return left_null and right_null
            if isinstance(left.raw, CallableValue) and isinstance(right.raw, CallableValue):
                return self._callables_equal(left.raw, right.raw)
            return False
        if isinstance(left.raw, Pointer) or isinstance(right.raw, Pointer):
            lt = left.raw.target if isinstance(left.raw, Pointer) else None
            rt = right.raw.target if isinstance(right.raw, Pointer) else None
            return lt is rt
        return left.raw == right.raw

    def _eval_unary(self, expr: UnaryExpr) -> Value:
        if expr.op in ("++", "--"):
            box = self._resolve_lvalue(expr.operand)
            operand_t = box.value.type
            new = box.value.raw + (1 if expr.op == "++" else -1)
            # Preserve the operand's static type; _store masks byte to 0..255.
            self._store(box, Value(operand_t, new))
            return box.value

        operand = self._eval(expr.operand)
        if expr.op == "!":
            return Value(NamedType("bool"), not operand.raw)
        if expr.op == "~":
            if self._is(operand, "byte"):
                return Value(NamedType("byte"), (~operand.raw) & 0xFF)
            return Value(NamedType("int"), ~operand.raw)
        if expr.op == "-":
            if self._is(operand, "byte"):
                return Value(NamedType("byte"), (-operand.raw) & 0xFF)
            t = "int" if self._is(operand, "int") else "float"
            return Value(NamedType(t), -operand.raw)
        if expr.op == "+":
            return operand
        raise GlangRuntimeError(f"unknown unary operator '{expr.op}'", expr.line, expr.col)

    def _callables_equal(self, left: CallableValue, right: CallableValue) -> bool:
        if left.function is not None or right.function is not None:
            return left.function is right.function
        if left.method is not None or right.method is not None:
            return (
                left.method is right.method
                and left.defining_class == right.defining_class
            )
        return left is right

    def _eval_cast(self, expr: CastExpr) -> Value:
        src = self._eval(expr.expr)
        target = expr.target_type
        if isinstance(target, NamedType):
            if target.name == "int":
                if self._is(src, "char"):
                    return Value(target, ord(src.raw))
                return Value(target, int(src.raw))
            if target.name == "byte":
                if self._is(src, "char"):
                    return Value(target, ord(src.raw) & 0xFF)
                return Value(target, int(src.raw) & 0xFF)
            if target.name == "float":
                return Value(target, float(src.raw))
            if target.name == "char":
                if self._is(src, "int") or self._is(src, "byte"):
                    return Value(target, chr(src.raw & 0xFF))
                return Value(target, src.raw)
        # pointer reinterpret-cast: keep the raw pointer, retag the type
        return Value(target, src.raw)

    def _eval_call(self, expr: CallExpr) -> Value:
        box = self._frame.lookup(expr.name)
        if box is not None:
            args = [self._eval(a) for a in expr.args]
            return self._call_callable(box.value, args, expr.line, expr.col)

        if self._is_builtin_call(expr.name):
            return self._eval_builtin_call(expr)

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

    def _is_builtin_call(self, name: str) -> bool:
        return name in {
            "print",
            "printErr",
            "len",
            "substr",
            "parseInt",
            "parseFloat",
            "toString",
            "startsWith",
            "endsWith",
            "contains",
            "indexOf",
            "readFile",
            "writeFile",
            "fileExists",
            "fileSize",
            "readFileInto",
            "writeFileFrom",
            "listDir",
            "bytesFromString",
            "stringFromBytes",
            "getArgCount",
            "getArg",
            "exit",
            "intToStr",
            "readStdin",
            "readByte",
            "writeStdout",
            "termRawOn",
            "termRawOff",
            "termWidth",
            "termHeight",
            "readByteTimeout",
            "termResized",
            "termInterrupted",
            "shell",
            "nowNanos",
            "wallMillis",
            "sleepMs",
            "netListen",
            "netLocalPort",
            "netAccept",
            "netConnect",
            "netRecv",
            "netSend",
            "netClose",
            "netConnectNb",
            "netSetNonBlocking",
            "netSetNoDelay",
            "netShutdown",
            "netSockError",
            "netErrno",
            "netWouldBlock",
            "netPoll",
        }

    # -- terminal control (parity with glang_runtime.c term* builtins) ------

    def _install_term_handlers(self) -> None:
        if self._term_handlers_installed:
            return
        import signal as _signal
        import atexit as _atexit

        def _on_winch(signum, frame):  # noqa: ARG001
            self._term_winch = True

        def _on_intr(signum, frame):  # noqa: ARG001
            self._term_intr = True

        try:
            _signal.signal(_signal.SIGWINCH, _on_winch)
            _signal.signal(_signal.SIGINT, _on_intr)
        except (ValueError, OSError):
            # Not the main thread, or platform without SIGWINCH — flags simply
            # never fire, which is acceptable degraded behaviour.
            pass
        _atexit.register(self._term_raw_off)
        self._term_handlers_installed = True

    def _term_raw_on(self) -> int:
        import sys as _sys
        import os as _os
        try:
            fd = _sys.stdin.fileno()
        except (ValueError, OSError):
            return -1
        if not _os.isatty(fd):
            return -1
        import termios
        import tty
        try:
            saved = termios.tcgetattr(fd)
        except termios.error:
            return -1
        if not self._term_raw_active:
            self._term_saved = saved
            self._install_term_handlers()
        try:
            tty.setraw(fd)
        except termios.error:
            return -1
        self._term_raw_active = True
        return 0

    def _term_raw_off(self) -> int:
        if self._term_raw_active and self._term_saved is not None:
            import sys as _sys
            import termios
            try:
                termios.tcsetattr(
                    _sys.stdin.fileno(), termios.TCSAFLUSH, self._term_saved
                )
            except (termios.error, ValueError, OSError):
                pass
            self._term_raw_active = False
        return 0

    def _term_size(self, index: int) -> int:
        # index 0 -> rows (height), 1 -> cols (width)
        import sys as _sys
        try:
            import fcntl
            import termios
            import struct

            packed = fcntl.ioctl(
                _sys.stdout.fileno(),
                termios.TIOCGWINSZ,
                struct.pack("HHHH", 0, 0, 0, 0),
            )
            rows, cols, _xp, _yp = struct.unpack("HHHH", packed)
        except (ImportError, OSError, ValueError):
            return -1
        val = rows if index == 0 else cols
        return val if val > 0 else -1

    def _read_byte_timeout(self, ms: int) -> int:
        import sys as _sys
        import os as _os
        import select as _select
        try:
            fd = _sys.stdin.fileno()
        except (ValueError, OSError):
            return -1
        timeout = None if ms < 0 else ms / 1000.0
        try:
            ready, _w, _e = _select.select([fd], [], [], timeout)
        except (OSError, ValueError):
            return -2
        if not ready:
            return -2
        try:
            b = _os.read(fd, 1)
        except OSError:
            return -1
        if not b:
            return -1
        return b[0]

    def _eval_builtin_call(self, expr: CallExpr) -> Value:
        if expr.name == "print":
            self._do_print(self._eval(expr.args[0]))
            return VOID

        if expr.name == "printErr":
            self._do_print_err(self._eval(expr.args[0]))
            return VOID

        if expr.name == "getArgCount":
            return Value(NamedType("int"), len(self._args))

        if expr.name == "getArg":
            idx = int(self._eval(expr.args[0]).raw)
            if idx < 0 or idx >= len(self._args):
                raise GlangRuntimeError(
                    f"getArg index {idx} out of range (have {len(self._args)} args)",
                    expr.line, expr.col,
                )
            return Value(NamedType("string"), self._args[idx])

        if expr.name == "exit":
            code = int(self._eval(expr.args[0]).raw)
            raise GlangExitException(code)

        if expr.name == "len":
            value = self._eval(expr.args[0])
            return Value(NamedType("int"), len(value.raw))

        if expr.name == "substr":
            source = self._eval(expr.args[0]).raw
            start = self._eval(expr.args[1]).raw
            end = self._eval(expr.args[2]).raw
            if start < 0 or end < start or end > len(source):
                raise GlangRuntimeError(
                    "substring range out of bounds", expr.line, expr.col
                )
            return Value(NamedType("string"), source[start:end])

        if expr.name == "bytesFromString":
            text = self._eval(expr.args[0]).raw
            byte_t = NamedType("byte")
            elements = [
                self._new_box(Value(byte_t, ord(ch) & 0xFF)) for ch in text
            ]
            block = Value(ArrayType(byte_t, len(elements)), elements)
            box = self._heap.alloc(block)
            return Value(PointerType(byte_t), Pointer(box))

        if expr.name == "stringFromBytes":
            data = self._eval(expr.args[0])
            n = self._eval(expr.args[1]).raw
            if n < 0:
                raise GlangRuntimeError(
                    "stringFromBytes length must be non-negative", expr.line, expr.col
                )
            block = self._deref(data, expr.line, expr.col)
            elements = block.value.raw
            if not isinstance(elements, list) or n > len(elements):
                raise GlangRuntimeError(
                    "stringFromBytes length out of bounds", expr.line, expr.col
                )
            chars = [chr(elements[i].value.raw & 0xFF) for i in range(n)]
            return Value(NamedType("string"), "".join(chars))

        if expr.name == "parseInt":
            text = self._eval(expr.args[0]).raw
            try:
                return Value(NamedType("int"), int(text, 0))
            except ValueError:
                raise GlangRuntimeError(
                    f"parseInt invalid integer '{text}'", expr.line, expr.col
                ) from None

        if expr.name == "parseFloat":
            text = self._eval(expr.args[0]).raw
            try:
                return Value(NamedType("float"), float(text))
            except ValueError:
                raise GlangRuntimeError(
                    f"parseFloat invalid float '{text}'", expr.line, expr.col
                ) from None

        if expr.name == "toString":
            value = self._eval(expr.args[0])
            return Value(NamedType("string"), self._value_to_string(value))

        if expr.name == "readFile":
            path = self._eval(expr.args[0]).raw
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return Value(NamedType("string"), f.read())
            except OSError as e:
                raise GlangRuntimeError(
                    f"readFile failed for '{path}': {e.strerror or e}",
                    expr.line, expr.col,
                ) from None

        if expr.name == "writeFile":
            path = self._eval(expr.args[0]).raw
            content = self._eval(expr.args[1]).raw
            try:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(content)
            except OSError as e:
                raise GlangRuntimeError(
                    f"writeFile failed for '{path}': {e.strerror or e}",
                    expr.line, expr.col,
                ) from None
            return VOID

        if expr.name == "fileExists":
            path = self._eval(expr.args[0]).raw
            return Value(NamedType("bool"), os.path.isfile(path))

        if expr.name == "fileSize":
            path = self._eval(expr.args[0]).raw
            try:
                return Value(NamedType("int"), os.path.getsize(path))
            except OSError:
                return Value(NamedType("int"), -1)

        if expr.name == "readFileInto":
            path = self._eval(expr.args[0]).raw
            buf = self._eval(expr.args[1])
            cap = int(self._eval(expr.args[2]).raw)
            if cap <= 0:
                return Value(NamedType("int"), 0)
            try:
                with open(path, "rb") as f:
                    data = f.read(cap)
            except OSError:
                return Value(NamedType("int"), -1)
            elements = self._deref(buf, expr.line, expr.col).value.raw
            byte_t = NamedType("byte")
            n = min(len(data), len(elements))
            for i in range(n):
                elements[i].value = Value(byte_t, data[i])
            return Value(NamedType("int"), n)

        if expr.name == "writeFileFrom":
            path = self._eval(expr.args[0]).raw
            buf = self._eval(expr.args[1])
            length = int(self._eval(expr.args[2]).raw)
            if length < 0:
                return Value(NamedType("int"), -1)
            elements = self._deref(buf, expr.line, expr.col).value.raw
            n = min(length, len(elements))
            data = bytes(int(elements[i].value.raw) & 0xFF for i in range(n))
            try:
                with open(path, "wb") as f:
                    f.write(data)
            except OSError:
                return Value(NamedType("int"), -1)
            return Value(NamedType("int"), n)

        if expr.name == "listDir":
            path = self._eval(expr.args[0]).raw
            try:
                names = sorted(os.listdir(path))
            except OSError:
                return Value(NamedType("string"), "")
            joined = "".join(name + "\n" for name in names)
            return Value(NamedType("string"), joined)

        if expr.name == "intToStr":
            n = self._eval(expr.args[0]).raw
            return Value(NamedType("string"), str(int(n)))

        if expr.name == "readStdin":
            import sys as _sys
            return Value(NamedType("string"), _sys.stdin.read())

        if expr.name == "readByte":
            import sys as _sys
            b = _sys.stdin.buffer.read(1)
            return Value(NamedType("int"), -1 if not b else b[0])

        if expr.name == "writeStdout":
            import sys as _sys
            s = str(self._eval(expr.args[0]).raw)
            # Raw write, no trailing newline (mirrors glang_writestdout in the
            # C runtime). Goes to the real stream when one is wired (CLI mode).
            if self._out is not None:
                self._out.write(s)
                self._out.flush()
            else:
                _sys.stdout.write(s)
                _sys.stdout.flush()
            return Value(NamedType("void"), None)

        if expr.name == "termRawOn":
            return Value(NamedType("int"), self._term_raw_on())
        if expr.name == "termRawOff":
            return Value(NamedType("int"), self._term_raw_off())
        if expr.name == "termWidth":
            return Value(NamedType("int"), self._term_size(1))
        if expr.name == "termHeight":
            return Value(NamedType("int"), self._term_size(0))
        if expr.name == "readByteTimeout":
            ms = int(self._eval(expr.args[0]).raw)
            return Value(NamedType("int"), self._read_byte_timeout(ms))
        if expr.name == "termResized":
            v = self._term_winch
            self._term_winch = False
            return Value(NamedType("bool"), v)
        if expr.name == "termInterrupted":
            v = self._term_intr
            self._term_intr = False
            return Value(NamedType("bool"), v)

        if expr.name == "shell":
            import subprocess as _sp
            cmd = str(self._eval(expr.args[0]).raw)
            try:
                out = _sp.run(
                    cmd, shell=True, capture_output=True, text=True, timeout=30
                ).stdout
            except Exception:
                out = ""
            return Value(NamedType("string"), out)

        if expr.name == "nowNanos":
            import time as _time
            return Value(NamedType("int"), _time.monotonic_ns())

        if expr.name == "wallMillis":
            import time as _time
            return Value(NamedType("int"), int(_time.time() * 1000))

        if expr.name == "sleepMs":
            import time as _time
            ms = int(self._eval(expr.args[0]).raw)
            if ms > 0:
                _time.sleep(ms / 1000.0)
            return VOID

        if expr.name == "netListen":
            port = int(self._eval(expr.args[0]).raw)
            if port == 0:
                port = self._net_next_eph
                self._net_next_eph += 1
            elif port in self._net_by_port:
                return Value(NamedType("int"), -1)   # address already in use
            fd = self._net_next_fd
            self._net_next_fd += 1
            self._net_listeners[fd] = _NetListener(port)
            self._net_by_port[port] = fd
            return Value(NamedType("int"), fd)

        if expr.name == "netLocalPort":
            fd = int(self._eval(expr.args[0]).raw)
            lis = self._net_listeners.get(fd)
            return Value(NamedType("int"), lis.port if lis is not None else -1)

        if expr.name == "netAccept":
            fd = int(self._eval(expr.args[0]).raw)
            lis = self._net_listeners.get(fd)
            if lis is None or not lis.backlog:
                return Value(NamedType("int"), -1)   # would block / not listening
            return Value(NamedType("int"), lis.backlog.pop(0))

        if expr.name == "netConnect":
            self._eval(expr.args[0])                 # host is ignored (loopback)
            port = int(self._eval(expr.args[1]).raw)
            lfd = self._net_by_port.get(port)
            lis = self._net_listeners.get(lfd) if lfd is not None else None
            if lis is None or not lis.open:
                return Value(NamedType("int"), -1)   # connection refused
            conn = _NetConn()
            cfd = self._net_next_fd
            sfd = self._net_next_fd + 1
            self._net_next_fd += 2
            self._net_endpoints[cfd] = _NetEndpoint(conn, True)
            self._net_endpoints[sfd] = _NetEndpoint(conn, False)
            lis.backlog.append(sfd)
            return Value(NamedType("int"), cfd)

        if expr.name == "netRecv":
            fd = int(self._eval(expr.args[0]).raw)
            buf = self._eval(expr.args[1])
            cap = int(self._eval(expr.args[2]).raw)
            ep = self._net_endpoints.get(fd)
            if ep is None:
                return Value(NamedType("int"), -1)
            if cap <= 0:
                return Value(NamedType("int"), 0)
            inbound = ep.conn.s2c if ep.is_client else ep.conn.c2s
            peer_open = ep.conn.server_open if ep.is_client else ep.conn.client_open
            if not inbound:
                # Empty: peer closed -> EOF (0); peer still open -> would block.
                if not peer_open:
                    self._net_would_block = False
                    return Value(NamedType("int"), 0)
                self._net_would_block = True
                self._net_errno = 35   # EAGAIN
                return Value(NamedType("int"), -1)
            self._net_would_block = False
            block = self._deref(buf, expr.line, expr.col)
            elements = block.value.raw
            n = min(cap, len(inbound), len(elements))
            byte_t = NamedType("byte")
            for i in range(n):
                elements[i].value = Value(byte_t, inbound[i])
            del inbound[:n]
            return Value(NamedType("int"), n)

        if expr.name == "netSend":
            fd = int(self._eval(expr.args[0]).raw)
            buf = self._eval(expr.args[1])
            length = int(self._eval(expr.args[2]).raw)
            ep = self._net_endpoints.get(fd)
            if ep is None:
                return Value(NamedType("int"), -1)
            if length <= 0:
                return Value(NamedType("int"), 0)
            peer_open = ep.conn.server_open if ep.is_client else ep.conn.client_open
            if not peer_open:
                self._net_would_block = False
                self._net_errno = 32   # EPIPE
                return Value(NamedType("int"), -1)   # broken pipe
            self._net_would_block = False
            outbound = ep.conn.c2s if ep.is_client else ep.conn.s2c
            block = self._deref(buf, expr.line, expr.col)
            elements = block.value.raw
            n = min(length, len(elements))
            for i in range(n):
                outbound.append(int(elements[i].value.raw) & 0xFF)
            return Value(NamedType("int"), n)

        if expr.name == "netClose":
            fd = int(self._eval(expr.args[0]).raw)
            lis = self._net_listeners.get(fd)
            if lis is not None:
                lis.open = False
                if self._net_by_port.get(lis.port) == fd:
                    del self._net_by_port[lis.port]
                del self._net_listeners[fd]
                return VOID
            ep = self._net_endpoints.get(fd)
            if ep is not None:
                if ep.is_client:
                    ep.conn.client_open = False
                else:
                    ep.conn.server_open = False
                del self._net_endpoints[fd]
            return VOID

        if expr.name == "netConnectNb":
            # The loopback model connects instantly; identical to netConnect.
            self._eval(expr.args[0])
            port = int(self._eval(expr.args[1]).raw)
            lfd = self._net_by_port.get(port)
            lis = self._net_listeners.get(lfd) if lfd is not None else None
            if lis is None or not lis.open:
                self._net_errno = 61   # ECONNREFUSED
                return Value(NamedType("int"), -1)
            conn = _NetConn()
            cfd = self._net_next_fd
            sfd = self._net_next_fd + 1
            self._net_next_fd += 2
            self._net_endpoints[cfd] = _NetEndpoint(conn, True)
            self._net_endpoints[sfd] = _NetEndpoint(conn, False)
            lis.backlog.append(sfd)
            return Value(NamedType("int"), cfd)

        if expr.name == "netSetNonBlocking":
            self._eval(expr.args[0])
            return Value(NamedType("int"), 0)   # the model is always non-blocking

        if expr.name == "netSetNoDelay":
            self._eval(expr.args[0])
            return Value(NamedType("int"), 0)   # no-op in the model

        if expr.name == "netSockError":
            self._eval(expr.args[0])
            return Value(NamedType("int"), 0)   # connect completes instantly

        if expr.name == "netErrno":
            return Value(NamedType("int"), self._net_errno)

        if expr.name == "netWouldBlock":
            return Value(NamedType("bool"), self._net_would_block)

        if expr.name == "netShutdown":
            fd = int(self._eval(expr.args[0]).raw)
            how = int(self._eval(expr.args[1]).raw)
            ep = self._net_endpoints.get(fd)
            if ep is None:
                return Value(NamedType("int"), -1)
            if how != 0:   # write or both: peer drains then sees EOF
                if ep.is_client:
                    ep.conn.client_open = False
                else:
                    ep.conn.server_open = False
            return Value(NamedType("int"), 0)

        if expr.name == "netPoll":
            fds_v = self._eval(expr.args[0])
            events_v = self._eval(expr.args[1])
            revents_v = self._eval(expr.args[2])
            count = int(self._eval(expr.args[3]).raw)
            self._eval(expr.args[4])   # timeout: model never blocks
            fds_el = self._deref(fds_v, expr.line, expr.col).value.raw
            ev_el = self._deref(events_v, expr.line, expr.col).value.raw
            rev_el = self._deref(revents_v, expr.line, expr.col).value.raw
            int_t = NamedType("int")
            ready = 0
            for i in range(count):
                fd = int(fds_el[i].value.raw)
                want = int(ev_el[i].value.raw)
                r = 0
                lis = self._net_listeners.get(fd)
                if lis is not None:
                    if (want & 1) and lis.backlog:
                        r |= 1
                else:
                    ep = self._net_endpoints.get(fd)
                    if ep is not None:
                        inbound = ep.conn.s2c if ep.is_client else ep.conn.c2s
                        peer_open = (ep.conn.server_open if ep.is_client
                                     else ep.conn.client_open)
                        # Readable if data waiting or peer closed (recv -> 0/EOF).
                        if (want & 1) and (inbound or not peer_open):
                            r |= 1
                        # Writable while the peer can still receive.
                        if (want & 2) and peer_open:
                            r |= 2
                    else:
                        r |= 4   # unknown fd -> error
                rev_el[i].value = Value(int_t, r)
                if r:
                    ready += 1
            return Value(NamedType("int"), ready)

        source = self._eval(expr.args[0]).raw
        needle = self._eval(expr.args[1]).raw
        if expr.name == "startsWith":
            return Value(NamedType("bool"), source.startswith(needle))
        if expr.name == "endsWith":
            return Value(NamedType("bool"), source.endswith(needle))
        if expr.name == "contains":
            return Value(NamedType("bool"), needle in source)
        if expr.name == "indexOf":
            return Value(NamedType("int"), source.find(needle))

        raise GlangRuntimeError(f"undefined function '{expr.name}'", expr.line, expr.col)

    def _eval_closure(self, expr: ClosureExpr) -> Value:
        captures: Dict[str, Box] = {}
        for name in expr.captures:
            box = self._frame.lookup(name)
            if box is None:
                raise GlangRuntimeError(
                    f"undefined variable '{name}'", expr.line, expr.col
                )
            captures[name] = self._new_box(Value(box.value.type, box.value.raw))

        callable_value = CallableValue(
            params=expr.params,
            return_type=expr.return_type,
            body=expr.body,
            captures=captures,
            this_val=self._frame.this_val,
            current_class=self._frame.current_class,
        )
        return Value(
            self._function_type(expr.params, expr.return_type),
            callable_value,
        )

    def _call_callable(
        self, callee: Value, args: List[Value], line: int, col: int
    ) -> Value:
        raw = callee.raw
        if raw is None or (isinstance(raw, Pointer) and raw.target is None):
            raise GlangRuntimeError("null function pointer call", line, col)
        if not isinstance(raw, CallableValue):
            raise GlangRuntimeError("call of a non-function pointer", line, col)

        if raw.function is not None:
            return self._call_function(raw.function, args)
        if raw.method is not None:
            return self._call_method(raw.method, raw.defining_class, None, args)
        if raw.body is not None and raw.return_type is not None:
            frame = Frame(this_val=raw.this_val, current_class=raw.current_class)
            for name, box in raw.captures.items():
                frame.define(name, box)
            for param, arg in zip(raw.params, args):
                frame.define(param.name, self._new_box(self._coerce_value(arg, param.type)))
            return self._run_body(frame, raw.body, raw.return_type)

        raise GlangRuntimeError("invalid function pointer", line, col)

    def _eval_method_call(self, expr: MethodCallExpr) -> Value:
        # Union variant constructor: Shape.Circle(radius)
        if (
            not expr.is_arrow
            and isinstance(expr.object, IdentifierExpr)
            and self._env.is_union(expr.object.name)
            and self._frame.lookup(expr.object.name) is None
        ):
            union_name = expr.object.name
            union_info = self._env.unions[union_name]
            variant_info = union_info.variants[expr.method]
            field_values = [self._eval(a) for a in expr.args]
            fields = {
                fd.name: self._new_box(self._coerce_value(fv, fd.type))
                for fd, fv in zip(variant_info.fields, field_values)
            }
            inst = VariantInstance(
                union_name=union_name, variant_name=expr.method, fields=fields
            )
            return Value(NamedType(union_name), inst)

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
        # Primitive modifier path (e.g. "hello".any(...), where string is not
        # an ObjectInstance and cannot go through _receiver).
        if not isinstance(receiver.raw, (Pointer, ObjectInstance)):
            if isinstance(receiver.type, NamedType):
                mod = self._env.modifier_methods.get(receiver.type.name, {})
                if expr.method in mod:
                    return self._call_method(mod[expr.method], receiver.type.name, receiver, args)
        instance, this_val = self._receiver(receiver, expr.line, expr.col)
        method, defining = self._resolve_virtual(instance.class_name, expr.method)
        return self._call_method(method, defining, this_val, args)

    def _eval_new(self, expr: NewExpr) -> Value:
        # Union variant heap allocation: new Shape.Circle(args)
        if "." in expr.class_name:
            union_name, variant_name = expr.class_name.split(".", 1)
            union_info = self._env.unions[union_name]
            variant_info = union_info.variants[variant_name]
            field_values = [self._eval(a) for a in expr.args]
            fields = {
                fd.name: self._new_box(self._coerce_value(fv, fd.type))
                for fd, fv in zip(variant_info.fields, field_values)
            }
            inst = VariantInstance(
                union_name=union_name, variant_name=variant_name, fields=fields
            )
            val = Value(NamedType(union_name), inst)
            box = self._heap.alloc(val)
            return Value(PointerType(NamedType(union_name)), Pointer(box))
        this_val = self._instantiate(expr.class_name, on_heap=True)
        args = [self._eval(a) for a in expr.args]
        self._run_constructor(expr.class_name, this_val, args)
        info = self._env.classes.get(expr.class_name)
        if info is not None and info.is_managed:
            # A managed object is reached through a handle (T@); its raw value is
            # the same heap reference, but its declared type marks it managed.
            return Value(ManagedHandleType(NamedType(expr.class_name)), this_val.raw)
        return this_val

    def _eval_delete(self, expr: DeleteExpr) -> Value:
        value = self._eval(expr.operand)
        ptr = value.raw
        if not isinstance(ptr, Pointer) or ptr.target is None:
            return VOID  # delete null is a no-op
        if ptr.target.freed:
            raise GlangRuntimeError("delete of a freed pointer", expr.line, expr.col)
        self._delete_object(value)
        return VOID

    def _delete_object(self, value: Value) -> None:
        """Run the destructor chain for a live class pointer, then free it."""
        box = value.raw.target
        instance = box.value.raw
        if not isinstance(instance, VariantInstance):
            # Destructor chain: most-derived class first, up to the base.
            for cls in superclass_chain(instance.class_name, self._env):
                info = self._env.classes.get(cls)
                if info is not None and info.destructor is not None:
                    self._call_method(_as_method(info.destructor), cls, value, [])
        self._heap.free(box)

    # -- using blocks ------------------------------------------------------

    def _exec_using(self, stmt: UsingStmt) -> None:
        self._frame.push_scope()
        try:
            init = self._eval(stmt.decl.initializer)
            box = self._new_box(self._coerce_value(init, stmt.decl.type))
            self._frame.define(stmt.decl.name, box)
            try:
                self._exec_block(stmt.body)
            except GlangExitException:
                raise  # exit() terminates immediately; skip disposal
            except BaseException:
                self._dispose_resource(box.value, stmt)
                raise
            else:
                self._dispose_resource(box.value, stmt)
        finally:
            self._frame.pop_scope()

    def _dispose_resource(self, value: Value, stmt: UsingStmt) -> None:
        raw = value.raw
        if isinstance(raw, Pointer):
            # Null or already released inside the body: nothing left to do,
            # so early manual `delete`/`free` is safe.
            if raw.target is None or raw.target.freed:
                return
            if isinstance(raw.target.value.raw, ObjectInstance):
                self._delete_object(value)
            else:
                self._heap.free(raw.target)
            return
        if isinstance(raw, ObjectInstance):
            instance, this_val = self._receiver(value, stmt.line, stmt.col)
            method, defining = self._resolve_virtual(instance.class_name, "dispose")
            self._call_method(method, defining, this_val, [])
            return
        raise GlangRuntimeError(
            "using resource is not disposable", stmt.line, stmt.col
        )

    # -- object construction / dispatch ----------------------------------

    def _instantiate(self, class_name: str, *, on_heap: bool) -> Value:
        fields: Dict[str, Box] = {}
        # Collect fields base-first so derived classes can override order;
        # all are zero-initialised before any constructor runs.
        for cls in reversed(superclass_chain(class_name, self._env)):
            info = self._env.classes[cls]
            for fname, fd in info.fields.items():
                fields[fname] = self._new_box(self._zero_value(fd.type))
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
                frame.define(param.name, self._new_box(self._coerce_value(arg, param.type)))

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
        mod = self._env.modifier_methods.get(class_name, {})
        if method in mod:
            return mod[method], class_name
        raise GlangRuntimeError(
            f"'{class_name}' has no method '{method}'", 0, 0
        )

    def _make_function_value(self, fn: FunctionDecl) -> Value:
        return Value(
            self._function_type(fn.params, fn.return_type),
            CallableValue(function=fn),
        )

    def _make_static_method_value(self, cls: str, method: MethodDecl) -> Value:
        return Value(
            self._function_type(method.params, method.return_type),
            CallableValue(method=method, defining_class=cls),
        )

    def _function_type(self, params, return_type: TypeNode) -> FunctionPointerType:
        return FunctionPointerType(
            param_types=[p.type for p in params],
            return_type=return_type,
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

    def _eval_index(self, expr: IndexExpr) -> Value:
        container = self._eval(expr.array)
        idx_value = self._eval(expr.index)

        overloaded = self._try_apply_index_operator(
            container, idx_value, expr.line, expr.col
        )
        if overloaded is not None:
            return overloaded

        idx = idx_value.raw

        if isinstance(container.raw, str):
            if idx < 0 or idx >= len(container.raw):
                raise GlangRuntimeError(
                    "string index out of bounds", expr.line, expr.col
                )
            return Value(NamedType("char"), container.raw[idx])

        return self._block_element(container, idx, expr.line, expr.col).value

    def _block_element(self, container: Value, idx: int, line: int, col: int) -> Box:
        """Resolve the element Box at `idx` for an array value or a pointer to a
        contiguous block allocated with `alloc(T, n)`."""
        elements = container.raw
        if isinstance(elements, Pointer):
            block = self._deref(container, line, col)
            elements = block.value.raw
        if not isinstance(elements, list):
            raise GlangRuntimeError(
                "cannot index a non-array value", line, col
            )
        if idx < 0 or idx >= len(elements):
            raise GlangRuntimeError(
                "array index out of bounds", line, col
            )
        return elements[idx]

    def _try_apply_binary_operator(
        self,
        op: str,
        left: Value,
        right: Value,
        line: int,
        col: int,
    ) -> Optional[Value]:
        if op not in _BINARY_OPERATOR_OVERLOADS:
            return None
        class_name = self._class_value_name(left)
        if class_name is None or not self._same_named_class(left, right):
            return None

        method_name = f"operator{op}"
        invert = False
        if not self._has_instance_method(class_name, method_name):
            if op != "!=" or not self._has_instance_method(class_name, "operator=="):
                return None
            method_name = "operator=="
            invert = True

        result = self._call_operator_method(left, method_name, [right], line, col)
        if invert:
            return Value(NamedType("bool"), not result.raw)
        return result

    def _try_apply_index_operator(
        self,
        container: Value,
        index: Value,
        line: int,
        col: int,
    ) -> Optional[Value]:
        class_name = self._class_value_name(container)
        if class_name is None or not self._has_instance_method(class_name, "operator[]"):
            return None
        return self._call_operator_method(container, "operator[]", [index], line, col)

    def _foreach_values(self, iterable: Value, line: int, col: int) -> Iterator[Value]:
        if isinstance(iterable.raw, str):
            for ch in iterable.raw:
                yield Value(NamedType("char"), ch)
            return

        if isinstance(iterable.type, ArrayType):
            if not isinstance(iterable.raw, list):
                raise GlangRuntimeError("foreach expected an array value", line, col)
            for box in iterable.raw:
                yield box.value
            return

        class_name = self._class_value_name(iterable)
        if class_name is not None or isinstance(iterable.raw, Pointer):
            length = self._call_instance_method(iterable, "length", [], line, col)
            for i in range(length.raw):
                yield self._call_instance_method(
                    iterable,
                    "get",
                    [Value(NamedType("int"), i)],
                    line,
                    col,
                )
            return

        raise GlangRuntimeError("foreach expected an iterable value", line, col)

    def _call_operator_method(
        self,
        receiver: Value,
        method_name: str,
        args: List[Value],
        line: int,
        col: int,
    ) -> Value:
        return self._call_instance_method(receiver, method_name, args, line, col)

    def _call_instance_method(
        self,
        receiver: Value,
        method_name: str,
        args: List[Value],
        line: int,
        col: int,
    ) -> Value:
        instance, this_val = self._receiver(receiver, line, col)
        method, defining = self._resolve_virtual(instance.class_name, method_name)
        return self._call_method(method, defining, this_val, args)

    def _class_value_name(self, value: Value) -> Optional[str]:
        if isinstance(value.type, NamedType) and self._env.is_class(value.type.name):
            return value.type.name
        return None

    def _same_named_class(self, left: Value, right: Value) -> bool:
        left_name = self._class_value_name(left)
        right_name = self._class_value_name(right)
        return left_name is not None and left_name == right_name

    def _has_instance_method(self, class_name: str, method_name: str) -> bool:
        info = self._env.classes.get(class_name)
        return bool(info and method_name in info.instance_methods)

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
            # Union no-field variant: Expr.Nil
            if (
                isinstance(expr.object, IdentifierExpr)
                and self._env.is_union(expr.object.name)
                and self._frame.lookup(expr.object.name) is None
            ):
                union_name = expr.object.name
                inst = VariantInstance(
                    union_name=union_name, variant_name=expr.field_name, fields={}
                )
                return self._new_box(Value(NamedType(union_name), inst))

            # Enum variant: Color.RED
            if (
                isinstance(expr.object, IdentifierExpr)
                and self._env.is_enum(expr.object.name)
                and self._frame.lookup(expr.object.name) is None
            ):
                enum_info = self._env.enums[expr.object.name]
                val = enum_info.variants[expr.field_name]
                return self._new_box(Value(NamedType(expr.object.name), val))

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
            return self._block_element(arr, idx, expr.line, expr.col)

        raise GlangRuntimeError(
            f"'{type(expr).__name__}' is not an lvalue", 0, 0
        )

    def _static_method_ref(self, expr: FieldAccessExpr) -> Optional[Value]:
        if not (
            isinstance(expr.object, IdentifierExpr)
            and self._env.is_class(expr.object.name)
            and self._frame.lookup(expr.object.name) is None
        ):
            return None

        cls = expr.object.name
        if self._has_static_field(cls, expr.field_name):
            return None
        method = self._env.classes[cls].static_methods.get(expr.field_name)
        if method is None:
            return None
        return self._make_static_method_value(cls, method)

    def _has_static_field(self, cls: str, name: str) -> bool:
        for c in superclass_chain(cls, self._env):
            if (c, name) in self._statics:
                return True
        return False

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
        box.value = self._coerce_value(value, box.value.type)

    def _coerce_value(self, value: Value, target_type: TypeNode) -> Value:
        if isinstance(value.type, NamedType) and value.type.name == "null":
            if isinstance(target_type, FunctionPointerType):
                return Value(target_type, None)
            if isinstance(target_type, PointerType):
                return Value(target_type, Pointer(None))
            if isinstance(target_type, ManagedHandleType):
                return Value(target_type, Pointer(None))
            if isinstance(target_type, NullableType):
                return Value(target_type, None)
        if isinstance(target_type, NullableType):
            return Value(target_type, value.raw)
        # A byte is always kept in 0..255; this also realises implicit
        # int-literal → byte coercion on every store / param bind / return.
        if isinstance(target_type, NamedType) and target_type.name == "byte":
            return Value(target_type, int(value.raw) & 0xFF)
        return Value(target_type, value.raw)

    def _is(self, value: Value, name: str) -> bool:
        return isinstance(value.type, NamedType) and value.type.name == name

    def _exception_instance(self, val: 'Value') -> 'Optional[ObjectInstance]':
        """Dereference an Exception pointer to get the ObjectInstance."""
        ptr = val.raw
        if isinstance(ptr, Pointer) and ptr.target is not None:
            inner = ptr.target.value.raw
            if isinstance(inner, ObjectInstance):
                return inner
        return None

    def _exception_class(self, val: 'Value') -> str:
        inst = self._exception_instance(val)
        return inst.class_name if inst is not None else "Exception"

    def _exception_message(self, val: 'Value') -> str:
        inst = self._exception_instance(val)
        if inst is not None:
            msg_box = inst.fields.get("message")
            if msg_box is not None:
                return str(msg_box.value.raw)
        return "(no message)"

    def _zero_value(self, t: TypeNode) -> Value:
        if isinstance(t, NullableType):
            return Value(t, None)
        if isinstance(t, FunctionPointerType):
            return Value(t, None)
        if isinstance(t, PointerType):
            return Value(t, Pointer(None))
        if isinstance(t, ManagedHandleType):
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
            if t.name == "byte":
                return Value(t, 0)
            if t.name == "string":
                return Value(t, "")
            if self._env.is_enum(t.name):
                return Value(t, 0)
            if self._env.is_union(t.name):
                info = self._env.unions[t.name]
                first_name, first_variant = next(iter(info.variants.items()))
                fields = {
                    fd.name: self._new_box(self._zero_value(fd.type))
                    for fd in first_variant.fields
                }
                return Value(t, VariantInstance(t.name, first_name, fields))
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
        text = self._value_to_string(value)
        self.output.append(text)
        if self._out is not None:
            self._out.write(text + "\n")

    def _do_print_err(self, value: Value) -> None:
        text = self._value_to_string(value)
        self.err_output.append(text)
        if self._err is not None:
            self._err.write(text + "\n")

    def _value_to_string(self, value: Value) -> str:
        if self._is(value, "bool"):
            return "true" if value.raw else "false"
        return str(value.raw)


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
