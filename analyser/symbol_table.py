from __future__ import annotations
import sys
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, TYPE_CHECKING

from parser.ast_nodes import (
    TypeNode, Param, FunctionDecl, ClassDecl, InterfaceDecl,
    ConstructorDecl, DestructorDecl, MethodDecl, NamedType, FieldDecl,
)
from errors.errors import TypeError

if TYPE_CHECKING:
    from parser.ast_nodes import EnumDecl, UnionDecl


PRIMITIVES = {"int", "float", "bool", "char", "byte", "string", "void"}


@dataclass
class FunctionInfo:
    name: str
    params: List[Param]
    return_type: TypeNode
    decl: FunctionDecl


@dataclass
class ClassInfo:
    name: str
    fields: Dict[str, FieldDecl]
    static_fields: Dict[str, object]   # str → StaticFieldDecl
    instance_methods: Dict[str, MethodDecl]
    static_methods: Dict[str, MethodDecl]
    vtable: Dict[str, MethodDecl]
    constructor: Optional[ConstructorDecl]
    destructor: Optional[DestructorDecl]
    superclass: Optional[str]
    interfaces: List[str]
    decl: ClassDecl
    access: str = "public"


@dataclass
class InterfaceInfo:
    name: str
    methods: Dict[str, MethodDecl]
    decl: InterfaceDecl


@dataclass
class EnumInfo:
    name: str
    variants: Dict[str, int]
    decl: 'EnumDecl'


@dataclass
class UnionVariantInfo:
    name: str
    fields: List[FieldDecl]


@dataclass
class UnionInfo:
    name: str
    type_params: List[str]
    variants: Dict[str, UnionVariantInfo]  # variant_name → info
    decl: 'UnionDecl'


class SymbolTable:
    def __init__(self, parent: Optional[SymbolTable] = None) -> None:
        self._parent = parent
        self._symbols: Dict[str, tuple] = {}  # name → (TypeNode, line, col, is_const)

    def define(self, name: str, type: TypeNode, line: int, col: int,
               is_const: bool = False) -> None:
        if name in self._symbols:
            raise TypeError(f"name '{name}' is already defined", line, col)
        outer = self._find_outer(name)
        if outer is not None:
            outer_line = outer[1]
            print(
                f"warning: '{name}' shadows variable declared at line {outer_line}",
                file=sys.stderr,
            )
        self._symbols[name] = (type, line, col, is_const)

    def lookup(self, name: str) -> TypeNode:
        entry = self._find(name)
        if entry is None:
            raise TypeError(f"undefined variable '{name}'", 0, 0)
        return entry[0]

    def lookup_local(self, name: str) -> Optional[TypeNode]:
        entry = self._symbols.get(name)
        return entry[0] if entry is not None else None

    def find_scope(self, name: str) -> Optional[SymbolTable]:
        if name in self._symbols:
            return self
        if self._parent is not None:
            return self._parent.find_scope(name)
        return None

    def entry(self, name: str) -> Optional[tuple]:
        return self._symbols.get(name)

    def is_descendant_of(self, ancestor: SymbolTable) -> bool:
        current: Optional[SymbolTable] = self
        while current is not None:
            if current is ancestor:
                return True
            current = current._parent
        return False

    def is_const_var(self, name: str) -> bool:
        entry = self._find(name)
        return bool(entry and entry[3])

    def child(self) -> SymbolTable:
        return SymbolTable(parent=self)

    def _find(self, name: str) -> Optional[tuple]:
        if name in self._symbols:
            return self._symbols[name]
        if self._parent is not None:
            return self._parent._find(name)
        return None

    def _find_outer(self, name: str) -> Optional[tuple]:
        if self._parent is not None:
            return self._parent._find(name)
        return None


@dataclass
class GlobalEnv:
    functions: Dict[str, FunctionInfo] = field(default_factory=dict)
    classes: Dict[str, ClassInfo] = field(default_factory=dict)
    interfaces: Dict[str, InterfaceInfo] = field(default_factory=dict)
    enums: Dict[str, EnumInfo] = field(default_factory=dict)
    unions: Dict[str, UnionInfo] = field(default_factory=dict)
    modifier_methods: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    # target type name → {method name → MethodDecl}

    def resolve_type(self, node: TypeNode) -> None:
        from parser.ast_nodes import (
            PointerType, ArrayType, FunctionPointerType, GenericType, NullableType,
        )
        if isinstance(node, GenericType):
            # Monomorphization should have rewritten every GenericType already;
            # reaching one here means an instantiation site was missed.
            raise TypeError(
                f"unresolved generic type '{node.name}'", node.line, node.col
            )
        if isinstance(node, NamedType):
            if (
                node.name not in PRIMITIVES
                and node.name not in self.classes
                and node.name not in self.interfaces
                and node.name not in self.enums
                and node.name not in self.unions
                and node.name != "null"
            ):
                raise TypeError(
                    f"unknown type '{node.name}'", node.line, node.col
                )
        elif isinstance(node, PointerType):
            self.resolve_type(node.base)
        elif isinstance(node, ArrayType):
            self.resolve_type(node.base)
        elif isinstance(node, FunctionPointerType):
            for p in node.param_types:
                self.resolve_type(p)
            self.resolve_type(node.return_type)
        elif isinstance(node, NullableType):
            self.resolve_type(node.base)

    def is_class(self, name: str) -> bool:
        return name in self.classes

    def is_interface(self, name: str) -> bool:
        return name in self.interfaces

    def is_enum(self, name: str) -> bool:
        return name in self.enums

    def is_union(self, name: str) -> bool:
        return name in self.unions

    def is_primitive(self, name: str) -> bool:
        return name in PRIMITIVES
