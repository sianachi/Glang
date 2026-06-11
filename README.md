# Glang
# Language Specification — v1.0

## Table of Contents

1. [Overview](#1-overview)
2. [Lexical Structure](#2-lexical-structure)
3. [Types](#3-types)
4. [Variables & Declarations](#4-variables--declarations)
5. [Operators](#5-operators)
6. [Control Flow](#6-control-flow)
7. [Functions](#7-functions)
8. [Memory Model](#8-memory-model)
9. [Classes](#9-classes)
10. [Interfaces](#10-interfaces)
11. [Enums](#11-enums)
12. [Scope & Lifetime](#12-scope--lifetime)
13. [Modules](#13-modules)
14. [Entry Point](#14-entry-point)
15. [Memory-safety violations](#15-memory-safety-violations)
16. [Future Work](#16-future-work)

---

## 1. Overview

A statically-typed, manually-managed, C-style language with single inheritance and interface-based polymorphism. The runtime is intentionally minimal — no garbage collector, no exceptions, no implicit allocations. The only built-in I/O is `print` for diagnostics (§7.5); richer I/O and higher-level facilities (dynamic arrays, GC allocators, string builders, etc.) are provided by a standard library written in the language itself.

**Design goals:**
- Simple, unambiguous syntax close to C/Java
- Explicit control over memory
- A type system expressive enough to write a standard library
- A small, auditable runtime

---

## 2. Lexical Structure

### 2.1 Comments

```
// Single-line comment

/* Multi-line
   comment */
```

Block comments do not nest.

### 2.2 Identifiers

Identifiers start with a letter or underscore, followed by any number of letters, digits, or underscores.

```
[a-zA-Z_][a-zA-Z0-9_]*
```

### 2.3 Keywords

```
alloc     bool      break     byte      char      class
const     continue  delete    else      enum      extends
false     float     fn        for       free      if
implements  import  int       interface namespace new
null      private   protected public    return    static
string    super     this      true      void      while
```

### 2.4 Literals

| Kind    | Examples                              |
|---------|---------------------------------------|
| Integer | `0` `42` `-7` `0xFF` `0b1010`         |
| Float   | `3.14` `-0.5` `1e10` `1.5e-3`         |
| Bool    | `true` `false`                        |
| Char    | `'a'` `'\n'` `'\t'` `'\\'` `'\xFF'`  |
| String  | `"hello"` `"line\n"` `"say \"hi\""` |
| Null    | `null`                                |

Integer literals may use `_` as a visual separator: `1_000_000`.

### 2.5 Escape sequences (char and string)

| Sequence | Meaning        |
|----------|----------------|
| `\n`     | Newline        |
| `\t`     | Tab            |
| `\r`     | Carriage return|
| `\\`     | Backslash      |
| `\"`     | Double quote   |
| `\'`     | Single quote   |
| `\0`     | Null byte      |
| `\xHH`   | Hex byte       |

---

## 3. Types

### 3.1 Primitive types

| Type     | Representation   | Notes                                      |
|----------|------------------|--------------------------------------------|
| `int`    | 64-bit signed    | Integer division when both operands are int|
| `float`  | 64-bit IEEE 754  |                                            |
| `bool`   | 1 byte           | Not an alias of int                        |
| `char`   | 1 byte           | ASCII only; *text*, not arithmetic         |
| `byte`   | unsigned 8-bit   | Octet for binary data; wraps modulo 256    |
| `string` | Heap (ptr + len) | Immutable; `+` allocates a new string      |
| `null`   | —                | Only assignable to pointer/object types    |

**`byte`** is an unsigned 8-bit integer (`0..255`), distinct from both `int`
(width-unspecified text-free integer) and `char` (a text character). It is the
substrate for binary data — buffers, octets, and `byte[]` blocks.

- Arithmetic (`+ - * / %`), bitwise (`& | ^ ~ << >>`), comparisons, and
  `++`/`--` are all supported. Results stay `byte` and **wrap modulo 256**
  (e.g. `(byte)200 + (byte)100` is `44`).
- An integer **literal** in `0..255` may be used directly where a `byte` is
  expected; the range is checked at compile time (`byte b = 0xFF;` is fine,
  `byte b = 300;` is an error). An `int` *variable* still needs an explicit
  `(byte)` cast.
- `byte` does not mix with `int` variables in one expression without a cast,
  matching the no-implicit-conversion rule for `int`/`float`.

### 3.2 Pointer types

Any type can be made into a pointer type with `*`:

```
int*       // pointer to int
int**      // pointer to pointer to int
Dog*       // pointer to Dog instance
void*      // untyped pointer
```

`void*` can hold any pointer. Casting to/from `void*` is explicit.

### 3.3 Array types

Fixed-size arrays are declared with the size as part of the type:

```
int[10] buf;           // 10 ints on the stack
char[256] name;
```

Array size must be a compile-time constant. Dynamic arrays are a standard library concern. Arrays are zero-indexed. Out-of-bounds access is undefined behaviour.

### 3.4 Type casting

All casts are explicit:

```
float f = 3.9;
int i = (int) f;       // truncates to 3

byte b = (byte) 511;   // masks to low 8 bits -> 255
int  n = (int) b;      // 255
char c = (char) b;     // byte <-> char also allowed

void* p = (void*) myPtr;
Dog* d = (Dog*) p;
```

No implicit numeric widening or narrowing. No implicit bool/int conversion. The
allowed primitive casts are `int <-> float`, `int <-> char`, `int <-> byte`, and
`char <-> byte`; casting *to* `byte` masks the value to `0..255`. As a
convenience, an integer *literal* in range coerces to `byte` without a cast
(see §3.1).

### 3.5 Enum types

An enum is a named set of integer constants. Each variant carries a distinct `int` value.

```
enum Color  { RED, GREEN, BLUE }            // implicit: RED=0, GREEN=1, BLUE=2
enum Status { OK = 200, NOT_FOUND = 404 }   // explicit values
```

Implicit values start at 0 and increment by 1; after an explicit value the next implicit value is `explicit + 1`.

Enum types are **not** aliases of `int` — the type checker prevents assigning an `int` to an enum or vice versa without an explicit cast:

```
Color c = Color.GREEN;        // ok
int   n = (int) c;            // ok — cast to int
Color d = (Color) 2;          // ok — cast int to enum
int   x = Color.RED;          // error: cannot assign 'Color' to 'int'
Color e = 0;                  // error: cannot assign 'int' to 'Color'
```

Variant access uses dot notation (`Color.RED`). Enum values support `==` and `!=` comparisons.

---

## 4. Variables & Declarations

### 4.1 Local variables

```
int x = 5;
float pi = 3.14;
bool flag = true;
string name = "Rex";
```

Type is required. Initialiser is required — uninitialized variables are a compile error.

### 4.2 Multiple declarations

One variable per declaration statement. No `int x = 1, y = 2;`.

### 4.3 Constants

```
// No const keyword in v1.
// Convention: ALL_CAPS names for values that should not change.
int MAX_SIZE = 1024;
```

A `const` keyword is reserved for a future version.

---

## 5. Operators

### 5.1 Arithmetic

| Operator | Description                              |
|----------|------------------------------------------|
| `+`      | Addition; also string concatenation      |
| `-`      | Subtraction                              |
| `*`      | Multiplication                           |
| `/`      | Division (integer if both sides are int) |
| `%`      | Modulo (int or byte operands)            |

When both operands are `byte`, every arithmetic operator yields a `byte` that
wraps modulo 256 (§3.1).

### 5.2 Comparison

All return `bool`.

```
==  !=  <  >  <=  >=
```

Comparing a pointer to `null` is valid. Comparing two pointers checks address equality.

### 5.3 Logical

```
&&   // AND — short-circuit
||   // OR  — short-circuit
!    // NOT
```

Operands must be `bool`. Integers are not truthy.

### 5.4 Bitwise (int or byte)

```
&   |   ^   ~   <<   >>
```

Operands must both be `int` or both be `byte`. Right shift is arithmetic
(sign-extending) for signed ints. When the operands are `byte`, the result is a
`byte` masked to `0..255` (so `~` and `<<` stay in range).

### 5.5 Assignment

```
=   +=   -=   *=   /=   %=   &=   |=   ^=   <<=   >>=
```

Assignment is a statement, not an expression. It does not return a value. Chained assignment (`a = b = 5`) is not allowed.

The bitwise compound assignments (`&=`, `|=`, `^=`, `<<=`, `>>=`) are valid on `int` or `byte` operands, matching the restriction on their non-compound counterparts (§5.4).

### 5.6 Increment / decrement

Prefix only:

```
++i;   // increment
--i;   // decrement
```

Postfix (`i++`) is not supported.

### 5.7 Address-of and dereference

```
&x       // address of x — produces int*
*p       // dereference pointer p
p->field // dereference p and access field (equivalent to (*p).field)
```

### 5.8 Operator precedence (high to low)

| Level | Operators                        |
|-------|----------------------------------|
| 1     | `!` `~` `++` `--` (prefix) `&` `*` (unary) cast |
| 2     | `*` `/` `%`                      |
| 3     | `+` `-`                          |
| 4     | `<<` `>>`                        |
| 5     | `<` `>` `<=` `>=`                |
| 6     | `==` `!=`                        |
| 7     | `&`                              |
| 8     | `^`                              |
| 9     | `\|`                             |
| 10    | `&&`                             |
| 11    | `\|\|`                           |
| 12    | `=` `+=` `-=` `*=` `/=` `%=` `&=` `\|=` `^=` `<<=` `>>=` |

Use parentheses liberally. When in doubt, parenthesise.

---

## 6. Control Flow

### 6.1 If / else

```c
if (x > 0) {
    // ...
} else if (x == 0) {
    // ...
} else {
    // ...
}
```

Braces are always required, even for single-statement bodies. The condition must be `bool`.

### 6.2 While

```c
while (cond) {
    // ...
}
```

### 6.3 For

```c
for (int i = 0; i < n; ++i) {
    // ...
}
```

The init, condition, and post sections are all required. The loop variable is scoped to the loop body.

### 6.4 Break and continue

```c
break;      // exit the nearest enclosing loop
continue;   // jump to the next iteration
```

### 6.5 Return

```c
return;          // void function
return value;    // typed function
```

All non-void code paths must return a value — enforced at compile time.

---

## 7. Functions

### 7.1 Declaration

```c
int add(int a, int b) {
    return a + b;
}

void log(string msg) {
    // ...
}
```

Return type is required. Parameter types are required. No default parameters. No overloading — each function name must be unique within its scope.

### 7.2 Multiple return values

Use out-parameters (pointers):

```c
void divmod(int a, int b, int* q, int* r) {
    *q = a / b;
    *r = a % b;
}

// call site
int q = 0;
int r = 0;
divmod(10, 3, &q, &r);
```

### 7.3 Recursion

Supported. No tail-call optimisation guarantee in v1.

### 7.4 Restrictions

- No function overloading
- No default parameters
- No variadic functions
- Functions are not first-class values (no function pointers in v1)
- No nested function definitions

### 7.5 Built-in functions

The runtime provides a single built-in function, `print`, for diagnostic output:

```c
print(42);          // 42
print(3.14);        // 3.14
print(true);        // true
print('a');         // a
print("hello");     // hello
```

- `print` takes exactly one argument of a primitive type (`int`, `float`, `bool`, `char`, `byte`, or `string`) and returns `void`. A `byte` prints as its numeric value (`0..255`).
- It writes the value followed by a newline. `bool` prints as `true`/`false`.
- `print` is not a keyword and not overloadable; it occupies the global function namespace and may not be redefined.

Alongside `print` and the string built-ins (`len`, `substr`, `parseInt`, `parseFloat`, `toString`, `startsWith`, `endsWith`, `contains`, `indexOf`), the runtime provides three file-I/O built-ins. They are always available — no import is required — and operate on paths relative to the process working directory:

```c
writeFile("out.txt", "hello\n");   // (string, string) -> void
bool ok = fileExists("out.txt");   // (string) -> bool
string s = readFile("out.txt");    // (string) -> string  (errors if missing)
```

The runtime also provides two `byte`/`string` interop built-ins (no import
required):

```c
byte* bs = bytesFromString("Hi!");      // (string) -> byte*  (heap block)
string s = stringFromBytes(bs, 3);      // (byte*, int) -> string
free(bs);
```

`bytesFromString` allocates a heap `byte` block holding the string's code units
(masked to 8 bits); the caller owns it and must `free` it. `stringFromBytes`
rebuilds a string from the first `len` bytes of a block (out-of-bounds `len` is a
runtime error).

Higher-level, line-oriented helpers built on these live in `std/io.lang` (see the Standard Library section).

---

## 8. Memory Model

### 8.1 Stack allocation

Primitive types and fixed-size arrays declared inside a function or block are stack-allocated. They are freed automatically when the enclosing scope exits.

```c
int x = 5;           // stack
int[64] buf;         // stack
```

### 8.2 Heap allocation — primitives

```c
int* p = alloc(int);
*p = 42;
free(p);
```

`alloc(T)` allocates enough memory for one value of type `T` and returns a `T*`. The memory is uninitialised — you must write before reading. `free(p)` releases the memory. Behaviour after `free` is undefined.

A count allocates a **contiguous block** of zero-initialised cells, which is indexable through the pointer with `p[i]`:

```c
int* xs = alloc(int, 8);   // a block of 8 zeroed ints
xs[3] = 42;
int v = xs[3];             // 42  (in-bounds; out-of-bounds is a runtime error)
free(xs);                  // frees the whole block
```

This — a sized `alloc` plus pointer indexing — is what lets the standard-library collections (`List<T>`, `Map<K,V>`, …) grow by allocating a larger block, copying, and freeing the old one.

### 8.3 Heap allocation — objects

Objects are always heap-allocated via `new` and `delete`:

```c
Dog* d = new Dog("Rex");
d->speak();
delete d;            // calls destructor, then frees memory
```

`new` calls the constructor. `delete` calls the destructor, then frees the memory. Calling `delete` on `null` is a no-op.

### 8.4 Destructor chaining

When `delete` is called on a subclass instance through a base class pointer, the subclass destructor runs first, then the base class destructor. This requires that the vtable stores the destructor.

```c
Animal* a = new Dog("Rex");
delete a;            // calls ~Dog(), then ~Animal()
```

### 8.5 Ownership rules

The language has no ownership tracking. By convention:
- The caller that calls `new` owns the object
- A function that receives a pointer does not own it unless documented otherwise
- The standard library will provide owning wrapper types

### 8.6 `null`

`null` can be assigned to any pointer or object type. Dereferencing `null` is undefined behaviour. Null checks are explicit:

```c
if (p == null) { ... }
```

---

## 9. Classes

### 9.1 Declaration

```c
class Animal {
    // fields
    string name;
    static int count = 0;

    // constructor
    Animal(string n) {
        this.name = n;
        Animal.count += 1;
    }

    // destructor
    ~Animal() {
        Animal.count -= 1;
    }

    // instance method
    string speak() {
        return "...";
    }

    // static method
    static int getCount() {
        return Animal.count;
    }
}
```

### 9.2 Fields

- Instance fields are declared at the top of the class body with their type
- Static fields are declared with `static` and must have an initialiser
- All fields are public in v1
- Fields are accessed via `this.field` inside instance methods, and via `ClassName.field` for static fields

### 9.3 Constructor

- Same name as the class, no return type
- Called via `new ClassName(args)`
- A class with no explicit constructor gets a zero-argument default constructor that zero-initialises all fields
- A class with any explicit constructor does not get a default constructor

### 9.4 Destructor

- Named `~ClassName()`, no parameters, no return type
- Called automatically by `delete`
- A class with no explicit destructor gets a no-op destructor
- Destructor chaining through inheritance is automatic

### 9.5 `this`

Inside any instance method or constructor, `this` is a pointer to the current instance. Field and method access through `this` uses `this.field` / `this.method()`.

### 9.6 Static members

Accessed via `ClassName.member`, never via an instance. Static methods have no access to `this`.

### 9.7 Inheritance

Single inheritance only via `extends`:

```c
class Dog extends Animal {
    // constructor must call super
    Dog(string n) : super(n) {}

    // override a method
    string speak() {
        return "woof";
    }
}
```

- `super(args)` calls the parent constructor and must be the first thing in a subclass constructor body
- All methods are virtual by default — dispatch is always through the vtable
- No `override` keyword required, but a method with the same signature as a parent method silently overrides it
- A subclass can call a parent method explicitly: `super.speak()`
- No multiple inheritance of classes

### 9.8 Vtable

Every class has a vtable. The vtable stores pointers to all virtual methods (all instance methods) and the destructor. This is handled entirely by the runtime — user code does not interact with vtables directly.

### 9.9 No access modifiers

All fields and methods are public in v1. A future version may add `private` and `protected`.

### 9.10 No abstract classes

Declare an interface instead.

---

## 10. Interfaces

### 10.1 Declaration

```c
interface Printable {
    string toString();
}

interface Comparable {
    int compareTo(Comparable* other);
}
```

Interface bodies contain method signatures only — no fields, no static members, no default implementations.

### 10.2 Implementation

```c
class Dog extends Animal implements Printable, Comparable {
    string toString() {
        return this.name;
    }

    int compareTo(Comparable* other) {
        // ...
    }
}
```

- A class may implement multiple interfaces
- All methods declared in every implemented interface must be present — missing implementations are a compile error
- Interface pointer types are valid: `Printable* p = new Dog("Rex");`
- Calling a method through an interface pointer dispatches via vtable

---

## 11. Enums

### 11.1 Declaration

```
enum Direction { NORTH, EAST, SOUTH, WEST }
enum HttpStatus { OK = 200, NOT_FOUND = 404, SERVER_ERROR = 500 }
```

Variants are listed inside `{ }`, separated by commas. Each variant may optionally carry an explicit integer value with `= N`; otherwise it takes the value of the previous variant plus one (or 0 for the first variant).

### 11.2 Type rules

- An enum type is a distinct type. It is not interchangeable with `int` or any other enum without an explicit cast.
- `Color c = Color.RED;` — correct.
- `int n = Color.RED;` — type error.
- `Color c = 0;` — type error.

### 11.3 Variant access

Variants are accessed via `EnumName.VariantName`:

```
Direction d = Direction.NORTH;
HttpStatus s = HttpStatus.NOT_FOUND;
```

### 11.4 Comparisons

Enum values support `==` and `!=`:

```
if (d == Direction.SOUTH) { ... }
```

### 11.5 Casting

Cast to `int` to read the underlying ordinal; cast from `int` to convert a runtime integer back to an enum type:

```
int code = (int) HttpStatus.NOT_FOUND;   // 404
HttpStatus s = (HttpStatus) 500;         // SERVER_ERROR
```

---

## 12. Scope & Lifetime

### 12.1 Block scoping

Variables are visible from their declaration to the end of the enclosing `{}` block. There is no hoisting.

```c
int x = 1;
{
    int x = 2;   // shadows outer x — compiler warning
    // inner x freed here
}
// outer x = 1
```

Shadowing is allowed but generates a compiler warning.

### 12.2 Stack lifetime

Stack variables are destroyed in reverse declaration order when their scope exits. If a class has a destructor, it is called.

### 12.3 Heap lifetime

Heap objects live until explicitly freed with `delete` or `free`. The compiler does not track heap lifetimes.

---

## 13. Modules

### 13.1 Import

```c
import "path/to/file.lang";
```

Importing a file makes all top-level declarations in that file visible in the current file. Import paths are relative to the source file. Circular imports are a compile error. Duplicate imports are silently ignored (include-guard semantics).

An import path beginning with `std/` is resolved against the bundled standard-library directory (`stdlib/`) instead of the importing file's directory, regardless of the current working directory:

```c
import "std/list.lang";   // resolves to <project>/stdlib/list.lang
import "std/math.lang";
```

### 13.2 Namespaces

Top-level declarations — functions, classes, interfaces, enums, and nested
namespaces — may be grouped in a `namespace` block. Members are referenced
from outside with the qualified `ns::name` form:

```c
namespace geo {
    class Point {
        int x;
        Point(int x) { this.x = x; }
    }
    int getX(Point p) { return p.x; }   // sibling reference needs no prefix
}

int main() {
    geo::Point p = geo::Point(7);
    return geo::getX(p);
}
```

Resolution rules:

- Inside a namespace, an unqualified name is looked up in the enclosing
  namespaces innermost-first, then falls back to the global scope and the
  builtins. Local variables and parameters always shadow namespace members.
- Outside a namespace, members must be fully qualified (`math::abs(x)`).
  There is no `using` import (yet).
- Qualified names work everywhere a name does: types (`geo::Point* p`),
  construction (`new geo::Point(7)`), casts (`(traffic::Light)1`), enum
  variants (`traffic::Light.GREEN`), static members (`cfg::Defaults.get()`),
  generics (`col::Pair<int>`), `extends`/`implements` clauses, and function
  references (`fn(int) -> int f = math::twice;`).
- Re-declaring a namespace extends it — in the same file or another file —
  so a namespace can span multiple modules. Duplicate *members* remain a
  compile error.
- `namespace a::b { ... }` is shorthand for nesting `b` inside `a`.

Namespaces compile away before type checking: every member becomes an
ordinary top-level declaration whose name carries the prefix, so the rest of
the pipeline (and error messages) see plain qualified names like `math::abs`.

---

## 14. Entry Point

Every program must define exactly one `main` function:

```c
int main() {
    // ...
    return 0;
}
```

The return value is the process exit code. `0` means success. No command-line argument support in v1.

---

## 15. Memory-safety violations

These operations are programming errors. The language does not define a way to
recover from them.

**Checked by the reference interpreter** — it detects these and aborts with a
runtime error (a `RuntimeError` diagnostic) rather than continuing:

- Dereferencing a null pointer
- Dereferencing a freed pointer (use-after-free)
- Out-of-bounds array access
- Calling `delete` (or `free`) twice on the same pointer
- `free` of a pointer that was not heap-allocated
- Division or modulo by zero

**Undefined behaviour** — not detected; results are unspecified:

- Reading an uninitialised `alloc`'d value (the interpreter zero-fills, but
  programs must not rely on this)
- Integer overflow (wraps on most platforms, but not guaranteed)
- Casting to an incompatible pointer type and dereferencing

> **Direction:** the reference interpreter favours fail-fast safety, so most of
> the classic C hazards above are *checked* rather than silently undefined. A
> future optimising or native backend may downgrade some checked cases to true
> undefined behaviour for performance; portable programs should not depend on
> either the check firing or on a particular post-violation result.

---

## 16. Future Work

Since v1, the following have shipped: `const`, access modifiers, string
operations, the import system (with a `std/` prefix), function pointers,
closures, operator overloading, sized `alloc(T, n)` with pointer indexing,
file-I/O built-ins, **generics** (monomorphized) with a generic standard
library, the `byte` primitive with `byte[]` blocks and `string`/`byte` interop,
the non-owning `Span<T>` / owning `MemoryOwner<T>` memory views, and
**namespaces** (section 13.2) with a namespaced standard library. The
remaining items reserved for later versions:

| Feature              | Notes                                              |
|----------------------|----------------------------------------------------|
| Generic bounds       | `<T extends Comparable>` — type params are unconstrained today |
| Generic type inference | Generic *function* calls need explicit `f<int>(x)` for now |
| `using` declarations | Namespace members must be fully qualified outside their namespace |
| Exceptions           | Error handling via return values for now           |
| Garbage collection   | Planned as a pure-Glang standard-library module    |
| Command-line args    | `main(int argc, string[] argv)` — the `getArgCount`/`getArg` builtins cover this meanwhile |
| Variadic functions   | Needed for printf-style stdlib functions           |

---

## 17. Standard Library

The bundled standard library lives in `stdlib/` and is imported with the `std/`
prefix (e.g. `import "std/list.lang";`). The file-I/O built-ins (`readFile`,
`writeFile`, `fileExists`) are part of the runtime and need no import.

The function modules are wrapped in namespaces — `math`, `chars`, `strings`,
`io` (the latter three pluralised or shortened because `char` and `string` are
type keywords) — so their members are called as `math::abs(x)`,
`chars::isDigit(c)`, and so on. The collection classes remain global.

| Module            | Provides                                                                 |
|-------------------|--------------------------------------------------------------------------|
| `std/math.lang`   | `math::` — `abs`, `fabs`, `min`/`max`, `fmin`/`fmax`, `clamp`, `sign`, `ipow`, `gcd`, `lcm`, `isqrt`, `factorial` |
| `std/char.lang`   | `chars::` — `isDigit`/`isAlpha`/`isAlnum`/`isSpace`/`isUpper`/`isLower`, `toUpper`/`toLower`, `digitToInt` |
| `std/string.lang` | `strings::` — `toUpperStr`/`toLowerStr`, `reverse`, `repeat`, `trim`, `padLeft`, `count`, `replaceChar`, `equalsIgnoreCase` |
| `std/io.lang`     | `io::` — `appendFile`, `readLineCount`, `dieWith` (built on the I/O built-ins) |
| `std/list.lang`   | `List<T>` — growable list: `add`, `get`, `set`, `contains`, `removeAt`, `length`, `isEmpty`, `clear` |
| `std/stack.lang`  | `Stack<T>` — `push`, `pop`, `peek`, `length`, `isEmpty`                   |
| `std/queue.lang`  | `Queue<T>` — ring buffer: `enqueue`, `dequeue`, `peek`, `length`, `isEmpty` |
| `std/map.lang`    | `Map<K,V>` — association map: `set`, `getOr`, `has`, `remove`, `length`  |
| `std/option.lang` | `Option<T>` — `setSome`/`setNone`, `isSome`/`isNone`, `get`, `getOr`      |
| `std/span.lang`   | `Span<T>` — non-owning bounds-checked view: `get`, `set`, `slice`, `length`, `isEmpty` |
| `std/memory.lang` | `MemoryOwner<T>` — owning heap block: `get`, `set`, `span`, `length`, `dispose` (frees; also `~MemoryOwner` on `delete`) |

The collections are growable and generic: each one is backed by a contiguous
`alloc(T, cap)` block that doubles when full. The map uses linear search, so it
works for any key type that supports `==` (a hashed map awaits a generic hashing
mechanism).

```c
import "std/list.lang";

int main() {
    List<int> xs = List<int>();
    xs.add(10);
    xs.add(20);
    print(xs.get(1));   // 20
    return 0;
}
```

**Contiguous memory: `MemoryOwner<T>` and `Span<T>`.** A `MemoryOwner<T>` owns a
heap block (`alloc(T, n)`) and frees it when released; a `Span<T>` is a
non-owning, bounds-checked view (`pointer + offset + length`) over a block.
`slice` produces zero-copy sub-views that alias the same storage. Because Glang
has no scope-exit cleanup, freeing is explicit: call `dispose()` on a value
handle, or `delete` a `new`'d handle (which runs `~MemoryOwner`). Do not do both
on the same owner (double free). A span is valid only while its backing owner
is live.

```c
import "std/memory.lang";

int main() {
    MemoryOwner<int> o = MemoryOwner<int>(8);
    for (int i = 0; i < 8; ++i) { o.set(i, i * 10); }

    Span<int> mid = o.span().slice(2, 6);  // view of o[2..6)
    print(mid.get(0));                     // 20
    mid.set(0, 999);                       // aliases the backing block
    print(o.get(2));                       // 999

    o.dispose();                           // free the block
    return 0;
}
```

---

## 18. Running Programs and Examples

```bash
# Run a program
python3 main.py run path/to/program.lang

# Run all unit tests
python3 -m pytest tests/ -v
```

Runnable example programs live in `examples/`, each paired with a golden-output
file under `examples/expected/<name>.expected`. Two harnesses run them — both
separate from the unit tests:

```bash
# Standalone runner: executes every example and diffs stdout against its golden
python3 examples/run_examples.py
python3 examples/run_examples.py --generate   # rewrite the golden files

# The same examples under pytest
python3 -m pytest tests/test_examples.py -v
```
