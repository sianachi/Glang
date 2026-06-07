from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, List, Any


# ---------------------------------------------------------------------------
# Base marker classes
# ---------------------------------------------------------------------------

class Node:
    """Base for every AST node. Carries no data."""

class Expr(Node):
    """Marker for expression nodes — nodes that produce a value."""

class Stmt(Node):
    """Marker for statement nodes — nodes that are executed for side effects."""

class Decl(Node):
    """Marker for top-level and class-body declarations."""


# ---------------------------------------------------------------------------
# Type nodes
# ---------------------------------------------------------------------------

class TypeNode(Node):
    """Base for all type representations."""


@dataclass
class NamedType(TypeNode):
    """A primitive or class type referred to by name.

    Covers both built-in primitives (int, float, bool, char, string, void)
    and user-defined class/interface names (Dog, Animal, Printable).

    Examples:
      int         → NamedType("int")
      Dog         → NamedType("Dog")
    """
    name: str
    line: int = 0
    col: int = 0


@dataclass
class PointerType(TypeNode):
    """A pointer to another type (T*).

    Examples:
      int*    → PointerType(NamedType("int"))
      Dog**   → PointerType(PointerType(NamedType("Dog")))
    """
    base: TypeNode
    line: int = 0
    col: int = 0


@dataclass
class ArrayType(TypeNode):
    """A fixed-size stack array (T[N]).

    The size must be a compile-time integer constant; the semantic analyser
    enforces this. The parser stores the size as a raw integer.

    Examples:
      int[10]    → ArrayType(NamedType("int"), 10)
      char[256]  → ArrayType(NamedType("char"), 256)
    """
    base: TypeNode
    size: int
    line: int = 0
    col: int = 0


# ---------------------------------------------------------------------------
# Helper: function / method parameter
# ---------------------------------------------------------------------------

@dataclass
class Param:
    """A single formal parameter in a function or method signature.

    Example:
      int add(int a, int b)  →  [Param("a", NamedType("int")),
                                  Param("b", NamedType("int"))]
    """
    name: str
    type: TypeNode
    line: int = 0
    col: int = 0


# ---------------------------------------------------------------------------
# Top-level program structure
# ---------------------------------------------------------------------------

@dataclass
class ImportDecl(Decl):
    """An import statement bringing another source file into scope.

    Example:
      import "stdlib/list.lang";  →  ImportDecl("stdlib/list.lang")
    """
    path: str
    line: int = 0
    col: int = 0


@dataclass
class Program(Node):
    """Root node of the AST — the entire compilation unit.

    Contains all imports (in order) followed by all top-level declarations
    (functions, classes, interfaces) in source order.
    """
    imports: List[ImportDecl]
    declarations: List[Decl]
    line: int = 0
    col: int = 0


# ---------------------------------------------------------------------------
# Declarations — functions
# ---------------------------------------------------------------------------

@dataclass
class FunctionDecl(Decl):
    """A top-level function declaration.

    Example:
      int add(int a, int b) { return a + b; }
      →  FunctionDecl("add", [Param("a", ...), Param("b", ...)],
                       NamedType("int"), Block([...]))
    """
    name: str
    params: List[Param]
    return_type: TypeNode
    body: Block
    line: int = 0
    col: int = 0


# ---------------------------------------------------------------------------
# Declarations — classes
# ---------------------------------------------------------------------------

@dataclass
class FieldDecl(Decl):
    """An instance field declaration inside a class body.

    Instance fields have no initialiser; they are zero-initialised by the
    default constructor or explicitly written in the user-defined constructor.

    Example:
      string name;  →  FieldDecl("name", NamedType("string"))
    """
    name: str
    type: TypeNode
    line: int = 0
    col: int = 0


@dataclass
class StaticFieldDecl(Decl):
    """A static (class-level) field declaration with a required initialiser.

    Example:
      static int count = 0;
      →  StaticFieldDecl("count", NamedType("int"), LiteralExpr("int", "0"))
    """
    name: str
    type: TypeNode
    initializer: Expr
    line: int = 0
    col: int = 0


@dataclass
class ConstructorDecl(Decl):
    """A class constructor.

    If the class extends a base class, `super_args` holds the arguments
    passed to the parent constructor via `: super(...)`. The parser
    enforces that super_args is only present on subclass constructors.

    Example:
      Dog(string n) : super(n) { ... }
      →  ConstructorDecl([Param("n", NamedType("string"))],
                          super_args=[IdentifierExpr("n")],
                          body=Block([...]))
    """
    params: List[Param]
    body: Block
    super_args: Optional[List[Expr]] = None
    line: int = 0
    col: int = 0


@dataclass
class DestructorDecl(Decl):
    """A class destructor (~ClassName()).

    Takes no parameters and has no return type. Called automatically by
    `delete`; chaining through the inheritance hierarchy is handled by
    the runtime.

    Example:
      ~Animal() { Animal.count -= 1; }
      →  DestructorDecl(body=Block([...]))
    """
    body: Block
    line: int = 0
    col: int = 0


@dataclass
class MethodDecl(Decl):
    """An instance or static method declaration inside a class body.

    Static methods carry `is_static=True` and have no access to `this`.

    Example:
      string speak() { return "woof"; }
      →  MethodDecl("speak", [], NamedType("string"), Block([...]))

      static int getCount() { return Animal.count; }
      →  MethodDecl("getCount", [], NamedType("int"), Block([...]),
                     is_static=True)
    """
    name: str
    params: List[Param]
    return_type: TypeNode
    body: Block
    is_static: bool = False
    line: int = 0
    col: int = 0


@dataclass
class ClassDecl(Decl):
    """A class declaration, optionally extending a base class and/or
    implementing one or more interfaces.

    Fields must appear before constructor/destructor/methods in the
    source; the parser enforces this ordering.

    Example:
      class Dog extends Animal implements Printable {
          string name;
          Dog(string n) : super(n) {}
          string speak() { return "woof"; }
      }
    """
    name: str
    fields: List[FieldDecl]
    static_fields: List[StaticFieldDecl]
    methods: List[MethodDecl]
    superclass: Optional[str] = None
    interfaces: List[str] = field(default_factory=list)
    constructor: Optional[ConstructorDecl] = None
    destructor: Optional[DestructorDecl] = None
    line: int = 0
    col: int = 0


@dataclass
class InterfaceDecl(Decl):
    """An interface declaration containing only method signatures.

    Interface bodies have no fields, no static members, and no method
    bodies. Each signature is stored as a MethodDecl with body=None.

    Example:
      interface Printable {
          string toString();
      }
    """
    name: str
    methods: List[MethodDecl]
    line: int = 0
    col: int = 0


# ---------------------------------------------------------------------------
# Statements
# ---------------------------------------------------------------------------

@dataclass
class Block(Stmt):
    """A brace-delimited sequence of statements.

    Introduces a new lexical scope. Used as the body of functions,
    methods, if/else branches, loops, etc.
    """
    stmts: List[Stmt]
    line: int = 0
    col: int = 0


@dataclass
class VarDecl(Stmt):
    """A local variable declaration with a required initialiser.

    The spec forbids uninitialised variables — the parser must reject
    declarations without an initialiser.

    Example:
      int x = 5;  →  VarDecl("x", NamedType("int"), LiteralExpr("int","5"))
    """
    name: str
    type: TypeNode
    initializer: Expr
    line: int = 0
    col: int = 0


@dataclass
class AssignStmt(Stmt):
    """An assignment statement (never an expression).

    `target` is an lvalue expression: IdentifierExpr, FieldAccessExpr,
    ArrowAccessExpr, DerefExpr, or IndexExpr.
    `op` is one of: = += -= *= /= %=

    Example:
      x += 1;  →  AssignStmt(IdentifierExpr("x"), "+=", LiteralExpr(...))
    """
    target: Expr
    op: str
    value: Expr
    line: int = 0
    col: int = 0


@dataclass
class IfStmt(Stmt):
    """An if / else-if / else chain.

    `else_branch` is either another IfStmt (else-if) or a Block (else),
    or None when there is no else clause.

    Example:
      if (x > 0) { ... } else { ... }
    """
    condition: Expr
    then_branch: Block
    else_branch: Optional[Block | IfStmt] = None
    line: int = 0
    col: int = 0


@dataclass
class WhileStmt(Stmt):
    """A while loop.

    Example:
      while (cond) { ... }
    """
    condition: Expr
    body: Block
    line: int = 0
    col: int = 0


@dataclass
class ForStmt(Stmt):
    """A for loop with mandatory init, condition, and post sections.

    `init`      — a VarDecl scoped to the loop body.
    `condition` — must evaluate to bool.
    `post`      — typically an AssignStmt (i += 1) or a UnaryExpr (++i).

    Example:
      for (int i = 0; i < n; ++i) { ... }
    """
    init: VarDecl
    condition: Expr
    post: Any  # AssignStmt | UnaryExpr
    body: Block
    line: int = 0
    col: int = 0


@dataclass
class BreakStmt(Stmt):
    """A break statement; exits the nearest enclosing loop.

    Example:
      break;
    """
    line: int = 0
    col: int = 0


@dataclass
class ContinueStmt(Stmt):
    """A continue statement; jumps to the next loop iteration.

    Example:
      continue;
    """
    line: int = 0
    col: int = 0


@dataclass
class ReturnStmt(Stmt):
    """A return statement, with an optional value for non-void functions.

    Example:
      return;          →  ReturnStmt(value=None)
      return a + b;    →  ReturnStmt(value=BinaryExpr(...))
    """
    value: Optional[Expr] = None
    line: int = 0
    col: int = 0


# ---------------------------------------------------------------------------
# Expressions
# ---------------------------------------------------------------------------

@dataclass
class BinaryExpr(Expr):
    """A binary infix expression.

    `op` is the operator string: + - * / % & | ^ << >> && || == != < <= > >=

    Example:
      a + b  →  BinaryExpr(IdentifierExpr("a"), "+", IdentifierExpr("b"))
    """
    left: Expr
    op: str
    right: Expr
    line: int = 0
    col: int = 0


@dataclass
class UnaryExpr(Expr):
    """A prefix unary expression.

    `op` is one of: ! ~ ++ -- unary- unary+
    Address-of (&) and dereference (*) have their own dedicated nodes.

    Example:
      !flag   →  UnaryExpr("!", IdentifierExpr("flag"))
      ++i     →  UnaryExpr("++", IdentifierExpr("i"))
    """
    op: str
    operand: Expr
    line: int = 0
    col: int = 0


@dataclass
class CastExpr(Expr):
    """An explicit type cast.

    Example:
      (int) f       →  CastExpr(NamedType("int"), IdentifierExpr("f"))
      (void*) myPtr →  CastExpr(PointerType(NamedType("void")), ...)
    """
    target_type: TypeNode
    expr: Expr
    line: int = 0
    col: int = 0


@dataclass
class CallExpr(Expr):
    """A call to a free (top-level) function.

    Example:
      add(a, b)  →  CallExpr("add", [IdentifierExpr("a"), ...])
    """
    name: str
    args: List[Expr]
    line: int = 0
    col: int = 0


@dataclass
class MethodCallExpr(Expr):
    """A method call on an object or pointer.

    `is_arrow=True` means the call used -> (pointer receiver);
    `is_arrow=False` means it used . (value receiver).

    Examples:
      obj.speak()  →  MethodCallExpr(IdentifierExpr("obj"), "speak", [], False)
      ptr->speak() →  MethodCallExpr(IdentifierExpr("ptr"), "speak", [], True)
    """
    object: Expr
    method: str
    args: List[Expr]
    is_arrow: bool
    line: int = 0
    col: int = 0


@dataclass
class NewExpr(Expr):
    """A heap object allocation via `new`.

    Allocates memory, calls the constructor, and returns a pointer.

    Example:
      new Dog("Rex")  →  NewExpr("Dog", [LiteralExpr("string", "Rex")])
    """
    class_name: str
    args: List[Expr]
    line: int = 0
    col: int = 0


@dataclass
class DeleteExpr(Expr):
    """A heap object deallocation via `delete`.

    Calls the destructor chain then frees memory. `delete null` is a no-op.

    Example:
      delete d;  →  DeleteExpr(IdentifierExpr("d"))
    """
    operand: Expr
    line: int = 0
    col: int = 0


@dataclass
class AllocExpr(Expr):
    """A raw heap allocation for a primitive or pointer type via `alloc(T)`.

    Returns a T*. The allocated memory is uninitialised.

    Example:
      alloc(int)  →  AllocExpr(NamedType("int"))
    """
    type: TypeNode
    line: int = 0
    col: int = 0


@dataclass
class FreeExpr(Expr):
    """A raw heap deallocation via `free(p)`.

    Frees the pointer without calling any destructor. Typically used with
    memory allocated by `alloc`, not `new`.

    Example:
      free(p);  →  FreeExpr(IdentifierExpr("p"))
    """
    operand: Expr
    line: int = 0
    col: int = 0


@dataclass
class FieldAccessExpr(Expr):
    """A dot field access on a value (not a pointer).

    Example:
      obj.name  →  FieldAccessExpr(IdentifierExpr("obj"), "name")
    """
    object: Expr
    field_name: str
    line: int = 0
    col: int = 0


@dataclass
class ArrowAccessExpr(Expr):
    """An arrow field access through a pointer (equivalent to (*p).field).

    Example:
      ptr->name  →  ArrowAccessExpr(IdentifierExpr("ptr"), "name")
    """
    pointer: Expr
    field_name: str
    line: int = 0
    col: int = 0


@dataclass
class IndexExpr(Expr):
    """An array index expression.

    Example:
      buf[i]  →  IndexExpr(IdentifierExpr("buf"), IdentifierExpr("i"))
    """
    array: Expr
    index: Expr
    line: int = 0
    col: int = 0


@dataclass
class AddressOfExpr(Expr):
    """The address-of operator (&x), producing a pointer to its operand.

    Example:
      &x  →  AddressOfExpr(IdentifierExpr("x"))
    """
    operand: Expr
    line: int = 0
    col: int = 0


@dataclass
class DerefExpr(Expr):
    """A pointer dereference (*p), producing the value at the address.

    Example:
      *p  →  DerefExpr(IdentifierExpr("p"))
    """
    operand: Expr
    line: int = 0
    col: int = 0


@dataclass
class IdentifierExpr(Expr):
    """A bare name that refers to a variable, parameter, or class.

    Example:
      x  →  IdentifierExpr("x")
    """
    name: str
    line: int = 0
    col: int = 0


@dataclass
class LiteralExpr(Expr):
    """A literal value of any primitive kind.

    `kind` is one of: "int" "float" "bool" "char" "string"
    `value` is the decoded string representation from the lexer
    (e.g. actual newline char for '\\n', decimal string for 0xFF).

    Examples:
      42      →  LiteralExpr("int",    "42")
      3.14    →  LiteralExpr("float",  "3.14")
      true    →  LiteralExpr("bool",   "true")
      'a'     →  LiteralExpr("char",   "a")
      "hello" →  LiteralExpr("string", "hello")
    """
    kind: str
    value: str
    line: int = 0
    col: int = 0


@dataclass
class NullExpr(Expr):
    """The null literal, assignable to any pointer or object type.

    Example:
      null  →  NullExpr()
    """
    line: int = 0
    col: int = 0


@dataclass
class ThisExpr(Expr):
    """The `this` keyword, a pointer to the current instance.

    Valid only inside instance methods and constructors.

    Example:
      this.name  →  FieldAccessExpr(ThisExpr(), "name")
    """
    line: int = 0
    col: int = 0


@dataclass
class SuperExpr(Expr):
    """The `super` keyword, used to call a parent class method.

    Typically appears as the receiver in a MethodCallExpr.

    Example:
      super.speak()  →  MethodCallExpr(SuperExpr(), "speak", [], False)
    """
    line: int = 0
    col: int = 0
