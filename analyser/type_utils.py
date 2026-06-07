from __future__ import annotations
from typing import List, TYPE_CHECKING

from parser.ast_nodes import (
    TypeNode, NamedType, PointerType, ArrayType, Expr,
    IdentifierExpr, FieldAccessExpr, ArrowAccessExpr, DerefExpr, IndexExpr,
)
from errors.errors import TypeError

if TYPE_CHECKING:
    from analyser.symbol_table import GlobalEnv


PRIMITIVES = {"int", "float", "bool", "char", "string", "void"}
NULL_TYPE = NamedType("null")


def types_equal(a: TypeNode, b: TypeNode) -> bool:
    if type(a) is not type(b):
        return False
    if isinstance(a, NamedType):
        return a.name == b.name
    if isinstance(a, PointerType):
        return types_equal(a.base, b.base)
    if isinstance(a, ArrayType):
        return a.size == b.size and types_equal(a.base, b.base)
    return False


def is_assignable(from_type: TypeNode, to_type: TypeNode, env: GlobalEnv) -> bool:
    if types_equal(from_type, to_type):
        return True

    # null → any pointer
    if isinstance(from_type, NamedType) and from_type.name == "null":
        if isinstance(to_type, PointerType):
            return True

    # Subclass pointer covariance
    if isinstance(from_type, PointerType) and isinstance(to_type, PointerType):
        fb = from_type.base
        tb = to_type.base
        if isinstance(fb, NamedType) and isinstance(tb, NamedType):
            if env.is_class(fb.name) and env.is_class(tb.name):
                chain = superclass_chain(fb.name, env)
                if tb.name in chain[1:]:
                    return True
            if env.is_class(fb.name) and env.is_interface(tb.name):
                if implements_interface(fb.name, tb.name, env):
                    return True

    return False


def is_numeric(t: TypeNode) -> bool:
    return isinstance(t, NamedType) and t.name in ("int", "float")


def is_integer(t: TypeNode) -> bool:
    return isinstance(t, NamedType) and t.name == "int"


def is_bool(t: TypeNode) -> bool:
    return isinstance(t, NamedType) and t.name == "bool"


def is_string(t: TypeNode) -> bool:
    return isinstance(t, NamedType) and t.name == "string"


def is_pointer(t: TypeNode) -> bool:
    return isinstance(t, PointerType)


def is_array(t: TypeNode) -> bool:
    return isinstance(t, ArrayType)


def pointer_base(t: PointerType) -> TypeNode:
    return t.base


def type_str(t: TypeNode) -> str:
    if isinstance(t, NamedType):
        return t.name
    if isinstance(t, PointerType):
        return type_str(t.base) + "*"
    if isinstance(t, ArrayType):
        return f"{type_str(t.base)}[{t.size}]"
    return "?"


def is_lvalue(expr: Expr) -> bool:
    return isinstance(
        expr,
        (IdentifierExpr, FieldAccessExpr, ArrowAccessExpr, DerefExpr, IndexExpr),
    )


def binary_result_type(op: str, left: TypeNode, right: TypeNode) -> TypeNode:
    l_int = is_integer(left)
    r_int = is_integer(right)
    l_float = isinstance(left, NamedType) and left.name == "float"
    r_float = isinstance(right, NamedType) and right.name == "float"
    l_str = is_string(left)
    r_str = is_string(right)
    l_bool = is_bool(left)
    r_bool = is_bool(right)

    if op in ("+", "-", "*", "/"):
        if l_int and r_int:
            return NamedType("int")
        if l_float and r_float:
            return NamedType("float")
        if op == "+" and l_str and r_str:
            return NamedType("string")
        ls = type_str(left)
        rs = type_str(right)
        if ls == rs:
            raise TypeError(
                f"operator '{op}' requires int or float operands", 0, 0
            )
        raise TypeError(
            f"operator '{op}': type mismatch '{ls}' and '{rs}'", 0, 0
        )

    if op == "%":
        if l_int and r_int:
            return NamedType("int")
        raise TypeError("operator '%' requires int operands", 0, 0)

    if op in ("<", ">", "<=", ">="):
        if (l_int and r_int) or (l_float and r_float):
            return NamedType("bool")
        ls, rs = type_str(left), type_str(right)
        raise TypeError(
            f"operator '{op}': type mismatch '{ls}' and '{rs}'", 0, 0
        )

    if op in ("==", "!="):
        if types_equal(left, right):
            return NamedType("bool")
        # null vs pointer
        null_name = isinstance(left, NamedType) and left.name == "null"
        null_name2 = isinstance(right, NamedType) and right.name == "null"
        if (null_name and is_pointer(right)) or (null_name2 and is_pointer(left)):
            return NamedType("bool")
        ls, rs = type_str(left), type_str(right)
        raise TypeError(
            f"operator '{op}': type mismatch '{ls}' and '{rs}'", 0, 0
        )

    if op in ("&&", "||"):
        if l_bool and r_bool:
            return NamedType("bool")
        bad = type_str(left) if not l_bool else type_str(right)
        raise TypeError(
            f"operator '{op}' requires bool, got '{bad}'", 0, 0
        )

    if op in ("&", "|", "^", "<<", ">>"):
        if l_int and r_int:
            return NamedType("int")
        raise TypeError(f"operator '{op}' requires int operands", 0, 0)

    raise TypeError(f"unknown operator '{op}'", 0, 0)


def unary_result_type(op: str, operand: TypeNode) -> TypeNode:
    if op == "!":
        if not is_bool(operand):
            raise TypeError(
                f"operator '!' requires bool, got '{type_str(operand)}'", 0, 0
            )
        return NamedType("bool")
    if op == "~":
        if not is_integer(operand):
            raise TypeError("operator '~' requires int operands", 0, 0)
        return NamedType("int")
    if op in ("++", "--"):
        if not is_integer(operand):
            raise TypeError(
                f"operator '{op}' requires int operands", 0, 0
            )
        return NamedType("int")
    if op in ("-", "unary-"):
        if is_integer(operand):
            return NamedType("int")
        if isinstance(operand, NamedType) and operand.name == "float":
            return NamedType("float")
        raise TypeError(
            f"operator '-' requires int or float, got '{type_str(operand)}'", 0, 0
        )
    if op == "unary+":
        if is_integer(operand):
            return NamedType("int")
        if isinstance(operand, NamedType) and operand.name == "float":
            return NamedType("float")
        raise TypeError(
            f"operator '+' requires int or float, got '{type_str(operand)}'", 0, 0
        )
    raise TypeError(f"unknown unary operator '{op}'", 0, 0)


def superclass_chain(class_name: str, env: GlobalEnv) -> List[str]:
    chain: List[str] = []
    current = class_name
    while current is not None:
        if current in chain:
            break
        chain.append(current)
        info = env.classes.get(current)
        if info is None:
            break
        current = info.superclass
    return chain


def implements_interface(class_name: str, iface_name: str, env: GlobalEnv) -> bool:
    for cls in superclass_chain(class_name, env):
        info = env.classes.get(cls)
        if info is None:
            break
        if iface_name in info.interfaces:
            return True
    return False
