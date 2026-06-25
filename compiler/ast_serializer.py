"""compiler/ast_serializer.py

Serialises a type-checked Glang Program to the indented tagged-line text
format consumed by compiler/transpiler.lang.

Format:
    <2*depth spaces><TAG> [<key>=<percent-encoded-value> ...]

Children of a node appear immediately after it at depth+1.
Percent-encoding: space→%20, =→%3D, newline→%0A, %→%25, \\r→%0D, \\t→%09.

Attribute naming (avoiding Python keywords):
    return_type  →  ret
    class_name   →  cls
    type         →  type   (OK: 'type' is a builtin, not a keyword)
    super        →  super  (OK: 'super' is a builtin, not a keyword)
"""
from __future__ import annotations
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from parser.ast_nodes import (
    Program, ImportDecl, FunctionDecl, ClassDecl, EnumDecl, UnionDecl,
    InterfaceDecl, ModifierDecl, NamespaceDecl, UsingDecl,
    FieldDecl, StaticFieldDecl, ConstructorDecl, DestructorDecl, MethodDecl,
    EnumVariant, UnionVariant, Param,
    Block, VarDecl, AssignStmt, IfStmt, WhileStmt, DoWhileStmt,
    ForStmt, ForeachStmt, UsingStmt, BreakStmt, ContinueStmt,
    ReturnStmt, ThrowStmt, TryCatchStmt, CatchClause, MatchStmt, MatchArm,
    VariantPattern, WildcardPattern,
    BinaryExpr, UnaryExpr, CastExpr, CallExpr, IndirectCallExpr, ClosureExpr,
    MethodCallExpr, NewExpr, DeleteExpr, AllocExpr, FreeExpr,
    FieldAccessExpr, ArrowAccessExpr, IndexExpr, AddressOfExpr, DerefExpr,
    IdentifierExpr, LiteralExpr, NullExpr, ThisExpr, SuperExpr,
    TypeNode, NamedType, PointerType, ArrayType, GenericType,
    NullableType, FunctionPointerType,
)
from analyser.symbol_table import GlobalEnv


def _encode(s: str) -> str:
    s = s.replace('%', '%25')
    s = s.replace('\n', '%0A')
    s = s.replace('\r', '%0D')
    s = s.replace('\t', '%09')
    s = s.replace(' ', '%20')
    s = s.replace('=', '%3D')
    # Percent-encode any remaining C0 control byte (in particular NUL, e.g. the
    # '\0' char literal).  The compiled runtime's strings are NUL-terminated and
    # line-oriented, so a raw control byte would truncate or corrupt the AST when
    # the transpiler reads it; the interpreter tolerates it but the two must agree.
    if any(ord(c) < 0x20 for c in s):
        s = ''.join(c if ord(c) >= 0x20 else f'%{ord(c):02X}' for c in s)
    return s


def _type_str(t: TypeNode) -> str:
    if isinstance(t, NamedType):
        return t.name
    if isinstance(t, PointerType):
        return _type_str(t.base) + '*'
    if isinstance(t, ArrayType):
        return _type_str(t.base) + '[' + str(t.size) + ']'
    if isinstance(t, NullableType):
        return _type_str(t.base) + '?'
    if isinstance(t, FunctionPointerType):
        params = ','.join(_type_str(p) for p in t.param_types)
        return 'fn(' + params + ')->' + _type_str(t.return_type)
    if isinstance(t, GenericType):
        args = ','.join(_type_str(a) for a in t.type_args)
        return t.name + '<' + args + '>'
    return 'void'


class AstSerializer:
    def __init__(self):
        self.lines: list[str] = []
        self.depth = 0

    def _emit(self, tag: str, **attrs):
        parts = [tag]
        for k, v in attrs.items():
            parts.append(f'{k}={_encode(str(v))}')
        self.lines.append('  ' * self.depth + ' '.join(parts))

    def _indent(self):
        self.depth += 1

    def _dedent(self):
        self.depth -= 1

    def serialize(self, program: Program, env: GlobalEnv) -> str:
        self._emit('PROGRAM')
        self._indent()
        for decl in program.declarations:
            self._ser_node(decl)
        self._dedent()
        return '\n'.join(self.lines) + '\n'

    def _ser_node(self, node):
        if node is None:
            return
        # ── Declarations ────────────────────────────────────────────────────
        if isinstance(node, FunctionDecl):
            self._ser_func(node)
        elif isinstance(node, ClassDecl):
            self._ser_class(node)
        elif isinstance(node, EnumDecl):
            self._ser_enum(node)
        elif isinstance(node, UnionDecl):
            self._ser_union(node)
        elif isinstance(node, InterfaceDecl):
            self._ser_interface(node)
        elif isinstance(node, ModifierDecl):
            self._ser_modifier(node)
        elif isinstance(node, (ImportDecl, UsingDecl, NamespaceDecl)):
            pass  # consumed before this stage
        # ── Statements ──────────────────────────────────────────────────────
        elif isinstance(node, Block):
            self._ser_block(node)
        elif isinstance(node, VarDecl):
            self._ser_vardecl(node)
        elif isinstance(node, AssignStmt):
            self._ser_assign(node)
        elif isinstance(node, IfStmt):
            self._ser_if(node)
        elif isinstance(node, WhileStmt):
            self._ser_while(node)
        elif isinstance(node, DoWhileStmt):
            self._ser_dowhile(node)
        elif isinstance(node, ForStmt):
            self._ser_for(node)
        elif isinstance(node, ForeachStmt):
            self._ser_foreach(node)
        elif isinstance(node, UsingStmt):
            self._ser_using_stmt(node)
        elif isinstance(node, BreakStmt):
            self._emit('BREAK')
        elif isinstance(node, ContinueStmt):
            self._emit('CONTINUE')
        elif isinstance(node, ReturnStmt):
            self._ser_return(node)
        elif isinstance(node, ThrowStmt):
            self._ser_throw(node)
        elif isinstance(node, TryCatchStmt):
            self._ser_try(node)
        elif isinstance(node, MatchStmt):
            self._ser_match(node)
        # ── Expressions (also appear as statements) ──────────────────────────
        elif isinstance(node, BinaryExpr):
            self._ser_binary(node)
        elif isinstance(node, UnaryExpr):
            self._ser_unary(node)
        elif isinstance(node, CastExpr):
            self._ser_cast(node)
        elif isinstance(node, CallExpr):
            self._ser_call(node)
        elif isinstance(node, IndirectCallExpr):
            self._ser_indirect_call(node)
        elif isinstance(node, ClosureExpr):
            self._ser_closure(node)
        elif isinstance(node, MethodCallExpr):
            self._ser_method_call(node)
        elif isinstance(node, NewExpr):
            self._ser_new(node)
        elif isinstance(node, DeleteExpr):
            self._ser_delete(node)
        elif isinstance(node, AllocExpr):
            self._ser_alloc(node)
        elif isinstance(node, FreeExpr):
            self._ser_free(node)
        elif isinstance(node, FieldAccessExpr):
            self._ser_field_access(node)
        elif isinstance(node, ArrowAccessExpr):
            self._ser_arrow_access(node)
        elif isinstance(node, IndexExpr):
            self._ser_index(node)
        elif isinstance(node, AddressOfExpr):
            self._ser_address_of(node)
        elif isinstance(node, DerefExpr):
            self._ser_deref(node)
        elif isinstance(node, IdentifierExpr):
            self._emit('IDENT', name=node.name)
        elif isinstance(node, LiteralExpr):
            self._emit('LIT', kind=node.kind, val=node.value)
        elif isinstance(node, NullExpr):
            self._emit('NULL')
        elif isinstance(node, ThisExpr):
            self._emit('THIS')
        elif isinstance(node, SuperExpr):
            self._emit('SUPER')
        else:
            self._emit('UNKNOWN', nodetype=type(node).__name__)

    # ── Declarations ────────────────────────────────────────────────────────

    def _ser_func(self, node: FunctionDecl):
        self._emit('FUNC', name=node.name, params=len(node.params),
                   ret=_type_str(node.return_type))
        self._indent()
        for p in node.params:
            self._ser_param(p)
        if node.body is not None:
            self._ser_block(node.body)
        self._dedent()

    def _ser_class(self, node: ClassDecl):
        ifaces = ','.join(node.interfaces) if node.interfaces else ''
        super_ = node.superclass or ''
        imethods = sum(1 for m in node.methods if not m.is_static)
        smethods = sum(1 for m in node.methods if m.is_static)
        self._emit('CLASS',
                   name=node.name,
                   super=super_,
                   ifaces=ifaces,
                   fields=len(node.fields),
                   sfields=len(node.static_fields),
                   imethods=imethods,
                   smethods=smethods,
                   has_ctor=('true' if node.constructor else 'false'),
                   has_dtor=('true' if node.destructor else 'false'),
                   access=node.access)
        self._indent()
        for f in node.fields:
            self._ser_field(f)
        for sf in node.static_fields:
            self._ser_sfield(sf)
        if node.constructor:
            self._ser_ctor(node.constructor)
        if node.destructor:
            self._ser_dtor(node.destructor)
        for m in node.methods:
            self._ser_method(m)
        self._dedent()

    def _ser_field(self, node: FieldDecl):
        self._emit('FIELD', name=node.name, type=_type_str(node.type),
                   const=('true' if node.is_const else 'false'),
                   access=node.access)

    def _ser_sfield(self, node: StaticFieldDecl):
        self._emit('SFIELD', name=node.name, type=_type_str(node.type),
                   const=('true' if node.is_const else 'false'),
                   access=node.access)
        self._indent()
        self._ser_node(node.initializer)
        self._dedent()

    def _ser_ctor(self, node: ConstructorDecl):
        super_count = len(node.super_args) if node.super_args else 0
        self._emit('CTOR', params=len(node.params),
                   has_super=('true' if node.super_args is not None else 'false'),
                   super_args=super_count)
        self._indent()
        for p in node.params:
            self._ser_param(p)
        if node.super_args:
            for arg in node.super_args:
                self._emit('SUPER_ARG')
                self._indent()
                self._ser_node(arg)
                self._dedent()
        self._ser_block(node.body)
        self._dedent()

    def _ser_dtor(self, node: DestructorDecl):
        self._emit('DTOR')
        self._indent()
        self._ser_block(node.body)
        self._dedent()

    def _ser_method(self, node: MethodDecl):
        self._emit('METHOD', name=node.name,
                   static=('true' if node.is_static else 'false'),
                   ret=_type_str(node.return_type),
                   params=len(node.params),
                   access=node.access)
        self._indent()
        for p in node.params:
            self._ser_param(p)
        if node.body is not None:
            self._ser_block(node.body)
        self._dedent()

    def _ser_param(self, node: Param):
        self._emit('PARAM', name=node.name, type=_type_str(node.type),
                   const=('true' if node.is_const else 'false'))

    def _ser_enum(self, node: EnumDecl):
        self._emit('ENUM', name=node.name, variants=len(node.variants))
        self._indent()
        next_val = 0
        for v in node.variants:
            val = v.value if v.value is not None else next_val
            next_val = val + 1
            self._emit('VARIANT', name=v.name, val=val)
        self._dedent()

    def _ser_union(self, node: UnionDecl):
        self._emit('UNION', name=node.name, variants=len(node.variants))
        self._indent()
        for v in node.variants:
            self._emit('UNION_VARIANT', name=v.name, fields=len(v.fields))
            self._indent()
            for f in v.fields:
                self._emit('UNION_FIELD', name=f.name, type=_type_str(f.type))
            self._dedent()
        self._dedent()

    def _ser_interface(self, node: InterfaceDecl):
        self._emit('INTERFACE', name=node.name, methods=len(node.methods))
        self._indent()
        for m in node.methods:
            self._emit('METHOD_SIG', name=m.name,
                       ret=_type_str(m.return_type),
                       params=len(m.params))
            self._indent()
            for p in m.params:
                self._ser_param(p)
            self._dedent()
        self._dedent()

    def _ser_modifier(self, node: ModifierDecl):
        self._emit('MODIFIER', target=_type_str(node.target),
                   methods=len(node.methods))
        self._indent()
        for m in node.methods:
            self._ser_method(m)
        self._dedent()

    # ── Statements ──────────────────────────────────────────────────────────

    def _ser_block(self, node: Block):
        self._emit('BLOCK')
        self._indent()
        for s in node.stmts:
            self._ser_node(s)
        self._dedent()

    def _ser_vardecl(self, node: VarDecl):
        self._emit('VARDECL', name=node.name, type=_type_str(node.type),
                   const=('true' if node.is_const else 'false'))
        self._indent()
        self._ser_node(node.initializer)
        self._dedent()

    def _ser_assign(self, node: AssignStmt):
        self._emit('ASSIGN', op=node.op)
        self._indent()
        self._ser_node(node.target)
        self._ser_node(node.value)
        self._dedent()

    def _ser_if(self, node: IfStmt):
        has_else = node.else_branch is not None
        else_is_if = has_else and isinstance(node.else_branch, IfStmt)
        self._emit('IF',
                   has_else=('true' if has_else else 'false'),
                   else_is_if=('true' if else_is_if else 'false'))
        self._indent()
        self._ser_node(node.condition)
        self._ser_block(node.then_branch)
        if has_else:
            if else_is_if:
                self._ser_if(node.else_branch)  # type: ignore
            else:
                self._ser_block(node.else_branch)  # type: ignore
        self._dedent()

    def _ser_while(self, node: WhileStmt):
        self._emit('WHILE')
        self._indent()
        self._ser_node(node.condition)
        self._ser_block(node.body)
        self._dedent()

    def _ser_dowhile(self, node: DoWhileStmt):
        self._emit('DOWHILE')
        self._indent()
        self._ser_block(node.body)
        self._ser_node(node.condition)
        self._dedent()

    def _ser_for(self, node: ForStmt):
        self._emit('FOR')
        self._indent()
        self._ser_vardecl(node.init)
        self._ser_node(node.condition)
        self._ser_node(node.post)
        self._ser_block(node.body)
        self._dedent()

    def _ser_foreach(self, node: ForeachStmt):
        self._emit('FOREACH', var=node.var_name,
                   type=_type_str(node.var_type),
                   const=('true' if node.is_const else 'false'))
        self._indent()
        self._ser_node(node.iterable)
        self._ser_block(node.body)
        self._dedent()

    def _ser_using_stmt(self, node: UsingStmt):
        self._emit('USING_STMT')
        self._indent()
        self._ser_vardecl(node.decl)
        self._ser_block(node.body)
        self._dedent()

    def _ser_return(self, node: ReturnStmt):
        self._emit('RETURN', has_val=('true' if node.value is not None else 'false'))
        if node.value is not None:
            self._indent()
            self._ser_node(node.value)
            self._dedent()

    def _ser_throw(self, node: ThrowStmt):
        self._emit('THROW')
        self._indent()
        self._ser_node(node.value)
        self._dedent()

    def _ser_try(self, node: TryCatchStmt):
        self._emit('TRY', catches=len(node.catches))
        self._indent()
        self._ser_block(node.body)
        for c in node.catches:
            self._emit('CATCH', type=_type_str(c.catch_type), var=c.var_name)
            self._indent()
            self._ser_block(c.body)
            self._dedent()
        self._dedent()

    def _ser_match(self, node: MatchStmt):
        self._emit('MATCH', arms=len(node.arms))
        self._indent()
        self._ser_node(node.scrutinee)
        for arm in node.arms:
            if isinstance(arm.pattern, WildcardPattern):
                self._emit('ARM', is_wild='true', union='', variant='', bindings=0)
                self._indent()
                self._ser_block(arm.body)
                self._dedent()
            else:
                p = arm.pattern
                self._emit('ARM', is_wild='false',
                           union=p.union_name, variant=p.variant_name,
                           bindings=len(p.bindings))
                self._indent()
                for b in p.bindings:
                    self._emit('BIND', name=b)
                self._ser_block(arm.body)
                self._dedent()
        self._dedent()

    # ── Expressions ─────────────────────────────────────────────────────────

    def _ser_binary(self, node: BinaryExpr):
        self._emit('BINARY', op=node.op)
        self._indent()
        self._ser_node(node.left)
        self._ser_node(node.right)
        self._dedent()

    def _ser_unary(self, node: UnaryExpr):
        self._emit('UNARY', op=node.op)
        self._indent()
        self._ser_node(node.operand)
        self._dedent()

    def _ser_cast(self, node: CastExpr):
        self._emit('CAST', to=_type_str(node.target_type))
        self._indent()
        self._ser_node(node.expr)
        self._dedent()

    def _ser_call(self, node: CallExpr):
        self._emit('CALL', name=node.name, args=len(node.args))
        self._indent()
        for a in node.args:
            self._ser_node(a)
        self._dedent()

    def _ser_indirect_call(self, node: IndirectCallExpr):
        self._emit('INDIRECT_CALL', args=len(node.args))
        self._indent()
        self._ser_node(node.callee)
        for a in node.args:
            self._ser_node(a)
        self._dedent()

    def _ser_closure(self, node: ClosureExpr):
        self._emit('CLOSURE', params=len(node.params),
                   ret=_type_str(node.return_type),
                   captures=len(node.captures))
        self._indent()
        for p in node.params:
            self._ser_param(p)
        for c in node.captures:
            self._emit('BIND', name=c)
        self._ser_block(node.body)
        self._dedent()

    def _ser_method_call(self, node: MethodCallExpr):
        self._emit('METHOD_CALL', method=node.method,
                   args=len(node.args),
                   arrow=('true' if node.is_arrow else 'false'))
        self._indent()
        self._ser_node(node.object)
        for a in node.args:
            self._ser_node(a)
        self._dedent()

    def _ser_new(self, node: NewExpr):
        self._emit('NEW', cls=node.class_name, args=len(node.args))
        self._indent()
        for a in node.args:
            self._ser_node(a)
        self._dedent()

    def _ser_delete(self, node: DeleteExpr):
        self._emit('DELETE')
        self._indent()
        self._ser_node(node.operand)
        self._dedent()

    def _ser_alloc(self, node: AllocExpr):
        self._emit('ALLOC', type=_type_str(node.type),
                   has_count=('true' if node.count is not None else 'false'))
        if node.count is not None:
            self._indent()
            self._ser_node(node.count)
            self._dedent()

    def _ser_free(self, node: FreeExpr):
        self._emit('FREE')
        self._indent()
        self._ser_node(node.operand)
        self._dedent()

    def _ser_field_access(self, node: FieldAccessExpr):
        self._emit('FIELD_ACCESS', field=node.field_name)
        self._indent()
        self._ser_node(node.object)
        self._dedent()

    def _ser_arrow_access(self, node: ArrowAccessExpr):
        self._emit('ARROW_ACCESS', field=node.field_name)
        self._indent()
        self._ser_node(node.pointer)
        self._dedent()

    def _ser_index(self, node: IndexExpr):
        self._emit('INDEX')
        self._indent()
        self._ser_node(node.array)
        self._ser_node(node.index)
        self._dedent()

    def _ser_address_of(self, node: AddressOfExpr):
        self._emit('ADDRESS_OF')
        self._indent()
        self._ser_node(node.operand)
        self._dedent()

    def _ser_deref(self, node: DerefExpr):
        self._emit('DEREF')
        self._indent()
        self._ser_node(node.operand)
        self._dedent()


def serialize(program: Program, env: GlobalEnv) -> str:
    """Serialise a fully-analysed Glang program to the transpiler text format."""
    return AstSerializer().serialize(program, env)
