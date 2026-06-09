import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from lexer.lexer import Lexer
from parser.parser import Parser
from parser.ast_nodes import (
    NamedType, PointerType, ArrayType, FunctionPointerType,
    Block, ReturnStmt, IfStmt,
    WhileStmt, ForStmt, VarDecl, IdentifierExpr, LiteralExpr,
    BinaryExpr, FieldAccessExpr, ArrowAccessExpr, DerefExpr, IndexExpr,
)
from errors.errors import TypeError as GTE
from analyser.analyser import Analyser
from analyser.symbol_table import SymbolTable, GlobalEnv, FunctionInfo, ClassInfo, InterfaceInfo
from analyser.type_utils import (
    types_equal, is_assignable, is_lvalue, type_str,
    binary_result_type, unary_result_type,
    superclass_chain, implements_interface,
    is_numeric, is_integer, is_bool, is_string, is_pointer, is_array,
    NULL_TYPE,
)
from analyser.return_checker import always_returns


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def analyse(src: str) -> GlobalEnv:
    tokens = Lexer(src).tokenize()
    prog = Parser(tokens).parse()
    return Analyser().analyse(prog)


def ok(src: str) -> None:
    analyse(src)


def err(src: str, fragment: str) -> None:
    with pytest.raises(GTE) as exc_info:
        analyse(src)
    assert fragment in exc_info.value.msg, (
        f"expected {fragment!r} in {exc_info.value.msg!r}"
    )


def named(n: str) -> NamedType:
    return NamedType(n)


def ptr(t: NamedType) -> PointerType:
    return PointerType(t)


# ---------------------------------------------------------------------------
# TestTypeUtils — pure helpers
# ---------------------------------------------------------------------------

class TestTypesEqual:
    def test_same_primitive(self):
        assert types_equal(named("int"), named("int"))

    def test_different_primitives(self):
        assert not types_equal(named("int"), named("float"))

    def test_pointer_equal(self):
        assert types_equal(ptr(named("int")), ptr(named("int")))

    def test_pointer_base_differs(self):
        assert not types_equal(ptr(named("int")), ptr(named("float")))

    def test_pointer_vs_named(self):
        assert not types_equal(ptr(named("int")), named("int"))

    def test_array_equal(self):
        assert types_equal(ArrayType(named("int"), 5), ArrayType(named("int"), 5))

    def test_array_size_differs(self):
        assert not types_equal(ArrayType(named("int"), 5), ArrayType(named("int"), 10))

    def test_array_base_differs(self):
        assert not types_equal(ArrayType(named("int"), 5), ArrayType(named("float"), 5))

    def test_function_pointer_equal(self):
        a = FunctionPointerType([named("int")], named("bool"))
        b = FunctionPointerType([named("int")], named("bool"))
        assert types_equal(a, b)

    def test_function_pointer_param_differs(self):
        a = FunctionPointerType([named("int")], named("bool"))
        b = FunctionPointerType([named("float")], named("bool"))
        assert not types_equal(a, b)

    def test_null_type_equal(self):
        assert types_equal(NULL_TYPE, NamedType("null"))

    def test_null_vs_int(self):
        assert not types_equal(NULL_TYPE, named("int"))


class TestIsAssignable:
    def _env(self) -> GlobalEnv:
        return GlobalEnv()

    def test_same_type(self):
        assert is_assignable(named("int"), named("int"), self._env())

    def test_different_primitives(self):
        assert not is_assignable(named("int"), named("float"), self._env())

    def test_null_to_pointer(self):
        assert is_assignable(NULL_TYPE, ptr(named("int")), self._env())

    def test_null_to_function_pointer(self):
        fn_t = FunctionPointerType([named("int")], named("int"))
        assert is_assignable(NULL_TYPE, fn_t, self._env())

    def test_null_to_named(self):
        assert not is_assignable(NULL_TYPE, named("int"), self._env())

    def test_subclass_pointer(self):
        env = GlobalEnv()
        # Build minimal class hierarchy: Dog extends Animal
        env.classes["Animal"] = ClassInfo(
            name="Animal", fields={}, static_fields={},
            instance_methods={}, static_methods={}, vtable={},
            constructor=None, destructor=None,
            superclass=None, interfaces=[], decl=None,
        )
        env.classes["Dog"] = ClassInfo(
            name="Dog", fields={}, static_fields={},
            instance_methods={}, static_methods={}, vtable={},
            constructor=None, destructor=None,
            superclass="Animal", interfaces=[], decl=None,
        )
        assert is_assignable(ptr(named("Dog")), ptr(named("Animal")), env)
        assert not is_assignable(ptr(named("Animal")), ptr(named("Dog")), env)

    def test_implements_interface(self):
        env = GlobalEnv()
        env.interfaces["Printable"] = InterfaceInfo(name="Printable", methods={}, decl=None)
        env.classes["Dog"] = ClassInfo(
            name="Dog", fields={}, static_fields={},
            instance_methods={}, static_methods={}, vtable={},
            constructor=None, destructor=None,
            superclass=None, interfaces=["Printable"], decl=None,
        )
        assert is_assignable(ptr(named("Dog")), ptr(named("Printable")), env)
        assert not is_assignable(ptr(named("Printable")), ptr(named("Dog")), env)

    def test_pointer_to_pointer_no_relation(self):
        env = GlobalEnv()
        env.classes["Cat"] = ClassInfo(
            name="Cat", fields={}, static_fields={},
            instance_methods={}, static_methods={}, vtable={},
            constructor=None, destructor=None,
            superclass=None, interfaces=[], decl=None,
        )
        env.classes["Dog"] = ClassInfo(
            name="Dog", fields={}, static_fields={},
            instance_methods={}, static_methods={}, vtable={},
            constructor=None, destructor=None,
            superclass=None, interfaces=[], decl=None,
        )
        assert not is_assignable(ptr(named("Dog")), ptr(named("Cat")), env)


class TestTypeStr:
    def test_primitive(self):
        assert type_str(named("int")) == "int"

    def test_pointer(self):
        assert type_str(ptr(named("int"))) == "int*"

    def test_double_pointer(self):
        assert type_str(PointerType(ptr(named("Dog")))) == "Dog**"

    def test_array(self):
        assert type_str(ArrayType(named("char"), 10)) == "char[10]"


class TestIsLvalue:
    def test_identifier_is_lvalue(self):
        assert is_lvalue(IdentifierExpr("x"))

    def test_field_access_is_lvalue(self):
        assert is_lvalue(FieldAccessExpr(IdentifierExpr("o"), "f"))

    def test_arrow_access_is_lvalue(self):
        assert is_lvalue(ArrowAccessExpr(IdentifierExpr("p"), "f"))

    def test_deref_is_lvalue(self):
        assert is_lvalue(DerefExpr(IdentifierExpr("p")))

    def test_index_is_lvalue(self):
        assert is_lvalue(IndexExpr(IdentifierExpr("a"), LiteralExpr("int", "0")))

    def test_literal_is_not_lvalue(self):
        assert not is_lvalue(LiteralExpr("int", "5"))

    def test_binary_is_not_lvalue(self):
        assert not is_lvalue(BinaryExpr(IdentifierExpr("a"), "+", IdentifierExpr("b")))


class TestBinaryResultType:
    def test_int_add(self):
        assert types_equal(binary_result_type("+", named("int"), named("int")), named("int"))

    def test_float_mul(self):
        assert types_equal(binary_result_type("*", named("float"), named("float")), named("float"))

    def test_string_concat(self):
        assert types_equal(binary_result_type("+", named("string"), named("string")), named("string"))

    def test_int_mod(self):
        assert types_equal(binary_result_type("%", named("int"), named("int")), named("int"))

    def test_comparison_returns_bool(self):
        for op in ("<", ">", "<=", ">="):
            assert types_equal(binary_result_type(op, named("int"), named("int")), named("bool"))

    def test_equality_same_type(self):
        assert types_equal(binary_result_type("==", named("int"), named("int")), named("bool"))

    def test_equality_null_pointer(self):
        assert types_equal(binary_result_type("==", NULL_TYPE, ptr(named("int"))), named("bool"))
        assert types_equal(binary_result_type("!=", ptr(named("int")), NULL_TYPE), named("bool"))

    def test_logical_and(self):
        assert types_equal(binary_result_type("&&", named("bool"), named("bool")), named("bool"))

    def test_bitwise_ops(self):
        for op in ("&", "|", "^", "<<", ">>"):
            assert types_equal(binary_result_type(op, named("int"), named("int")), named("int"))

    def test_byte_arithmetic_returns_byte(self):
        for op in ("+", "-", "*", "/", "%"):
            assert types_equal(
                binary_result_type(op, named("byte"), named("byte")), named("byte")
            )

    def test_byte_bitwise_returns_byte(self):
        for op in ("&", "|", "^", "<<", ">>"):
            assert types_equal(
                binary_result_type(op, named("byte"), named("byte")), named("byte")
            )

    def test_byte_comparison_returns_bool(self):
        for op in ("<", ">", "<=", ">="):
            assert types_equal(
                binary_result_type(op, named("byte"), named("byte")), named("bool")
            )

    def test_byte_int_mismatch_raises(self):
        with pytest.raises(GTE):
            binary_result_type("+", named("byte"), named("int"))

    def test_int_float_mismatch_raises(self):
        with pytest.raises(GTE):
            binary_result_type("+", named("int"), named("float"))

    def test_bool_as_int_raises(self):
        with pytest.raises(GTE):
            binary_result_type("+", named("bool"), named("int"))

    def test_logical_on_int_raises(self):
        with pytest.raises(GTE):
            binary_result_type("&&", named("int"), named("int"))

    def test_mod_float_raises(self):
        with pytest.raises(GTE):
            binary_result_type("%", named("float"), named("float"))

    def test_comparison_cross_type_raises(self):
        with pytest.raises(GTE):
            binary_result_type("<", named("int"), named("float"))


class TestUnaryResultType:
    def test_not_bool(self):
        assert types_equal(unary_result_type("!", named("bool")), named("bool"))

    def test_not_int_raises(self):
        with pytest.raises(GTE):
            unary_result_type("!", named("int"))

    def test_bitwise_not_int(self):
        assert types_equal(unary_result_type("~", named("int")), named("int"))

    def test_bitwise_not_bool_raises(self):
        with pytest.raises(GTE):
            unary_result_type("~", named("bool"))

    def test_increment_int(self):
        assert types_equal(unary_result_type("++", named("int")), named("int"))

    def test_increment_float_raises(self):
        with pytest.raises(GTE):
            unary_result_type("++", named("float"))

    def test_negate_int(self):
        assert types_equal(unary_result_type("-", named("int")), named("int"))

    def test_negate_float(self):
        assert types_equal(unary_result_type("-", named("float")), named("float"))

    def test_negate_bool_raises(self):
        with pytest.raises(GTE):
            unary_result_type("-", named("bool"))


class TestSuperclassChain:
    def _env(self):
        env = GlobalEnv()
        env.classes["Animal"] = ClassInfo(
            name="Animal", fields={}, static_fields={},
            instance_methods={}, static_methods={}, vtable={},
            constructor=None, destructor=None,
            superclass=None, interfaces=[], decl=None,
        )
        env.classes["Dog"] = ClassInfo(
            name="Dog", fields={}, static_fields={},
            instance_methods={}, static_methods={}, vtable={},
            constructor=None, destructor=None,
            superclass="Animal", interfaces=[], decl=None,
        )
        env.classes["Poodle"] = ClassInfo(
            name="Poodle", fields={}, static_fields={},
            instance_methods={}, static_methods={}, vtable={},
            constructor=None, destructor=None,
            superclass="Dog", interfaces=[], decl=None,
        )
        return env

    def test_root_class(self):
        assert superclass_chain("Animal", self._env()) == ["Animal"]

    def test_one_level(self):
        assert superclass_chain("Dog", self._env()) == ["Dog", "Animal"]

    def test_two_levels(self):
        assert superclass_chain("Poodle", self._env()) == ["Poodle", "Dog", "Animal"]


class TestImplementsInterface:
    def _env(self):
        env = GlobalEnv()
        env.interfaces["Printable"] = InterfaceInfo(name="Printable", methods={}, decl=None)
        env.interfaces["Serializable"] = InterfaceInfo(name="Serializable", methods={}, decl=None)
        env.classes["Base"] = ClassInfo(
            name="Base", fields={}, static_fields={},
            instance_methods={}, static_methods={}, vtable={},
            constructor=None, destructor=None,
            superclass=None, interfaces=["Printable"], decl=None,
        )
        env.classes["Child"] = ClassInfo(
            name="Child", fields={}, static_fields={},
            instance_methods={}, static_methods={}, vtable={},
            constructor=None, destructor=None,
            superclass="Base", interfaces=[], decl=None,
        )
        return env

    def test_direct_implementation(self):
        assert implements_interface("Base", "Printable", self._env())

    def test_inherited_implementation(self):
        assert implements_interface("Child", "Printable", self._env())

    def test_not_implemented(self):
        assert not implements_interface("Base", "Serializable", self._env())

    def test_not_inherited_when_parent_lacks(self):
        assert not implements_interface("Child", "Serializable", self._env())


# ---------------------------------------------------------------------------
# TestSymbolTable
# ---------------------------------------------------------------------------

class TestSymbolTable:
    def test_define_and_lookup(self):
        st = SymbolTable()
        st.define("x", named("int"), 1, 1)
        assert types_equal(st.lookup("x"), named("int"))

    def test_lookup_missing_raises(self):
        st = SymbolTable()
        with pytest.raises(GTE) as exc:
            st.lookup("x")
        assert "undefined variable 'x'" in exc.value.msg

    def test_redeclaration_in_same_scope_raises(self):
        st = SymbolTable()
        st.define("x", named("int"), 1, 1)
        with pytest.raises(GTE) as exc:
            st.define("x", named("float"), 2, 1)
        assert "already defined" in exc.value.msg

    def test_child_scope_sees_parent(self):
        parent = SymbolTable()
        parent.define("x", named("int"), 1, 1)
        child = parent.child()
        assert types_equal(child.lookup("x"), named("int"))

    def test_child_scope_can_shadow(self, capsys):
        parent = SymbolTable()
        parent.define("x", named("int"), 1, 1)
        child = parent.child()
        child.define("x", named("float"), 2, 1)
        assert types_equal(child.lookup("x"), named("float"))
        captured = capsys.readouterr()
        assert "shadows" in captured.err

    def test_sibling_scopes_independent(self):
        parent = SymbolTable()
        a = parent.child()
        b = parent.child()
        a.define("x", named("int"), 1, 1)
        with pytest.raises(GTE):
            b.lookup("x")

    def test_lookup_local_present(self):
        st = SymbolTable()
        st.define("x", named("int"), 1, 1)
        assert types_equal(st.lookup_local("x"), named("int"))

    def test_lookup_local_absent_returns_none(self):
        st = SymbolTable()
        assert st.lookup_local("x") is None

    def test_lookup_local_does_not_search_parent(self):
        parent = SymbolTable()
        parent.define("x", named("int"), 1, 1)
        child = parent.child()
        assert child.lookup_local("x") is None


# ---------------------------------------------------------------------------
# TestGlobalEnv — resolve_type
# ---------------------------------------------------------------------------

class TestGlobalEnv:
    def test_primitive_types_valid(self):
        env = GlobalEnv()
        for prim in ("int", "float", "bool", "char", "byte", "string", "void"):
            env.resolve_type(named(prim))  # must not raise

    def test_unknown_type_raises(self):
        env = GlobalEnv()
        with pytest.raises(GTE) as exc:
            env.resolve_type(named("Foo"))
        assert "unknown type 'Foo'" in exc.value.msg

    def test_known_class_valid(self):
        env = GlobalEnv()
        env.classes["Dog"] = ClassInfo(
            name="Dog", fields={}, static_fields={},
            instance_methods={}, static_methods={}, vtable={},
            constructor=None, destructor=None,
            superclass=None, interfaces=[], decl=None,
        )
        env.resolve_type(named("Dog"))  # must not raise

    def test_known_interface_valid(self):
        env = GlobalEnv()
        env.interfaces["Printable"] = InterfaceInfo(name="Printable", methods={}, decl=None)
        env.resolve_type(named("Printable"))

    def test_pointer_to_unknown_raises(self):
        env = GlobalEnv()
        with pytest.raises(GTE):
            env.resolve_type(ptr(named("Unknown")))

    def test_array_of_unknown_raises(self):
        env = GlobalEnv()
        with pytest.raises(GTE):
            env.resolve_type(ArrayType(named("Unknown"), 5))

    def test_pointer_to_known_valid(self):
        env = GlobalEnv()
        env.resolve_type(ptr(named("int")))


# ---------------------------------------------------------------------------
# TestReturnChecker
# ---------------------------------------------------------------------------

def _return() -> ReturnStmt:
    return ReturnStmt()


def _if_else(then_returns: bool, else_returns: bool) -> IfStmt:
    then_block = Block([_return()] if then_returns else [])
    else_block = Block([_return()] if else_returns else [])
    return IfStmt(
        condition=LiteralExpr("bool", "true"),
        then_branch=then_block,
        else_branch=else_block,
    )


def _if_no_else() -> IfStmt:
    return IfStmt(
        condition=LiteralExpr("bool", "true"),
        then_branch=Block([_return()]),
        else_branch=None,
    )


class TestReturnChecker:
    def test_empty_list(self):
        assert not always_returns([])

    def test_return_stmt(self):
        assert always_returns([_return()])

    def test_if_else_both_return(self):
        assert always_returns([_if_else(True, True)])

    def test_if_else_only_then_returns(self):
        assert not always_returns([_if_else(True, False)])

    def test_if_else_only_else_returns(self):
        assert not always_returns([_if_else(False, True)])

    def test_if_else_neither_returns(self):
        assert not always_returns([_if_else(False, False)])

    def test_if_without_else_no_guarantee(self):
        assert not always_returns([_if_no_else()])

    def test_while_no_guarantee(self):
        assert not always_returns([WhileStmt(LiteralExpr("bool", "true"), Block([_return()]))])

    def test_block_that_returns(self):
        assert always_returns([Block([_return()])])

    def test_block_that_does_not_return(self):
        assert not always_returns([Block([])])

    def test_unreachable_after_return(self):
        # Return followed by if — the if is unreachable but always_returns should
        # see True as soon as it hits the return stmt
        assert always_returns([_return(), _if_no_else()])

    def test_stmt_before_return_does_not_block(self):
        nop = Block([])
        assert always_returns([nop, _return()])

    def test_nested_if_else_chain(self):
        inner = _if_else(True, True)
        outer = IfStmt(
            condition=LiteralExpr("bool", "true"),
            then_branch=Block([inner]),
            else_branch=Block([_return()]),
        )
        assert always_returns([outer])

    def test_if_else_if_else_all_return(self):
        else_if = IfStmt(
            condition=LiteralExpr("bool", "true"),
            then_branch=Block([_return()]),
            else_branch=Block([_return()]),
        )
        outer = IfStmt(
            condition=LiteralExpr("bool", "true"),
            then_branch=Block([_return()]),
            else_branch=else_if,
        )
        assert always_returns([outer])

    def test_if_else_if_missing_final_else(self):
        else_if = IfStmt(
            condition=LiteralExpr("bool", "true"),
            then_branch=Block([_return()]),
            else_branch=None,
        )
        outer = IfStmt(
            condition=LiteralExpr("bool", "true"),
            then_branch=Block([_return()]),
            else_branch=else_if,
        )
        assert not always_returns([outer])


# ---------------------------------------------------------------------------
# TestPass1 — top-level registration
# ---------------------------------------------------------------------------

class TestPass1Functions:
    def test_registers_function(self):
        env = analyse("int add(int a, int b) { return a + b; }")
        assert "add" in env.functions
        info = env.functions["add"]
        assert info.name == "add"
        assert len(info.params) == 2
        assert types_equal(info.return_type, named("int"))

    def test_duplicate_function_raises(self):
        err(
            "int f() { return 1; } int f() { return 2; }",
            "already defined",
        )

    def test_function_with_unknown_param_type_raises(self):
        err("int f(Foo x) { return 1; }", "unknown type 'Foo'")

    def test_function_with_unknown_return_type_raises(self):
        err("Foo f() { return 1; }", "unknown type 'Foo'")


class TestPass1Classes:
    def test_registers_class(self):
        env = analyse("class Dog {} void main() {}")
        assert "Dog" in env.classes

    def test_duplicate_class_raises(self):
        err("class Dog {} class Dog {} void main() {}", "already defined")

    def test_function_and_class_same_name_raises(self):
        err("int Dog() { return 1; } class Dog {} void main() {}", "already defined")

    def test_class_with_unknown_field_type_raises(self):
        err("class Dog { Foo x; } void main() {}", "unknown type 'Foo'")

    def test_self_pointer_field_ok(self):
        ok("class Node { int value; Node* next; } void main() {}")

    def test_self_type_in_method_signature_ok(self):
        ok("class Node { void link(Node* next) {} } void main() {}")

    def test_mutually_referential_pointer_fields_ok(self):
        ok("class A { B* b; } class B { A* a; } void main() {}")

    def test_direct_self_field_raises(self):
        err(
            "class Node { Node child; } void main() {}",
            "direct class field cycle",
        )

    def test_mutual_direct_class_fields_raise(self):
        err(
            "class A { B b; } class B { A a; } void main() {}",
            "direct class field cycle",
        )

    def test_extends_unknown_class_raises(self):
        err("class Dog extends Animal {} void main() {}", "unknown class 'Animal'")

    def test_extends_interface_raises(self):
        err(
            "interface Printable { string toString(); } "
            "class Dog extends Printable {} void main() {}",
            "cannot extend interface",
        )

    def test_implements_unknown_interface_raises(self):
        err("class Dog implements Printable {} void main() {}", "unknown interface 'Printable'")

    def test_implements_class_raises(self):
        err(
            "class Animal {} class Dog implements Animal {} void main() {}",
            "cannot implement class",
        )

    def test_circular_inheritance_raises(self):
        err(
            "class A extends B {} class B extends A {} void main() {}",
            "circular inheritance",
        )

    def test_three_class_cycle_raises(self):
        err(
            "class A extends B {} class B extends C {} class C extends A {} void main() {}",
            "circular inheritance",
        )


class TestPass1Interfaces:
    def test_registers_interface(self):
        env = analyse("interface Printable { string toString(); } void main() {}")
        assert "Printable" in env.interfaces
        assert "toString" in env.interfaces["Printable"].methods

    def test_duplicate_interface_raises(self):
        err(
            "interface I { void f(); } interface I { void f(); } void main() {}",
            "already defined",
        )

    def test_interface_method_unknown_type_raises(self):
        err("interface I { Foo f(); } void main() {}", "unknown type 'Foo'")


class TestPass1Vtables:
    def test_inherited_fields_merged(self):
        src = """
        class Animal {
            string name;
            Animal(string n) { this.name = n; }
        }
        class Dog extends Animal {
            int age;
            Dog(string n, int a) : super(n) { this.age = a; }
        }
        void main() {}
        """
        env = analyse(src)
        dog = env.classes["Dog"]
        assert "name" in dog.fields
        assert "age" in dog.fields

    def test_inherited_methods_merged(self):
        src = """
        class Animal {
            string name;
            Animal(string n) { this.name = n; }
            string speak() { return this.name; }
        }
        class Dog extends Animal {
            Dog(string n) : super(n) {}
        }
        void main() {}
        """
        env = analyse(src)
        dog = env.classes["Dog"]
        assert "speak" in dog.instance_methods

    def test_override_in_vtable(self):
        src = """
        class Animal {
            string name;
            Animal(string n) { this.name = n; }
            string speak() { return this.name; }
        }
        class Dog extends Animal {
            Dog(string n) : super(n) {}
            string speak() { return this.name; }
        }
        void main() {}
        """
        env = analyse(src)
        assert env.classes["Dog"].vtable["speak"] is env.classes["Dog"].instance_methods["speak"]

    def test_interface_completeness_ok(self):
        src = """
        interface Printable { string toString(); }
        class Dog implements Printable {
            string name;
            Dog(string n) { this.name = n; }
            string toString() { return this.name; }
        }
        void main() {}
        """
        ok(src)

    def test_interface_method_missing_raises(self):
        err(
            """
            interface Printable { string toString(); }
            class Dog implements Printable { void main() {} }
            void main() {}
            """,
            "does not implement",
        )

    def test_interface_method_wrong_return_type_raises(self):
        err(
            """
            interface Printable { string toString(); }
            class Dog implements Printable {
                int toString() { return 1; }
            }
            void main() {}
            """,
            "does not match interface signature",
        )

    def test_interface_method_wrong_params_raises(self):
        err(
            """
            interface I { int f(int x); }
            class C implements I {
                int f(string x) { return 1; }
            }
            void main() {}
            """,
            "does not match interface signature",
        )

    def test_inherited_method_satisfies_interface(self):
        src = """
        interface Printable { string toString(); }
        class Animal {
            string name;
            Animal(string n) { this.name = n; }
            string toString() { return this.name; }
        }
        class Dog extends Animal implements Printable {
            Dog(string n) : super(n) {}
        }
        void main() {}
        """
        ok(src)


# ---------------------------------------------------------------------------
# TestPass2Functions
# ---------------------------------------------------------------------------

class TestPass2Functions:
    def test_simple_function_ok(self):
        ok("int add(int a, int b) { return a + b; }")

    def test_void_function_ok(self):
        ok("void noop() {}")

    def test_missing_return_raises(self):
        err("int f() { int x = 1; }", "not all code paths return a value")

    def test_void_returns_value_raises(self):
        err("void f() { return 1; }", "void function must not return a value")

    def test_non_void_empty_return_raises(self):
        err("int f() { return; }", "non-void function must return a value")

    def test_return_wrong_type_raises(self):
        err("int f() { return true; }", "cannot assign")

    def test_if_else_both_return_ok(self):
        ok("int f(bool b) { if (b) { return 1; } else { return 2; } }")

    def test_if_without_else_not_enough_raises(self):
        err("int f(bool b) { if (b) { return 1; } }", "not all code paths return a value")

    def test_params_in_scope(self):
        ok("int f(int x) { return x; }")

    def test_param_type_mismatch_on_call_raises(self):
        err(
            "int f(int x) { return x; } int main() { return f(true); }",
            "cannot assign",
        )

    def test_wrong_arg_count_raises(self):
        err(
            "int add(int a, int b) { return a+b; } int main() { return add(1); }",
            "expects 2 arguments, got 1",
        )

    def test_too_many_args_raises(self):
        err(
            "int f(int x) { return x; } int main() { return f(1, 2); }",
            "expects 1 arguments, got 2",
        )

    def test_undefined_function_raises(self):
        err("int f() { return foo(); }", "undefined function 'foo'")

    def test_recursive_function_ok(self):
        ok("int fib(int n) { if (n <= 1) { return n; } else { return fib(n - 1) + fib(n - 2); } }")


class TestPass2FunctionPointersAndClosures:
    def test_free_function_reference_ok(self):
        ok(
            "int add(int a, int b) { return a + b; } "
            "void main() { fn(int, int) -> int op = add; int x = op(1, 2); }"
        )

    def test_static_method_reference_ok(self):
        ok(
            "class C { static int inc(int x) { return x + 1; } } "
            "void main() { fn(int) -> int f = C.inc; int x = f(1); }"
        )

    def test_null_assignment_and_comparison_ok(self):
        ok("void main() { fn(int) -> int f = null; if (f == null) {} }")

    def test_function_pointer_signature_mismatch_raises(self):
        err(
            "int add(int a, int b) { return a + b; } "
            "void main() { fn(int) -> int op = add; }",
            "cannot initialise",
        )

    def test_non_callable_variable_call_raises(self):
        err("void main() { int x = 1; x(); }", "'x' is not callable")

    def test_instance_method_reference_raises(self):
        err(
            "class C { int m() { return 1; } } "
            "void main() { C c = C(); fn() -> int f = c.m; }",
            "has no field 'm'",
        )

    def test_closure_capture_ok(self):
        ok(
            "void main() { int threshold = 10; "
            "fn(int) -> bool check = (int x) -> bool { return x > threshold; }; }"
        )

    def test_recursive_closure_unsupported(self):
        err(
            "void main() { fn(int) -> int f = "
            "(int x) -> int { return f(x); }; }",
            "undefined function 'f'",
        )


# ---------------------------------------------------------------------------
# TestPass2Statements
# ---------------------------------------------------------------------------

class TestPass2VarDecl:
    def test_var_decl_ok(self):
        ok("void f() { int x = 5; }")

    def test_var_decl_type_mismatch_raises(self):
        err("void f() { int x = true; }", "cannot initialise 'int'")

    def test_var_decl_unknown_type_raises(self):
        err("void f() { Foo x = 1; }", "unknown type 'Foo'")

    def test_var_decl_null_to_pointer_ok(self):
        ok("void f() { int* p = null; }")

    def test_var_redeclaration_raises(self):
        err("void f() { int x = 1; int x = 2; }", "already defined")

    def test_var_use_before_decl_raises(self):
        err("int f() { return x; }", "undefined variable 'x'")

    def test_var_out_of_scope_raises(self):
        err(
            "int f() { if (true) { int x = 1; } return x; }",
            "undefined variable 'x'",
        )


class TestPass2AssignStmt:
    def test_assign_ok(self):
        ok("void f() { int x = 0; x = 5; }")

    def test_assign_type_mismatch_raises(self):
        err("void f() { int x = 0; x = true; }", "cannot assign")

    def test_assign_to_literal_raises(self):
        err("void f() { 5 = 3; }", "not assignable")

    def test_compound_assign_ok(self):
        ok("void f() { int x = 0; x += 1; }")

    def test_compound_assign_type_mismatch_raises(self):
        err("void f() { int x = 0; x += true; }", "type mismatch")


class TestPass2ControlFlow:
    def test_if_bool_ok(self):
        ok("void f(bool b) { if (b) {} }")

    def test_if_int_condition_raises(self):
        err("void f() { if (1) {} }", "condition must be bool")

    def test_if_else_ok(self):
        ok("void f(bool b) { if (b) {} else {} }")

    def test_while_bool_ok(self):
        ok("void f(bool b) { while (b) {} }")

    def test_while_int_condition_raises(self):
        err("void f() { while (1) {} }", "condition must be bool")

    def test_for_ok(self):
        ok("void f() { for (int i = 0; i < 10; i += 1) {} }")

    def test_for_non_bool_condition_raises(self):
        err("void f() { for (int i = 0; i; i += 1) {} }", "condition must be bool")

    def test_break_in_loop_ok(self):
        ok("void f() { while (true) { break; } }")

    def test_break_outside_loop_raises(self):
        err("void f() { break; }", "'break' outside a loop")

    def test_continue_in_loop_ok(self):
        ok("void f() { while (true) { continue; } }")

    def test_continue_outside_loop_raises(self):
        err("void f() { continue; }", "'continue' outside a loop")

    def test_break_in_nested_loop_ok(self):
        ok("void f() { while (true) { while (true) { break; } break; } }")

    def test_for_var_scoped_to_loop(self):
        err(
            "int f() { for (int i = 0; i < 10; i += 1) {} return i; }",
            "undefined variable 'i'",
        )


# ---------------------------------------------------------------------------
# TestPass2Expressions
# ---------------------------------------------------------------------------

class TestPass2Literals:
    def test_int_literal(self):
        ok("int f() { return 42; }")

    def test_float_literal(self):
        ok("float f() { return 3.14; }")

    def test_bool_literal(self):
        ok("bool f() { return true; }")

    def test_char_literal(self):
        ok("char f() { return 'a'; }")

    def test_string_literal(self):
        ok('string f() { return "hi"; }')

    def test_null_to_pointer(self):
        ok("void f() { int* p = null; }")


class TestPass2Arithmetic:
    def test_int_add(self):
        ok("int f() { return 1 + 2; }")

    def test_int_sub(self):
        ok("int f() { return 5 - 3; }")

    def test_float_mul(self):
        ok("float f() { return 2.0 * 3.0; }")

    def test_int_mod(self):
        ok("int f() { return 7 % 3; }")

    def test_mixed_int_float_raises(self):
        err("float f() { return 1 + 2.0; }", "type mismatch")

    def test_string_concat(self):
        ok('string f() { return "a" + "b"; }')

    def test_bitwise_and(self):
        ok("int f() { return 5 & 3; }")

    def test_shift(self):
        ok("int f() { return 1 << 3; }")

    def test_comparison(self):
        ok("bool f() { return 1 < 2; }")

    def test_logical_and(self):
        ok("bool f() { return true && false; }")

    def test_logical_or(self):
        ok("bool f() { return true || false; }")

    def test_equality(self):
        ok("bool f() { return 1 == 1; }")

    def test_equality_type_mismatch_raises(self):
        err("bool f() { return 1 == true; }", "type mismatch")


class TestPass2StringOperations:
    def test_string_index_returns_char(self):
        ok('char f() { string s = "hello"; return s[1]; }')

    def test_string_index_requires_int(self):
        err(
            'char f() { string s = "hello"; return s[true]; }',
            "string index must be int",
        )

    def test_string_index_not_assignable(self):
        err(
            'void f() { string s = "hi"; s[0] = \'H\'; }',
            "string index is not assignable",
        )

    def test_len_string_ok(self):
        ok('int f() { return len("hello"); }')

    def test_len_array_ok(self):
        ok("class Buf { int[3] data; Buf() {} } int f() { Buf b = Buf(); return len(b.data); }")

    def test_len_wrong_type_raises(self):
        err("int f() { return len(42); }", "'len' requires string or array")

    def test_string_builtins_ok(self):
        ok(
            'int f() { int i = parseInt("42"); float x = parseFloat("3.5"); '
            'string s = substr("hello", 1, 3); string t = toString(i); '
            'bool a = startsWith("hello", "he"); bool b = endsWith("hello", "lo"); '
            'bool c = contains("hello", "ell"); return indexOf("hello", "ll"); }'
        )

    def test_substr_wrong_arg_type_raises(self):
        err('string f() { return substr("hello", true, 3); }', "cannot assign")

    def test_to_string_wrong_arg_type_raises(self):
        err("string f() { int* p = null; return toString(p); }", "'toString' requires a primitive")

    def test_file_io_builtins_ok(self):
        ok(
            'int f() { writeFile("a.txt", "x"); '
            'bool e = fileExists("a.txt"); '
            'string s = readFile("a.txt"); return len(s); }'
        )

    def test_write_file_wrong_arg_type_raises(self):
        err('void f() { writeFile("a.txt", 42); }', "cannot assign")


class TestPass2OperatorOverloading:
    VEC2 = """
    class Vec2 {
        int x;
        int y;
        Vec2(int x, int y) { this.x = x; this.y = y; }
        Vec2 operator+(Vec2 other) {
            return Vec2(this.x + other.x, this.y + other.y);
        }
        bool operator==(Vec2 other) {
            return this.x == other.x && this.y == other.y;
        }
        int operator[](int index) {
            if (index == 0) { return this.x; }
            return this.y;
        }
    }
    """

    def test_binary_operator_overload_ok(self):
        ok(self.VEC2 + "int f() { Vec2 a = Vec2(1, 2); Vec2 b = Vec2(3, 4); Vec2 c = a + b; return c.x; }")

    def test_equality_and_inequality_fallback_ok(self):
        ok(self.VEC2 + "bool f() { Vec2 a = Vec2(1, 2); Vec2 b = Vec2(1, 2); return a == b && !(a != b); }")

    def test_index_operator_overload_ok(self):
        ok(self.VEC2 + "int f() { Vec2 a = Vec2(7, 9); return a[1]; }")

    def test_missing_binary_operator_raises(self):
        err(
            "class Vec2 {} int f() { Vec2 a = Vec2(); Vec2 b = Vec2(); return a + b; }",
            "operator '+' requires int or float operands",
        )

    def test_static_operator_rejected(self):
        err(
            "class Vec2 { static Vec2 operator+(Vec2 other) { return other; } } void main() {}",
            "operator overloads must be instance methods",
        )

    def test_binary_operator_param_must_match_class(self):
        err(
            "class Vec2 { Vec2 operator+(int other) { return Vec2(); } } void main() {}",
            "'operator+' parameter must be 'Vec2'",
        )

    def test_comparison_operator_must_return_bool(self):
        err(
            "class Vec2 { int operator==(Vec2 other) { return 1; } } void main() {}",
            "'operator==' must return bool",
        )

    def test_index_operator_result_not_assignable(self):
        err(
            "class Box { int operator[](int i) { return i; } } void f() { Box b = Box(); b[0] = 1; }",
            "operator[] result is not assignable",
        )

    def test_index_operator_arg_type_checked(self):
        err(
            "class Box { int operator[](string key) { return 1; } } int f() { Box b = Box(); return b[0]; }",
            "cannot assign 'int' to 'string'",
        )


class TestPass2Unary:
    def test_negate_int(self):
        ok("int f() { return -1; }")

    def test_not_bool(self):
        ok("bool f() { return !true; }")

    def test_not_int_raises(self):
        err("bool f() { return !1; }", "requires bool")

    def test_increment(self):
        ok("void f() { int x = 0; ++x; }")

    def test_increment_literal_raises(self):
        err("void f() { ++1; }", "must be an lvalue")

    def test_bitwise_not(self):
        ok("int f() { return ~5; }")


class TestPass2Pointers:
    def test_address_of(self):
        ok("void f() { int x = 0; int* p = &x; }")

    def test_address_of_literal_raises(self):
        err("void f() { int* p = &5; }", "must be an lvalue")

    def test_deref_pointer(self):
        ok("int f() { int x = 0; int* p = &x; return *p; }")

    def test_deref_non_pointer_raises(self):
        err("int f() { int x = 5; return *x; }", "'*' requires a pointer")

    def test_null_pointer_assignable(self):
        ok("void f() { int* p = null; }")


class TestPass2Cast:
    def test_int_to_float(self):
        ok("float f() { return (float) 1; }")

    def test_float_to_int(self):
        ok("int f() { return (int) 3.14; }")

    def test_int_to_char(self):
        ok("char f() { return (char) 65; }")

    def test_char_to_int(self):
        ok("int f() { return (int) 'a'; }")

    def test_pointer_to_void_ptr(self):
        ok("void f() { int x = 0; int* p = &x; }")

    def test_invalid_cast_raises(self):
        err("int f() { return (int) true; }", "invalid cast")

    def test_string_to_int_raises(self):
        err('int f() { return (int) "hi"; }', "invalid cast")


class TestPass2Byte:
    def test_byte_var_and_arithmetic(self):
        ok("void main() { byte a = 1; byte b = 2; byte c = a + b; }")

    def test_byte_bitwise_with_literal(self):
        ok("void main() { byte a = 200; byte m = a & 0x0F; byte s = a << 1; }")

    def test_byte_literal_in_range(self):
        ok("void main() { byte b = 255; byte z = 0; }")

    def test_byte_literal_out_of_range_raises(self):
        err("void main() { byte b = 300; }", "byte literal out of range")

    def test_negative_into_byte_requires_cast(self):
        # -1 is a unary expression, not a byte literal, so it needs a cast.
        err("void main() { byte b = -1; }", "cannot initialise 'byte'")

    def test_int_var_to_byte_requires_cast(self):
        err("void main() { int i = 5; byte b = i; }", "cannot initialise 'byte'")

    def test_byte_int_mixing_requires_cast(self):
        err("void main() { byte b = 5; int i = 3; byte c = b + i; }", "type mismatch")

    def test_byte_int_casts(self):
        ok("void main() { byte b = 5; int i = (int) b; byte c = (byte) i; }")

    def test_byte_char_casts(self):
        ok("void main() { byte b = 65; char c = (char) b; byte d = (byte) c; }")

    def test_byte_to_float_cast_raises(self):
        err("void main() { byte b = 5; float f = (float) b; }", "invalid cast")

    def test_byte_to_bool_cast_raises(self):
        err("void main() { byte b = 5; bool x = (bool) b; }", "invalid cast")

    def test_byte_array_and_alloc(self):
        ok("void main() { byte* p = alloc(byte, 4); p[0] = 0xFF; free(p); }")

    def test_byte_compound_assign_with_literal(self):
        ok("void main() { byte b = 5; b += 10; b <<= 1; }")

    def test_bytes_from_string_returns_byte_ptr(self):
        ok('void main() { byte* p = bytesFromString("hi"); free(p); }')

    def test_string_from_bytes(self):
        ok('void main() { byte* p = bytesFromString("hi"); '
           'string s = stringFromBytes(p, 2); free(p); }')


class TestPass2Memory:
    def test_new_expr(self):
        # Stack-allocate via constructor call; heap via new passed to function
        ok("""
        class Dog { string name; Dog(string n) { this.name = n; } }
        void take(Dog* d) { delete d; }
        void main() { take(new Dog("Rex")); }
        """)

    def test_new_unknown_class_raises(self):
        err("void main() { new Cat(); }", "unknown class 'Cat'")

    def test_delete_non_pointer_raises(self):
        err("void main() { int x = 0; delete x; }", "'delete' requires a pointer")

    def test_delete_primitive_pointer_raises(self):
        err("void main() { int x = 0; int* p = &x; delete p; }", "'delete' requires a pointer to a class")

    def test_alloc_primitive(self):
        ok("void main() { int* p = alloc(int); free(p); }")

    def test_alloc_void_raises(self):
        err("void main() { alloc(void); }", "cannot alloc void")

    def test_free_non_pointer_raises(self):
        err("void main() { int x = 0; free(x); }", "'free' requires a pointer")

    def test_alloc_block(self):
        ok("void main() { int* p = alloc(int, 8); p[0] = 1; free(p); }")

    def test_alloc_count_must_be_int(self):
        err("void main() { int* p = alloc(int, 1.5); free(p); }",
            "alloc count must be int")

    def test_pointer_index_yields_element_type(self):
        ok("void main() { int* p = alloc(int, 4); int x = p[2]; free(p); }")

    def test_pointer_index_must_be_int(self):
        err("void main() { int* p = alloc(int, 4); int x = p[\"a\"]; free(p); }",
            "pointer index must be int")


# ---------------------------------------------------------------------------
# TestPass2Classes
# ---------------------------------------------------------------------------

class TestPass2ClassBodies:
    def test_static_field_initializer_ok(self):
        ok("class C { static int count = 0; } void main() {}")

    def test_static_field_wrong_type_raises(self):
        err(
            "class C { static int count = true; } void main() {}",
            "cannot initialise 'int'",
        )

    def test_constructor_ok(self):
        ok("class Dog { string name; Dog(string n) { this.name = n; } } void main() {}")

    def test_constructor_super_required_raises(self):
        err(
            """
            class Animal { Animal(string n) {} }
            class Dog extends Animal { Dog(string n) {} }
            void main() {}
            """,
            "subclass constructor must call super",
        )

    def test_constructor_super_no_parent_raises(self):
        err(
            "class Dog { Dog(string n) : super(n) {} } void main() {}",
            "super() used in a class with no superclass",
        )

    def test_constructor_super_wrong_arg_count_raises(self):
        err(
            """
            class Animal { Animal(string n) {} }
            class Dog extends Animal { Dog(string n) : super(n, n) {} }
            void main() {}
            """,
            "super(...) expects 1 arguments, got 2",
        )

    def test_method_return_type_ok(self):
        ok("""
        class Dog {
            string name;
            Dog(string n) { this.name = n; }
            string speak() { return this.name; }
        }
        void main() {}
        """)

    def test_method_missing_return_raises(self):
        err(
            "class C { int f() { int x = 1; } } void main() {}",
            "not all code paths return a value",
        )

    def test_method_return_wrong_type_raises(self):
        err(
            "class C { int f() { return true; } } void main() {}",
            "cannot assign",
        )

    def test_instance_method_accesses_this_ok(self):
        ok("""
        class Dog { string name; Dog(string n) { this.name = n; } string get() { return this.name; } }
        void main() {}
        """)

    def test_this_in_instance_method(self):
        ok("""
        class C {
            int x;
            C(int v) { this.x = v; }
            int getX() { return this.x; }
        }
        void main() {}
        """)

    def test_destructor_ok(self):
        ok("""
        class C {
            int x;
            C(int v) { this.x = v; }
            ~C() { this.x = 0; }
        }
        void main() {}
        """)


class TestPass2ThisSuper:
    def test_this_is_pointer_to_class(self):
        # this->field access through a method call
        ok("""
        class Dog {
            string name;
            Dog(string n) { this.name = n; }
            string get() { return this.name; }
        }
        void main() {}
        """)

    def test_super_without_parent_raises(self):
        err(
            "class Dog { Dog() {} void f() { super; } } void main() {}",
            "'super' used in a class with no superclass",
        )

    def test_this_in_static_method_raises(self):
        err(
            "class C { static int f() { return this; } } void main() {}",
            "'this' is not available in a static method",
        )


class TestPass2FieldAccess:
    def test_dot_field_access_ok(self):
        ok("""
        class Dog { string name; Dog(string n) { this.name = n; } }
        void main() {
            Dog d = Dog("Rex");
            string s = d.name;
        }
        """)

    def test_arrow_field_access_ok(self):
        ok("""
        class Dog { string name; Dog(string n) { this.name = n; } }
        void access(Dog* d) { string s = d->name; }
        void main() {}
        """)

    def test_unknown_field_dot_raises(self):
        err(
            """
            class Dog { string name; Dog(string n) { this.name = n; } }
            void main() { Dog d = Dog("Rex"); string s = d.age; }
            """,
            "has no field 'age'",
        )

    def test_arrow_on_non_pointer_raises(self):
        err(
            """
            class Dog { string name; Dog(string n) { this.name = n; } }
            void f(Dog d) { string s = d->name; }
            void main() {}
            """,
            "'->' requires a pointer",
        )


class TestPass2MethodCall:
    def test_dot_method_call_ok(self):
        ok("""
        class Dog { string name; Dog(string n) { this.name = n; } string speak() { return this.name; } }
        void main() { Dog d = Dog("Rex"); string s = d.speak(); }
        """)

    def test_arrow_method_call_ok(self):
        ok("""
        class Dog { string name; Dog(string n) { this.name = n; } string speak() { return this.name; } }
        void call(Dog* d) { string s = d->speak(); }
        void main() {}
        """)

    def test_unknown_method_raises(self):
        err(
            """
            class Dog { string name; Dog(string n) { this.name = n; } }
            void main() { Dog d = Dog("Rex"); d.fly(); }
            """,
            "has no method 'fly'",
        )

    def test_method_wrong_arg_count_raises(self):
        err(
            """
            class Dog { Dog() {} void bark(int times) {} }
            void main() { Dog d = Dog(); d.bark(); }
            """,
            "expects 1 arguments, got 0",
        )


class TestPass2ThisMethodCall:
    def test_this_method_call_ok(self):
        ok("""
        class Dog {
            string name;
            Dog(string n) { this.name = n; }
            string get() { return this.name; }
            string greet() { return this.get(); }
        }
        void main() {}
        """)

    def test_this_method_chain_ok(self):
        ok("""
        class C {
            int x;
            C(int v) { this.x = v; }
            int double_x() { return this.x + this.x; }
            int quad() { return this.double_x() + this.double_x(); }
        }
        void main() {}
        """)

    def test_super_method_call_ok(self):
        ok("""
        class Animal {
            string name;
            Animal(string n) { this.name = n; }
            string speak() { return this.name; }
        }
        class Dog extends Animal {
            Dog(string n) : super(n) {}
            string greet() { return this.speak(); }
        }
        void main() {}
        """)


class TestPass2StaticAccess:
    def test_static_field_read_ok(self):
        ok("class Counter { static int count = 0; } void main() { int x = Counter.count; }")

    def test_static_field_assign_ok(self):
        ok("class Counter { static int count = 0; } void main() { Counter.count = 1; }")

    def test_static_method_call_ok(self):
        ok("""
        class Counter {
            static int count = 0;
            static int getCount() { return Counter.count; }
        }
        void main() { int x = Counter.getCount(); }
        """)

    def test_static_method_wrong_arg_count_raises(self):
        err(
            """
            class C { static int f(int x) { return x; } }
            void main() { int x = C.f(); }
            """,
            "expects 1 arguments, got 0",
        )

    def test_static_field_unknown_raises(self):
        err(
            "class C { static int count = 0; } void main() { int x = C.missing; }",
            "has no field 'missing'",
        )

    def test_static_method_unknown_raises(self):
        err(
            "class C { } void main() { C.missing(); }",
            "has no method 'missing'",
        )

    def test_static_method_in_static_body_ok(self):
        ok("""
        class Counter {
            static int count = 0;
            static int getCount() { return Counter.count; }
            static void increment() { Counter.count = Counter.count + 1; }
        }
        void main() {}
        """)


class TestPass2Subtyping:
    def test_subclass_pointer_assignable(self):
        ok("""
        class Animal { string name; Animal(string n) { this.name = n; } }
        class Dog extends Animal { Dog(string n) : super(n) {} }
        void f(Animal* a) {}
        void g(Dog* d) { f(d); }
        void main() {}
        """)

    def test_interface_pointer_assignable(self):
        ok("""
        interface Printable { string toString(); }
        class Dog implements Printable {
            string name;
            Dog(string n) { this.name = n; }
            string toString() { return this.name; }
        }
        void print_it(Printable* p) {}
        void g(Dog* d) { print_it(d); }
        void main() {}
        """)


# ---------------------------------------------------------------------------
# TestErrorCatalogue — one test per error in the catalogue
# ---------------------------------------------------------------------------

class TestErrorCatalogue:
    def test_duplicate_top_level_name(self):
        err("int f() { return 1; } int f() { return 2; }", "already defined")

    def test_unknown_type_name(self):
        err("Foo f() { return 1; }", "unknown type 'Foo'")

    def test_undefined_variable(self):
        err("int f() { return x; }", "undefined variable 'x'")

    def test_undefined_function(self):
        err("int f() { return foo(); }", "undefined function 'foo'")

    def test_unknown_method(self):
        err(
            "class Dog { Dog() {} } void f(Dog d) { d.fly(); } void main() {}",
            "has no method 'fly'",
        )

    def test_unknown_field(self):
        err(
            "class Dog { Dog() {} } void f(Dog d) { string s = d.name; } void main() {}",
            "has no field 'name'",
        )

    def test_wrong_arg_count(self):
        err(
            "int add(int a, int b) { return a+b; } int main() { return add(1); }",
            "expects 2 arguments, got 1",
        )

    def test_type_mismatch_assign(self):
        err("void f() { int x = 0; x = true; }", "cannot assign 'bool' to 'int'")

    def test_type_mismatch_init(self):
        err("void f() { int x = true; }", "cannot initialise 'int' with 'bool'")

    def test_non_bool_condition_if(self):
        err("void f() { if (1) {} }", "condition must be bool, got 'int'")

    def test_non_bool_condition_while(self):
        err("void f() { while (1) {} }", "condition must be bool, got 'int'")

    def test_non_bool_logical_op(self):
        err("bool f() { return 1 && true; }", "requires bool")

    def test_int_only_operator(self):
        err("float f() { return 1.0 % 2.0; }", "requires int")

    def test_mismatched_binary_types(self):
        err("float f() { return 1 + 2.0; }", "type mismatch")

    def test_return_in_void_fn(self):
        err("void f() { return 1; }", "void function must not return a value")

    def test_missing_return_value(self):
        err("int f() { return; }", "non-void function must return a value")

    def test_missing_return_path(self):
        err("int f() { int x = 1; }", "not all code paths return a value")

    def test_non_lvalue_assignment(self):
        err("void f() { 5 = 3; }", "left-hand side of '=' is not assignable")

    def test_non_lvalue_address_of(self):
        err("void f() { int* p = &5; }", "operand of '&' must be an lvalue")

    def test_non_lvalue_increment(self):
        err("void f() { ++1; }", "operand of '++' must be an lvalue")

    def test_deref_non_pointer(self):
        err("int f() { int x = 5; return *x; }", "'*' requires a pointer, got 'int'")

    def test_arrow_on_non_pointer(self):
        err(
            "class Dog { Dog() {} } void f(Dog d) { d->speak(); } void main() {}",
            "'->' requires a pointer",
        )

    def test_index_non_array(self):
        err("int f() { int x = 5; return x[0]; }", "'[]' requires an array")

    def test_non_int_index(self):
        err("int f(int[5] a) { return a[true]; }", "array index must be int")

    def test_new_unknown_class(self):
        err("void main() { new Cat(); }", "unknown class 'Cat'")

    def test_delete_non_pointer(self):
        err("void main() { int x = 0; delete x; }", "'delete' requires a pointer")

    def test_alloc_void(self):
        err("void main() { alloc(void); }", "cannot alloc void")

    def test_free_non_pointer(self):
        err("void main() { int x = 0; free(x); }", "'free' requires a pointer")

    def test_invalid_cast(self):
        err("int f() { return (int) true; }", "invalid cast from 'bool' to 'int'")

    def test_this_in_static_context(self):
        err(
            "class C { static int f() { return this; } } void main() {}",
            "'this' is not available in a static method",
        )

    def test_super_without_parent(self):
        err(
            "class Dog { Dog() {} void f() { super; } } void main() {}",
            "'super' used in a class with no superclass",
        )

    def test_missing_super_call(self):
        err(
            "class Animal { Animal() {} } class Dog extends Animal { Dog() {} } void main() {}",
            "subclass constructor must call super",
        )

    def test_spurious_super_call(self):
        err(
            "class Dog { Dog() : super() {} } void main() {}",
            "super() used in a class with no superclass",
        )

    def test_wrong_super_args(self):
        err(
            """
            class Animal { Animal(int x) {} }
            class Dog extends Animal { Dog() : super(1, 2) {} }
            void main() {}
            """,
            "super(...) expects 1 arguments, got 2",
        )

    def test_interface_method_missing(self):
        err(
            "interface I { int f(); } class C implements I {} void main() {}",
            "does not implement",
        )

    def test_interface_method_sig_mismatch(self):
        err(
            """
            interface I { int f(); }
            class C implements I { string f() { return "x"; } }
            void main() {}
            """,
            "does not match interface signature",
        )

    def test_extends_nonexistent(self):
        err("class Dog extends Animal {} void main() {}", "unknown class 'Animal'")

    def test_extends_interface(self):
        err(
            "interface I { void f(); } class C extends I {} void main() {}",
            "cannot extend interface",
        )

    def test_implements_nonexistent(self):
        err("class Dog implements Printable {} void main() {}", "unknown interface 'Printable'")

    def test_implements_class(self):
        err(
            "class Animal {} class Dog implements Animal {} void main() {}",
            "cannot implement class",
        )

    def test_circular_inheritance(self):
        err(
            "class A extends B {} class B extends A {} void main() {}",
            "circular inheritance",
        )

    def test_break_outside_loop(self):
        err("void f() { break; }", "'break' outside a loop")

    def test_continue_outside_loop(self):
        err("void f() { continue; }", "'continue' outside a loop")


# ---------------------------------------------------------------------------
# TestWarningShadow — shadow warning goes to stderr, analysis continues
# ---------------------------------------------------------------------------

class TestWarningShadow:
    def test_shadow_emits_warning(self, capsys):
        ok("void f() { int x = 1; if (true) { int x = 2; } }")
        captured = capsys.readouterr()
        assert "shadows" in captured.err

    def test_shadow_analysis_continues(self, capsys):
        # Shadowing alone must not abort analysis
        ok("int f() { int x = 1; if (true) { int x = 2; } return x; }")

    def test_no_warning_without_shadow(self, capsys):
        ok("void f() { int x = 1; int y = 2; }")
        captured = capsys.readouterr()
        assert "shadows" not in captured.err


# ---------------------------------------------------------------------------
# TestCompilerIO — type-checking for getArgCount/getArg/printErr/exit
# ---------------------------------------------------------------------------

class TestCompilerIO:
    def test_get_arg_count_ok(self):
        ok("int main() { int n = getArgCount(); return n; }")

    def test_get_arg_count_no_args_required(self):
        err("int main() { int n = getArgCount(42); return n; }", "expects")

    def test_get_arg_ok(self):
        ok("int main() { string s = getArg(0); return 0; }")

    def test_get_arg_wrong_type_raises(self):
        err('int main() { string s = getArg("x"); return 0; }', "")

    def test_get_arg_wrong_arg_count_raises(self):
        err("int main() { string s = getArg(0, 1); return 0; }", "expects")

    def test_print_err_int_ok(self):
        ok("int main() { printErr(42); return 0; }")

    def test_print_err_string_ok(self):
        ok('int main() { printErr("msg"); return 0; }')

    def test_print_err_too_many_args(self):
        err('int main() { printErr(1, 2); return 0; }', "expects 1")

    def test_print_err_non_primitive_raises(self):
        err("class C {} int main() { C c = C(); printErr(c); return 0; }", "primitive")

    def test_exit_ok(self):
        ok("int main() { exit(0); return 0; }")

    def test_exit_wrong_type_raises(self):
        err('int main() { exit("bad"); return 0; }', "")
