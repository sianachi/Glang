"""compiler/ast_serializer.py — canonical type-string helper.

Historically this serialised a type-checked Program to the tagged-line text the
old AST→C transpiler consumed. That path is gone: the compiler (``glangc``, under
``Toolchain/``) emits C directly from the typed AST, so the serialiser is no longer
used. The one piece still needed is ``_type_str`` — the canonical no-space
type-string oracle used by the parser/symtab differential tests (it mirrors
``Toolchain/compiler/ast.lang``'s ``showType``).
"""
from __future__ import annotations
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from parser.ast_nodes import (
    TypeNode, NamedType, PointerType, ManagedHandleType, ArrayType, GenericType,
    NullableType, FunctionPointerType,
)


def _type_str(t: TypeNode) -> str:
    if isinstance(t, NamedType):
        return t.name
    if isinstance(t, PointerType):
        return _type_str(t.base) + '*'
    if isinstance(t, ManagedHandleType):
        return _type_str(t.base) + '@'
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
