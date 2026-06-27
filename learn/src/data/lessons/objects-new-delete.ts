import type { Lesson } from '../../types.ts'

export default {
  id: 'objects-new-delete',
  title: 'Objects: new & delete',
  blurb: 'Heap-allocating objects with new, releasing them with delete, and who owns what.',
  blocks: [
    {
      type: 'prose',
      md: `Objects in Glang are **always heap-allocated**. You never get an object on the stack — you create one with \`new\`, which returns a pointer, and you release it with \`delete\`.

> \`new\`, \`delete\`, and method calls cannot run in the in-browser sandbox, so the programs here are read-only samples with their output shown. Trace each one to follow the constructor/destructor calls.`,
    },
    {
      type: 'prose',
      md: `## new and delete

- \`new Dog("Rex")\` allocates a \`Dog\` on the heap, runs its **constructor**, and returns a \`Dog*\`.
- \`delete d\` runs the object's **destructor**, then frees the memory.

The pair mirrors \`alloc\`/\`free\`, but with the constructor and destructor wired in.`,
    },
    {
      type: 'static',
      caption: 'dog.lang',
      code: `class Dog {
    string name;
    Dog(string n) {
        this.name = n;
        print("ctor: " + n);
    }
    ~Dog() {
        print("dtor: " + this.name);
    }
    void speak() {
        print(this.name + " says woof");
    }
}

int main() {
    Dog* d = new Dog("Rex");   // allocate + run constructor
    d->speak();                // call through the pointer with ->
    delete d;                  // run destructor, then free
    return 0;
}`,
      output: `ctor: Rex
Rex says woof
dtor: Rex`,
    },
    {
      type: 'callout',
      tone: 'note',
      md: `Because an object is reached through a pointer, you call its methods with the arrow operator \`->\` (\`d->speak()\`), the same way you dereference a struct pointer in C. \`delete\` is the only thing that frees the object — letting the pointer go out of scope does **not** free it.`,
    },
    {
      type: 'prose',
      md: `## delete on null is a no-op

\`delete\` quietly does nothing when handed \`null\`. That means you do not need to guard \`delete\` with a null check — it is always safe to call.`,
    },
    {
      type: 'static',
      caption: 'null_delete.lang',
      code: `class Box {
    Box() { print("ctor"); }
    ~Box() { print("dtor"); }
}

int main() {
    Box* b = null;
    delete b;          // no-op: nothing constructed, nothing freed
    print("done");
    return 0;
}`,
      output: `done`,
    },
    {
      type: 'prose',
      md: `## Destructor chaining

When you \`delete\` a subclass instance **through a base-class pointer**, the destructors run from the most-derived class up to the base: the subclass destructor first, then the base destructor. This works because the destructor is stored in the vtable, so \`delete\` finds the real runtime type.`,
    },
    {
      type: 'static',
      caption: 'chaining.lang',
      code: `class Animal {
    Animal() { print("Animal ctor"); }
    ~Animal() { print("~Animal"); }
}

class Dog : Animal {
    Dog() { print("Dog ctor"); }
    ~Dog() { print("~Dog"); }
}

int main() {
    Animal* a = new Dog();   // base pointer, derived object
    delete a;                // ~Dog() runs first, then ~Animal()
    return 0;
}`,
      output: `Animal ctor
Dog ctor
~Dog
~Animal`,
    },
    {
      type: 'callout',
      tone: 'tip',
      md: `Note the symmetry: construction builds **base-first** (\`Animal\` then \`Dog\`), and destruction tears down **derived-first** (\`~Dog\` then \`~Animal\`). A subclass is fully built on top of its base, and torn down before its base is dismantled.`,
    },
    {
      type: 'prose',
      md: `## Ownership

Glang does **not** track ownership for you. The convention is simple:

- **The caller that calls \`new\` owns the object** and is responsible for the matching \`delete\`.
- A function that merely *receives* a pointer does **not** own it — it must not \`delete\` it unless the API explicitly says so.
- The standard library provides owning wrapper types for cases where you want cleanup handled automatically.

Following this convention keeps every \`new\` paired with exactly one \`delete\`.`,
    },
    {
      type: 'static',
      caption: 'ownership.lang',
      code: `class Counter {
    int n;
    Counter() { this.n = 0; }
    ~Counter() { print("freed at " + toString(this.n)); }
    void bump() { this.n += 1; }
}

// receives a pointer it does NOT own — never deletes it
void useTwice(Counter* c) {
    c->bump();
    c->bump();
}

int main() {
    Counter* c = new Counter();   // main owns c
    useTwice(c);
    print(c->n);
    delete c;                     // main, the owner, frees it
    return 0;
}`,
      output: `2
freed at 2`,
    },
    {
      type: 'exercise',
      ex: {
        id: 'objects-new-delete-ex1',
        difficulty: 'medium',
        prompt: `**Predict the output.** Trace the constructor, the method call, and the destructor in order.`,
        code: `class Greeter {
    string who;
    Greeter(string w) {
        this.who = w;
        print("hi " + w);
    }
    ~Greeter() {
        print("bye " + this.who);
    }
    void shout() {
        print(this.who + "!");
    }
}

int main() {
    Greeter* g = new Greeter("Ada");
    g->shout();
    delete g;
    return 0;
}`,
        check: {
          kind: 'predict',
          expected: 'hi Ada\nAda!\nbye Ada',
        },
        hints: [
          'The constructor prints first, when `new` runs.',
          '`delete` runs the destructor last.',
        ],
      },
    },
    {
      type: 'exercise',
      ex: {
        id: 'objects-new-delete-ex2',
        difficulty: 'hard',
        prompt: `**Predict the output.** A derived object is deleted through a base pointer, and a separate \`null\` pointer is also deleted.`,
        code: `class Base {
    Base() { print("Base()"); }
    ~Base() { print("~Base()"); }
}

class Mid : Base {
    Mid() { print("Mid()"); }
    ~Mid() { print("~Mid()"); }
}

int main() {
    Base* p = new Mid();
    Base* q = null;
    delete q;          // no-op
    delete p;          // chains: ~Mid() then ~Base()
    print("end");
    return 0;
}`,
        check: {
          kind: 'predict',
          expected: 'Base()\nMid()\n~Mid()\n~Base()\nend',
        },
        hints: [
          'Construction is base-first: `Base()` then `Mid()`.',
          '`delete q` does nothing because `q` is `null`. `delete p` tears down derived-first: `~Mid()` then `~Base()`.',
        ],
      },
    },
  ],
} satisfies Lesson
