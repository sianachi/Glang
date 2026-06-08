from __future__ import annotations
from typing import Dict, List, Set

from parser.ast_nodes import (
    Program, FunctionDecl, ClassDecl, InterfaceDecl,
    MethodDecl, FieldDecl, StaticFieldDecl,
    NamedType, EnumDecl,
)
from errors.errors import TypeError
from analyser.symbol_table import (
    GlobalEnv, FunctionInfo, ClassInfo, InterfaceInfo, EnumInfo,
)


class Pass1Collector:
    def __init__(self, env: GlobalEnv) -> None:
        self._env = env

    def collect(self, program: Program) -> None:
        self._register_declarations(program)
        self._validate_inheritance()
        self._build_vtables()

    # ------------------------------------------------------------------
    # Phase 1: register all top-level names
    # ------------------------------------------------------------------

    def _register_declarations(self, program: Program) -> None:
        for decl in program.declarations:
            if isinstance(decl, FunctionDecl):
                self._register_function(decl)
            elif isinstance(decl, ClassDecl):
                self._register_class(decl)
            elif isinstance(decl, InterfaceDecl):
                self._register_interface(decl)
            elif isinstance(decl, EnumDecl):
                self._register_enum(decl)

    def _name_taken(self, name: str) -> bool:
        return (
            name in self._env.functions
            or name in self._env.classes
            or name in self._env.interfaces
            or name in self._env.enums
        )

    def _register_function(self, decl: FunctionDecl) -> None:
        if self._name_taken(decl.name):
            raise TypeError(
                f"name '{decl.name}' is already defined", decl.line, decl.col
            )
        self._env.resolve_type(decl.return_type)
        for p in decl.params:
            self._env.resolve_type(p.type)
        self._env.functions[decl.name] = FunctionInfo(
            name=decl.name,
            params=decl.params,
            return_type=decl.return_type,
            decl=decl,
        )

    def _register_class(self, decl: ClassDecl) -> None:
        if self._name_taken(decl.name):
            raise TypeError(
                f"name '{decl.name}' is already defined", decl.line, decl.col
            )

        fields: Dict[str, object] = {}
        for fd in decl.fields:
            self._env.resolve_type(fd.type)
            fields[fd.name] = fd.type

        static_fields: Dict[str, StaticFieldDecl] = {}
        for sfd in decl.static_fields:
            self._env.resolve_type(sfd.type)
            static_fields[sfd.name] = sfd

        instance_methods: Dict[str, MethodDecl] = {}
        static_methods: Dict[str, MethodDecl] = {}
        for md in decl.methods:
            self._env.resolve_type(md.return_type)
            for p in md.params:
                self._env.resolve_type(p.type)
            if md.is_static:
                static_methods[md.name] = md
            else:
                instance_methods[md.name] = md

        if decl.constructor:
            for p in decl.constructor.params:
                self._env.resolve_type(p.type)

        self._env.classes[decl.name] = ClassInfo(
            name=decl.name,
            fields=fields,
            static_fields=static_fields,
            instance_methods=instance_methods,
            static_methods=static_methods,
            vtable={},
            constructor=decl.constructor,
            destructor=decl.destructor,
            superclass=decl.superclass,
            interfaces=list(decl.interfaces),
            decl=decl,
        )

    def _register_interface(self, decl: InterfaceDecl) -> None:
        if self._name_taken(decl.name):
            raise TypeError(
                f"name '{decl.name}' is already defined", decl.line, decl.col
            )
        methods: Dict[str, MethodDecl] = {}
        for md in decl.methods:
            self._env.resolve_type(md.return_type)
            for p in md.params:
                self._env.resolve_type(p.type)
            methods[md.name] = md

        self._env.interfaces[decl.name] = InterfaceInfo(
            name=decl.name,
            methods=methods,
            decl=decl,
        )

    def _register_enum(self, decl: EnumDecl) -> None:
        if self._name_taken(decl.name):
            raise TypeError(
                f"name '{decl.name}' is already defined", decl.line, decl.col
            )
        variants: Dict[str, int] = {}
        next_val = 0
        for v in decl.variants:
            if v.name in variants:
                raise TypeError(
                    f"duplicate enum variant '{v.name}'", v.line, v.col
                )
            val = v.value if v.value is not None else next_val
            variants[v.name] = val
            next_val = val + 1
        self._env.enums[decl.name] = EnumInfo(
            name=decl.name, variants=variants, decl=decl
        )

    # ------------------------------------------------------------------
    # Phase 2: validate the inheritance graph
    # ------------------------------------------------------------------

    def _validate_inheritance(self) -> None:
        for info in self._env.classes.values():
            decl = info.decl

            if info.superclass is not None:
                if info.superclass in self._env.interfaces:
                    raise TypeError(
                        f"cannot extend interface '{info.superclass}'; use implements",
                        decl.line, decl.col,
                    )
                if info.superclass not in self._env.classes:
                    raise TypeError(
                        f"unknown class '{info.superclass}' in extends clause",
                        decl.line, decl.col,
                    )

            for iface in info.interfaces:
                if iface in self._env.classes:
                    raise TypeError(
                        f"cannot implement class '{iface}'; use extends",
                        decl.line, decl.col,
                    )
                if iface not in self._env.interfaces:
                    raise TypeError(
                        f"unknown interface '{iface}' in implements clause",
                        decl.line, decl.col,
                    )

        # Circular inheritance detection
        for class_name in self._env.classes:
            self._detect_cycle(class_name)

    def _detect_cycle(self, start: str) -> None:
        visited: List[str] = []
        current: str | None = start
        while current is not None:
            if current in visited:
                raise TypeError(
                    f"circular inheritance involving class '{current}'",
                    self._env.classes[start].decl.line,
                    self._env.classes[start].decl.col,
                )
            visited.append(current)
            info = self._env.classes.get(current)
            if info is None:
                break
            current = info.superclass

    # ------------------------------------------------------------------
    # Phase 3: build vtables in topological order
    # ------------------------------------------------------------------

    def _build_vtables(self) -> None:
        order = self._topological_order()
        for class_name in order:
            self._build_vtable_for(class_name)

        # Interface completeness check
        for info in self._env.classes.values():
            for iface_name in info.interfaces:
                iface = self._env.interfaces[iface_name]
                for method_name, iface_method in iface.methods.items():
                    impl = info.instance_methods.get(method_name)
                    if impl is None:
                        raise TypeError(
                            f"class '{info.name}' does not implement '{iface_name}.{method_name}'",
                            info.decl.line, info.decl.col,
                        )
                    if not self._signatures_match(impl, iface_method):
                        raise TypeError(
                            f"class '{info.name}' method '{method_name}' does not match interface signature",
                            impl.line, impl.col,
                        )

    def _topological_order(self) -> List[str]:
        result: List[str] = []
        visiting: Set[str] = set()
        visited: Set[str] = set()

        def visit(name: str) -> None:
            if name in visited:
                return
            visiting.add(name)
            info = self._env.classes.get(name)
            if info and info.superclass and info.superclass in self._env.classes:
                visit(info.superclass)
            visiting.discard(name)
            visited.add(name)
            result.append(name)

        for name in self._env.classes:
            visit(name)
        return result

    def _build_vtable_for(self, class_name: str) -> None:
        info = self._env.classes[class_name]
        vtable: Dict[str, MethodDecl] = {}

        if info.superclass:
            parent = self._env.classes[info.superclass]
            # Merge parent fields and instance methods into child
            merged_fields = {**parent.fields, **info.fields}
            merged_methods = {**parent.instance_methods, **info.instance_methods}
            info.fields = merged_fields
            info.instance_methods = merged_methods
            vtable = dict(parent.vtable)

        for name, method in info.instance_methods.items():
            vtable[name] = method

        if info.destructor is not None:
            vtable["~destructor"] = info.destructor
        else:
            vtable.setdefault("~destructor", None)

        info.vtable = vtable

    def _signatures_match(self, a: MethodDecl, b: MethodDecl) -> bool:
        from analyser.type_utils import types_equal
        if not types_equal(a.return_type, b.return_type):
            return False
        if len(a.params) != len(b.params):
            return False
        for pa, pb in zip(a.params, b.params):
            if not types_equal(pa.type, pb.type):
                return False
        return True
