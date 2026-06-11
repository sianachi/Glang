import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from lexer.lexer import Lexer
from parser.parser import Parser
from parser.ast_nodes import (
    Program, ImportDecl, FunctionDecl, ClassDecl, InterfaceDecl,
    FieldDecl, StaticFieldDecl, ConstructorDecl, DestructorDecl, MethodDecl,
    Block, VarDecl, AssignStmt, IfStmt, WhileStmt, DoWhileStmt, ForStmt,
    ForeachStmt,
    BreakStmt, ContinueStmt, ReturnStmt,
    BinaryExpr, UnaryExpr, CastExpr, CallExpr, IndirectCallExpr, ClosureExpr,
    MethodCallExpr,
    NewExpr, DeleteExpr, AllocExpr, FreeExpr,
    FieldAccessExpr, ArrowAccessExpr, IndexExpr,
    AddressOfExpr, DerefExpr,
    IdentifierExpr, LiteralExpr, NullExpr, ThisExpr, SuperExpr,
    NamedType, PointerType, ArrayType, FunctionPointerType,
)
from errors.errors import ParseError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def parse(src: str) -> Program:
    return Parser(Lexer(src).tokenize()).parse()


def parse_expr(src: str):
    """Parse a single expression inside a void function body."""
    prog = parse(f"void _f() {{ {src}; }}")
    return prog.declarations[0].body.stmts[0]


def parse_stmt(src: str):
    prog = parse(f"void _f() {{ {src} }}")
    return prog.declarations[0].body.stmts[0]


def named(name: str) -> NamedType:
    """NamedType with wildcard line/col for equality checks."""
    return NamedType(name, line=0, col=0)


def type_matches(node, expected) -> bool:
    """Compare type nodes ignoring line/col."""
    if type(node) != type(expected):
        return False
    if isinstance(node, NamedType):
        return node.name == expected.name
    if isinstance(node, PointerType):
        return type_matches(node.base, expected.base)
    if isinstance(node, ArrayType):
        return node.size == expected.size and type_matches(node.base, expected.base)
    if isinstance(node, FunctionPointerType):
        return (
            len(node.param_types) == len(expected.param_types)
            and all(type_matches(a, b) for a, b in zip(node.param_types, expected.param_types))
            and type_matches(node.return_type, expected.return_type)
        )
    return False


# ---------------------------------------------------------------------------
# TokenStream / top-level structure
# ---------------------------------------------------------------------------

class TestTopLevel:
    def test_empty_program(self):
        prog = parse("")
        assert prog.imports == []
        assert prog.declarations == []

    def test_import(self):
        prog = parse('import "stdlib/io.lang";')
        assert len(prog.imports) == 1
        assert isinstance(prog.imports[0], ImportDecl)
        assert prog.imports[0].path == "stdlib/io.lang"

    def test_multiple_imports(self):
        prog = parse('import "a.lang"; import "b.lang";')
        assert [i.path for i in prog.imports] == ["a.lang", "b.lang"]

    def test_function_decl(self):
        prog = parse("int add(int a, int b) { return a + b; }")
        assert len(prog.declarations) == 1
        fn = prog.declarations[0]
        assert isinstance(fn, FunctionDecl)
        assert fn.name == "add"
        assert type_matches(fn.return_type, named("int"))
        assert len(fn.params) == 2
        assert fn.params[0].name == "a" and type_matches(fn.params[0].type, named("int"))
        assert fn.params[1].name == "b" and type_matches(fn.params[1].type, named("int"))

    def test_void_no_params(self):
        prog = parse("void noop() {}")
        fn = prog.declarations[0]
        assert fn.params == []
        assert type_matches(fn.return_type, named("void"))


# ---------------------------------------------------------------------------
# TypeParser
# ---------------------------------------------------------------------------

class TestTypes:
    def test_primitive_types(self):
        for kw in ("int", "float", "bool", "char", "byte", "string", "void"):
            prog = parse(f"{kw} f() {{ return; }}")
            assert type_matches(prog.declarations[0].return_type, named(kw))

    def test_byte_pointer_and_array(self):
        prog = parse("byte* f() { return null; }")
        assert type_matches(
            prog.declarations[0].return_type, PointerType(NamedType("byte"))
        )
        prog = parse("byte[8] g() { return; }")
        t = prog.declarations[0].return_type
        assert isinstance(t, ArrayType)
        assert isinstance(t.base, NamedType) and t.base.name == "byte"
        assert t.size == 8

    def test_pointer_type(self):
        prog = parse("int* f() { return; }")
        assert type_matches(prog.declarations[0].return_type, PointerType(NamedType("int")))

    def test_double_pointer(self):
        prog = parse("int** f() { return; }")
        t = prog.declarations[0].return_type
        assert isinstance(t, PointerType)
        assert isinstance(t.base, PointerType)
        assert isinstance(t.base.base, NamedType) and t.base.base.name == "int"

    def test_array_type(self):
        prog = parse("int[10] f() { return; }")
        t = prog.declarations[0].return_type
        assert isinstance(t, ArrayType)
        assert isinstance(t.base, NamedType) and t.base.name == "int"
        assert t.size == 10

    def test_pointer_array(self):
        prog = parse("int*[10] f() { return; }")
        t = prog.declarations[0].return_type
        assert isinstance(t, ArrayType)
        assert isinstance(t.base, PointerType)

    def test_user_defined_type(self):
        prog = parse("Dog f() { return; }")
        t = prog.declarations[0].return_type
        assert isinstance(t, NamedType) and t.name == "Dog"

    def test_function_pointer_type(self):
        prog = parse("fn(int, int) -> int choose() { return null; }")
        t = prog.declarations[0].return_type
        assert type_matches(
            t,
            FunctionPointerType([NamedType("int"), NamedType("int")], NamedType("int")),
        )

    def test_function_pointer_local_decl(self):
        stmt = parse_stmt("fn(int) -> int f = null;")
        assert isinstance(stmt, VarDecl)
        assert type_matches(
            stmt.type,
            FunctionPointerType([NamedType("int")], NamedType("int")),
        )


# ---------------------------------------------------------------------------
# ExprParser — literals and identifiers
# ---------------------------------------------------------------------------

class TestLiterals:
    def test_int_literal(self):
        e = parse_expr("42")
        assert isinstance(e, LiteralExpr)
        assert e.kind == "int"
        assert e.value == "42"

    def test_float_literal(self):
        e = parse_expr("3.14")
        assert isinstance(e, LiteralExpr)
        assert e.kind == "float"

    def test_bool_true(self):
        e = parse_expr("true")
        assert isinstance(e, LiteralExpr)
        assert e.kind == "bool"
        assert e.value == "true"

    def test_bool_false(self):
        e = parse_expr("false")
        assert isinstance(e, LiteralExpr)
        assert e.value == "false"

    def test_char_literal(self):
        e = parse_expr("'a'")
        assert isinstance(e, LiteralExpr)
        assert e.kind == "char"

    def test_string_literal(self):
        e = parse_expr('"hello"')
        assert isinstance(e, LiteralExpr)
        assert e.kind == "string"

    def test_null(self):
        assert isinstance(parse_expr("null"), NullExpr)

    def test_this(self):
        assert isinstance(parse_expr("this"), ThisExpr)

    def test_super(self):
        assert isinstance(parse_expr("super"), SuperExpr)

    def test_identifier(self):
        e = parse_expr("myVar")
        assert isinstance(e, IdentifierExpr)
        assert e.name == "myVar"

    def test_empty_closure_literal(self):
        e = parse_expr("() -> int { return 1; }")
        assert isinstance(e, ClosureExpr)
        assert e.params == []
        assert type_matches(e.return_type, named("int"))

    def test_closure_literal_with_params(self):
        e = parse_expr("(int x, int y) -> int { return x + y; }")
        assert isinstance(e, ClosureExpr)
        assert [p.name for p in e.params] == ["x", "y"]
        assert all(type_matches(p.type, named("int")) for p in e.params)

    def test_indirect_call(self):
        e = parse_expr("(makeAdder(2))(5)")
        assert isinstance(e, IndirectCallExpr)
        assert isinstance(e.callee, CallExpr)
        assert len(e.args) == 1


# ---------------------------------------------------------------------------
# ExprParser — unary / address-of / deref / cast
# ---------------------------------------------------------------------------

class TestUnaryExpressions:
    def test_logical_not(self):
        e = parse_expr("!flag")
        assert isinstance(e, UnaryExpr)
        assert e.op == "!"

    def test_bitwise_not(self):
        e = parse_expr("~x")
        assert isinstance(e, UnaryExpr)
        assert e.op == "~"

    def test_pre_increment(self):
        e = parse_expr("++i")
        assert isinstance(e, UnaryExpr)
        assert e.op == "++"

    def test_pre_decrement(self):
        e = parse_expr("--i")
        assert isinstance(e, UnaryExpr)
        assert e.op == "--"

    def test_unary_minus(self):
        e = parse_expr("-1")
        assert isinstance(e, UnaryExpr)
        assert e.op == "-"

    def test_address_of(self):
        e = parse_expr("&x")
        assert isinstance(e, AddressOfExpr)
        assert isinstance(e.operand, IdentifierExpr)

    def test_deref(self):
        e = parse_expr("*p")
        assert isinstance(e, DerefExpr)
        assert isinstance(e.operand, IdentifierExpr)

    def test_cast_primitive(self):
        e = parse_expr("(int) f")
        assert isinstance(e, CastExpr)
        assert type_matches(e.target_type, named("int"))
        assert isinstance(e.expr, IdentifierExpr)

    def test_cast_pointer(self):
        e = parse_expr("(void*) p")
        assert isinstance(e, CastExpr)
        assert isinstance(e.target_type, PointerType)

    def test_grouping_not_cast(self):
        e = parse_expr("(a + b)")
        assert isinstance(e, BinaryExpr)


# ---------------------------------------------------------------------------
# ExprParser — binary operators and precedence
# ---------------------------------------------------------------------------

class TestBinaryExpressions:
    def test_addition(self):
        e = parse_expr("a + b")
        assert isinstance(e, BinaryExpr)
        assert e.op == "+"

    def test_precedence_mul_over_add(self):
        # a + b * c  →  a + (b * c)
        e = parse_expr("a + b * c")
        assert isinstance(e, BinaryExpr)
        assert e.op == "+"
        assert isinstance(e.right, BinaryExpr)
        assert e.right.op == "*"

    def test_left_associativity(self):
        # a - b - c  →  (a - b) - c
        e = parse_expr("a - b - c")
        assert isinstance(e, BinaryExpr)
        assert e.op == "-"
        assert isinstance(e.left, BinaryExpr)

    def test_logical_and_or_precedence(self):
        # a || b && c  →  a || (b && c)
        e = parse_expr("a || b && c")
        assert e.op == "||"
        assert e.right.op == "&&"

    def test_comparison(self):
        e = parse_expr("x == y")
        assert isinstance(e, BinaryExpr)
        assert e.op == "=="

    def test_bitwise_ops(self):
        e = parse_expr("a & b")
        assert e.op == "&"


# ---------------------------------------------------------------------------
# ExprParser — call, member access, index
# ---------------------------------------------------------------------------

class TestCallAndMemberAccess:
    def test_function_call_no_args(self):
        e = parse_expr("foo()")
        assert isinstance(e, CallExpr)
        assert e.name == "foo"
        assert e.args == []

    def test_function_call_with_args(self):
        e = parse_expr("add(1, 2)")
        assert isinstance(e, CallExpr)
        assert len(e.args) == 2

    def test_dot_field_access(self):
        e = parse_expr("obj.name")
        assert isinstance(e, FieldAccessExpr)
        assert e.field_name == "name"

    def test_dot_method_call(self):
        e = parse_expr("obj.speak()")
        assert isinstance(e, MethodCallExpr)
        assert e.method == "speak"
        assert e.is_arrow is False

    def test_arrow_field_access(self):
        e = parse_expr("ptr->name")
        assert isinstance(e, ArrowAccessExpr)
        assert e.field_name == "name"

    def test_arrow_method_call(self):
        e = parse_expr("ptr->speak()")
        assert isinstance(e, MethodCallExpr)
        assert e.is_arrow is True

    def test_index_expr(self):
        e = parse_expr("buf[i]")
        assert isinstance(e, IndexExpr)
        assert isinstance(e.array, IdentifierExpr)
        assert isinstance(e.index, IdentifierExpr)

    def test_chained_member_access(self):
        e = parse_expr("a.b.c")
        assert isinstance(e, FieldAccessExpr)
        assert isinstance(e.object, FieldAccessExpr)


# ---------------------------------------------------------------------------
# ExprParser — new / delete / alloc / free
# ---------------------------------------------------------------------------

class TestMemoryExprs:
    def test_new(self):
        e = parse_expr('new Dog("rex")')
        assert isinstance(e, NewExpr)
        assert e.class_name == "Dog"
        assert len(e.args) == 1

    def test_delete(self):
        e = parse_expr("delete d")
        assert isinstance(e, DeleteExpr)
        assert isinstance(e.operand, IdentifierExpr)

    def test_alloc(self):
        e = parse_expr("alloc(int)")
        assert isinstance(e, AllocExpr)
        assert isinstance(e.type, NamedType) and e.type.name == "int"

    def test_free(self):
        e = parse_expr("free(p)")
        assert isinstance(e, FreeExpr)
        assert isinstance(e.operand, IdentifierExpr)


# ---------------------------------------------------------------------------
# StmtParser
# ---------------------------------------------------------------------------

class TestStatements:
    def test_var_decl(self):
        s = parse_stmt("int x = 5;")
        assert isinstance(s, VarDecl)
        assert s.name == "x"
        assert isinstance(s.type, NamedType) and s.type.name == "int"
        assert isinstance(s.initializer, LiteralExpr)

    def test_var_inferred_decl(self):
        s = parse_stmt("var x = 5;")
        assert isinstance(s, VarDecl)
        assert s.name == "x"
        assert isinstance(s.type, NamedType) and s.type.name == "var"
        assert isinstance(s.initializer, LiteralExpr)

    def test_var_decl_requires_initializer(self):
        with pytest.raises(ParseError, match="initialiser"):
            parse_stmt("int x;")

    def test_var_decl_no_multi(self):
        with pytest.raises(ParseError, match="one variable"):
            parse_stmt("int x = 1, y = 2;")

    def test_assign_stmt(self):
        s = parse_stmt("x = 10;")
        assert isinstance(s, AssignStmt)
        assert s.op == "="

    def test_compound_assign(self):
        s = parse_stmt("x += 1;")
        assert isinstance(s, AssignStmt)
        assert s.op == "+="

    def test_break(self):
        assert isinstance(parse_stmt("break;"), BreakStmt)

    def test_continue(self):
        assert isinstance(parse_stmt("continue;"), ContinueStmt)

    def test_return_void(self):
        s = parse_stmt("return;")
        assert isinstance(s, ReturnStmt)
        assert s.value is None

    def test_return_value(self):
        s = parse_stmt("return 42;")
        assert isinstance(s, ReturnStmt)
        assert isinstance(s.value, LiteralExpr)

    def test_block(self):
        s = parse_stmt("{ int x = 1; int y = 2; }")
        assert isinstance(s, Block)
        assert len(s.stmts) == 2

    def test_if_no_else(self):
        s = parse_stmt("if (x > 0) { return; }")
        assert isinstance(s, IfStmt)
        assert s.else_branch is None

    def test_if_else(self):
        s = parse_stmt("if (x > 0) { return; } else { return; }")
        assert isinstance(s, IfStmt)
        assert isinstance(s.else_branch, Block)

    def test_else_if_chain(self):
        s = parse_stmt("if (a) { return; } else if (b) { return; } else { return; }")
        assert isinstance(s, IfStmt)
        assert isinstance(s.else_branch, IfStmt)
        assert isinstance(s.else_branch.else_branch, Block)

    def test_while(self):
        s = parse_stmt("while (n > 0) { n -= 1; }")
        assert isinstance(s, WhileStmt)
        assert isinstance(s.condition, BinaryExpr)

    def test_for(self):
        s = parse_stmt("for (int i = 0; i < 10; i += 1) { break; }")
        assert isinstance(s, ForStmt)
        assert isinstance(s.init, VarDecl)
        assert s.init.name == "i"
        assert isinstance(s.condition, BinaryExpr)
        assert isinstance(s.post, AssignStmt)
        assert s.post.op == "+="

    def test_for_prefix_post_step(self):
        s = parse_stmt("for (int i = 0; i < 10; ++i) { break; }")
        assert isinstance(s, ForStmt)
        assert isinstance(s.post, UnaryExpr)

    def test_do_while(self):
        s = parse_stmt("do { n += 1; } while (n < 10);")
        assert isinstance(s, DoWhileStmt)
        assert isinstance(s.condition, BinaryExpr)

    def test_foreach(self):
        s = parse_stmt("foreach (int n in nums) { break; }")
        assert isinstance(s, ForeachStmt)
        assert s.var_name == "n"
        assert type_matches(s.var_type, named("int"))
        assert isinstance(s.iterable, IdentifierExpr)

    def test_const_foreach(self):
        s = parse_stmt("foreach (const char c in text) { continue; }")
        assert isinstance(s, ForeachStmt)
        assert s.is_const
        assert s.var_name == "c"

    def test_expr_stmt_call(self):
        s = parse_stmt("foo();")
        assert isinstance(s, CallExpr)


# ---------------------------------------------------------------------------
# User-defined (class) pointer local declarations
#
# `Dog* d = ...` is unambiguously a declaration because `a * b` is never a
# valid assignment target; the parser distinguishes it from a multiplication
# expression statement by the trailing `=`.
# ---------------------------------------------------------------------------

class TestClassPointerVarDecl:
    def test_class_pointer_var_decl(self):
        s = parse_stmt("Dog* d = new Dog();")
        assert isinstance(s, VarDecl)
        assert s.name == "d"
        assert isinstance(s.type, PointerType)
        assert isinstance(s.type.base, NamedType) and s.type.base.name == "Dog"
        assert isinstance(s.initializer, NewExpr)

    def test_class_pointer_to_pointer_var_decl(self):
        s = parse_stmt("Dog** d = null;")
        assert isinstance(s, VarDecl)
        assert s.name == "d"
        assert isinstance(s.type, PointerType)
        assert isinstance(s.type.base, PointerType)
        assert isinstance(s.type.base.base, NamedType) and s.type.base.base.name == "Dog"
        assert isinstance(s.initializer, NullExpr)

    def test_class_pointer_without_initializer_is_multiplication(self):
        # Without the trailing `=`, the parser cannot tell `Dog` is a type, so
        # `Dog* d;` stays a multiplication expression statement (the analyser
        # later rejects it as undefined names). This mirrors plain `a * b;`.
        s = parse_stmt("Dog* d;")
        assert isinstance(s, BinaryExpr)
        assert s.op == "*"

    def test_multiplication_statement_not_misparsed(self):
        # `a * b;` must remain a multiplication expression statement.
        s = parse_stmt("a * b;")
        assert isinstance(s, BinaryExpr)
        assert s.op == "*"
        assert isinstance(s.left, IdentifierExpr) and s.left.name == "a"
        assert isinstance(s.right, IdentifierExpr) and s.right.name == "b"

    def test_multiplication_chain_not_misparsed(self):
        s = parse_stmt("a * b * c;")
        assert isinstance(s, BinaryExpr)
        assert s.op == "*"

    def test_primitive_pointer_still_works(self):
        s = parse_stmt("int* p = null;")
        assert isinstance(s, VarDecl)
        assert isinstance(s.type, PointerType)
        assert isinstance(s.type.base, NamedType) and s.type.base.name == "int"


# ---------------------------------------------------------------------------
# DeclParser — classes
# ---------------------------------------------------------------------------

class TestClassDecl:
    def test_minimal_class(self):
        prog = parse("class Foo {}")
        cls = prog.declarations[0]
        assert isinstance(cls, ClassDecl)
        assert cls.name == "Foo"
        assert cls.superclass is None
        assert cls.interfaces == []

    def test_extends(self):
        prog = parse("class Dog extends Animal {}")
        assert prog.declarations[0].superclass == "Animal"

    def test_implements_single(self):
        prog = parse("class Dog implements Printable {}")
        assert prog.declarations[0].interfaces == ["Printable"]

    def test_implements_multiple(self):
        prog = parse("class Dog implements Printable, Serializable {}")
        assert prog.declarations[0].interfaces == ["Printable", "Serializable"]

    def test_extends_and_implements(self):
        prog = parse("class Dog extends Animal implements Printable {}")
        cls = prog.declarations[0]
        assert cls.superclass == "Animal"
        assert cls.interfaces == ["Printable"]

    def test_static_field(self):
        prog = parse("class C { static int count = 0; }")
        cls = prog.declarations[0]
        assert len(cls.static_fields) == 1
        assert cls.static_fields[0].name == "count"
        assert isinstance(cls.static_fields[0].initializer, LiteralExpr)

    def test_instance_field(self):
        prog = parse("class C { string name; }")
        cls = prog.declarations[0]
        assert len(cls.fields) == 1
        assert cls.fields[0].name == "name"
        assert isinstance(cls.fields[0].type, NamedType) and cls.fields[0].type.name == "string"

    def test_constructor(self):
        prog = parse("class C { C(int x) { } }")
        cls = prog.declarations[0]
        assert isinstance(cls.constructor, ConstructorDecl)
        assert len(cls.constructor.params) == 1
        assert cls.constructor.super_args is None

    def test_constructor_with_super(self):
        prog = parse("class Dog extends Animal { Dog(string n) : super(n) { } }")
        cls = prog.declarations[0]
        assert cls.constructor.super_args is not None
        assert len(cls.constructor.super_args) == 1

    def test_destructor(self):
        prog = parse("class C { ~C() { } }")
        cls = prog.declarations[0]
        assert isinstance(cls.destructor, DestructorDecl)

    def test_destructor_name_mismatch(self):
        with pytest.raises(ParseError):
            parse("class C { ~D() { } }")

    def test_instance_method(self):
        prog = parse("class C { string speak() { return \"hi\"; } }")
        cls = prog.declarations[0]
        assert len(cls.methods) == 1
        m = cls.methods[0]
        assert m.name == "speak"
        assert m.is_static is False

    def test_static_method(self):
        prog = parse("class C { static int count() { return 0; } }")
        cls = prog.declarations[0]
        assert cls.methods[0].is_static is True

    def test_operator_method(self):
        prog = parse("class Vec2 { Vec2 operator+(Vec2 other) { return other; } }")
        cls = prog.declarations[0]
        assert len(cls.methods) == 1
        m = cls.methods[0]
        assert m.name == "operator+"
        assert m.is_static is False

    def test_operator_equality_method(self):
        prog = parse("class Vec2 { bool operator==(Vec2 other) { return true; } }")
        cls = prog.declarations[0]
        assert cls.methods[0].name == "operator=="

    def test_operator_index_method(self):
        prog = parse("class Vec2 { int operator[](int index) { return index; } }")
        cls = prog.declarations[0]
        assert cls.methods[0].name == "operator[]"

    def test_full_class(self):
        src = """
        class Dog extends Animal implements Printable {
            static int count = 0;
            string name;
            Dog(string n) : super(n) { this.name = n; }
            ~Dog() { }
            string speak() { return \"woof\"; }
            static int getCount() { return Dog.count; }
        }
        """
        prog = parse(src)
        cls = prog.declarations[0]
        assert len(cls.static_fields) == 1
        assert len(cls.fields) == 1
        assert cls.constructor is not None
        assert cls.destructor is not None
        assert len(cls.methods) == 2

    def test_fields_must_precede_methods(self):
        with pytest.raises(ParseError):
            parse("class C { string speak() { } string name; }")


# ---------------------------------------------------------------------------
# DeclParser — interfaces
# ---------------------------------------------------------------------------

class TestInterfaceDecl:
    def test_empty_interface(self):
        prog = parse("interface I {}")
        iface = prog.declarations[0]
        assert isinstance(iface, InterfaceDecl)
        assert iface.name == "I"
        assert iface.methods == []

    def test_interface_method_signature(self):
        prog = parse("interface Printable { string toString(); }")
        iface = prog.declarations[0]
        assert len(iface.methods) == 1
        m = iface.methods[0]
        assert m.name == "toString"
        assert isinstance(m.return_type, NamedType) and m.return_type.name == "string"
        assert m.body is None

    def test_multiple_signatures(self):
        prog = parse("interface I { int foo(int x); void bar(); }")
        assert len(prog.declarations[0].methods) == 2


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------

class TestErrors:
    def test_missing_semicolon(self):
        with pytest.raises(ParseError):
            parse("void f() { int x = 1 }")

    def test_unexpected_token_in_expr(self):
        with pytest.raises(ParseError):
            parse("void f() { int x = ; }")

    def test_mismatched_brace(self):
        with pytest.raises(ParseError):
            parse("void f() {")

    def test_import_requires_string(self):
        with pytest.raises(ParseError):
            parse("import foo;")
