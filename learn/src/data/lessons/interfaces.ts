import type { Lesson } from '../../types.ts'

export default {
  id: 'interfaces',
  title: 'Interfaces',
  blurb: 'Declare a contract of method signatures, implement it on a class, and dispatch through an interface pointer.',
  blocks: [
    {
      type: 'prose',
      md: `An **interface** is a named contract: a list of method *signatures* with no bodies. A class promises to satisfy the contract with the **\`implements\`** keyword, and the compiler checks that every required method is actually present.

Interfaces let you write code that works against a capability ("anything I can print") instead of a concrete class.`,
    },
    {
      type: 'prose',
      md: `### Declaring an interface

An interface body contains **method signatures only**. No fields, no \`static\` members, no default implementations — just the shapes of the methods an implementer must provide.`,
    },
    {
      type: 'static',
      caption: 'shapes.lang',
      code: `interface Printable {
    string toString();
}

interface Comparable {
    int compareTo(Comparable* other);
}`,
      output: '',
    },
    {
      type: 'callout',
      tone: 'note',
      md: `An interface declaration produces no output on its own — it only describes a contract. Notice that \`compareTo\` takes a \`Comparable*\`: an interface name is a valid type, and a pointer to it is the idiomatic way to pass "some implementer" around.`,
    },
    {
      type: 'prose',
      md: `### Implementing interfaces

A class lists the interfaces it satisfies after \`implements\`, separated by commas. It may also \`extends\` a base class at the same time — \`extends\` comes first, then \`implements\`.

A class may implement **multiple** interfaces. Every method declared in **every** implemented interface must appear in the class, or the program fails to compile.`,
    },
    {
      type: 'static',
      caption: 'dog.lang',
      code: `interface Printable {
    string toString();
}

interface Comparable {
    int compareTo(Comparable* other);
}

class Animal {
    string name;
    Animal(string name) { this.name = name; }
}

class Dog extends Animal implements Printable, Comparable {
    Dog(string name) : Animal(name) {}

    string toString() {
        return this.name;
    }

    int compareTo(Comparable* other) {
        return 0;
    }
}

int main() {
    Dog* d = new Dog("Rex");
    print(d.toString());
    return 0;
}`,
      output: 'Rex',
    },
    {
      type: 'callout',
      tone: 'warn',
      md: `If \`Dog\` declared \`implements Comparable\` but left out \`compareTo\`, that is a **compile error** — "missing implementation". The contract is enforced at compile time, before the program ever runs.`,
    },
    {
      type: 'prose',
      md: `### Interface pointer types and vtable dispatch

An interface name is a real type, so a pointer to it — \`Printable*\` — is a valid variable type. You can store a \`new Dog(...)\` in a \`Printable*\` because \`Dog\` implements \`Printable\`.

When you call a method **through an interface pointer**, the call dispatches via the object's **vtable** — it runs the implementer's version, even though the static type is only the interface.`,
    },
    {
      type: 'static',
      caption: 'dispatch.lang',
      code: `interface Printable {
    string toString();
}

class Dog implements Printable {
    string name;
    Dog(string name) { this.name = name; }
    string toString() { return "Dog(" + this.name + ")"; }
}

class Cat implements Printable {
    string name;
    Cat(string name) { this.name = name; }
    string toString() { return "Cat(" + this.name + ")"; }
}

void announce(Printable* p) {
    print(p.toString());
}

int main() {
    Printable* a = new Dog("Rex");
    Printable* b = new Cat("Mittens");
    announce(a);
    announce(b);
    return 0;
}`,
      output: 'Dog(Rex)\nCat(Mittens)',
    },
    {
      type: 'callout',
      tone: 'tip',
      md: `\`announce\` knows nothing about \`Dog\` or \`Cat\` — only that its argument can \`toString()\`. This is the payoff of interfaces: one function, written once, works for every current and future implementer.`,
    },
    {
      type: 'exercise',
      ex: {
        id: 'interfaces-ex1',
        difficulty: 'easy',
        prompt: `**Predict the output.** Both classes implement \`Greeter\`, and the calls go through \`Greeter*\` variables, so dispatch is by the real object type. Type exactly what this prints.`,
        code: `interface Greeter {
    string greet();
}

class English implements Greeter {
    string greet() { return "Hello"; }
}

class French implements Greeter {
    string greet() { return "Bonjour"; }
}

int main() {
    Greeter* g1 = new English();
    Greeter* g2 = new French();
    print(g1.greet());
    print(g2.greet());
    return 0;
}`,
        check: {
          kind: 'predict',
          expected: 'Hello\nBonjour',
        },
        hints: [
          'A call through a `Greeter*` dispatches via vtable to the actual object stored in it.',
          '`g1` holds an `English`, `g2` holds a `French`.',
        ],
      },
    },
    {
      type: 'exercise',
      ex: {
        id: 'interfaces-ex2',
        difficulty: 'medium',
        prompt: `**Predict the output.** \`Counter\` implements two interfaces, \`Sized\` and \`Named\`. The same object is viewed through both interface pointer types. Type exactly what this prints.`,
        code: `interface Sized {
    int size();
}

interface Named {
    string label();
}

class Box implements Sized, Named {
    int n;
    Box(int n) { this.n = n; }
    int size() { return this.n; }
    string label() { return "box"; }
}

int main() {
    Box* b = new Box(7);
    Sized* s = b;
    Named* nm = b;
    print(s.size());
    print(nm.label());
    print(s.size() + 3);
    return 0;
}`,
        check: {
          kind: 'predict',
          expected: '7\nbox\n10',
        },
        hints: [
          'One object can be referred to through several interface pointers at once.',
          '`s.size()` returns `7`, so `s.size() + 3` is `10`.',
        ],
      },
    },
  ],
} satisfies Lesson
