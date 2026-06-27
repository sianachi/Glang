import type { Lesson } from '../../types.ts'

export default {
  id: 'inheritance',
  title: 'Inheritance',
  blurb: 'Build a class on top of another with `extends`, `super`, and virtual method dispatch.',
  blocks: [
    {
      type: 'prose',
      md: `A class can **extend** exactly one other class, inheriting its fields and methods and adding or replacing behaviour. Glang supports **single inheritance only** — there is no multiple inheritance of classes.

> Classes are not runnable in the in-browser interpreter, so every program here is a read-only \`static\` sample with its output shown beneath it.`,
    },
    {
      type: 'prose',
      md: `### \`extends\` and \`super(...)\`

Write \`class Dog extends Animal\` to make \`Dog\` a subclass of \`Animal\`. A subclass constructor must hand the base class its arguments through **\`super(args)\`**, written in the constructor header after a colon. The super call runs the parent constructor *before* the subclass body.`,
    },
    {
      type: 'static',
      caption: 'inheritance.lang',
      code: `class Animal {
    string name;

    Animal(string n) {
        this.name = n;
    }

    string speak() {
        return "...";
    }
}

class Dog extends Animal {
    Dog(string n) : super(n) {}   // super(...) initialises the Animal part first

    string speak() {              // same signature -> silently overrides Animal.speak
        return "woof";
    }
}

int main() {
    Animal* a = new Animal("generic");
    Dog*    d = new Dog("Rex");
    print(a->speak());
    print(d->speak());
    print(d->name);   // \`name\` is inherited from Animal
    delete a;
    delete d;
    return 0;
}`,
      output: `...
woof
Rex`,
    },
    {
      type: 'callout',
      tone: 'warn',
      md: `\`super(args)\` **must be the first thing** in a subclass constructor — the base object has to be fully built before the subclass touches its own fields. There is no \`override\` keyword: a method whose signature matches a parent method **silently overrides** it.`,
    },
    {
      type: 'prose',
      md: `### Every method is virtual

All instance methods are **virtual by default** — calls are dispatched through the object's vtable based on its *runtime* type, not the type of the pointer holding it. So a \`Dog\` stored in an \`Animal*\` still speaks like a \`Dog\`. This is polymorphism.`,
    },
    {
      type: 'static',
      caption: 'polymorphism.lang',
      code: `class Animal {
    Animal() {}
    string speak() { return "..."; }
}

class Dog extends Animal {
    Dog() : super() {}
    string speak() { return "woof"; }
}

class Cat extends Animal {
    Cat() : super() {}
    string speak() { return "meow"; }
}

int main() {
    Animal* a = new Dog();   // static type Animal*, runtime type Dog
    Animal* b = new Cat();   // static type Animal*, runtime type Cat
    print(a->speak());       // virtual dispatch -> Dog.speak
    print(b->speak());       // virtual dispatch -> Cat.speak
    delete a;
    delete b;
    return 0;
}`,
      output: `woof
meow`,
    },
    {
      type: 'prose',
      md: `### Calling the parent with \`super.method()\`

An override can still reuse the parent's version by qualifying the call with \`super.\`. This lets a subclass *extend* behaviour rather than fully replace it.`,
    },
    {
      type: 'static',
      caption: 'super_call.lang',
      code: `class Animal {
    Animal() {}
    string speak() { return "(animal)"; }
}

class Parrot extends Animal {
    Parrot() : super() {}
    string speak() {
        return super.speak() + " squawk";  // reuse Animal.speak, then add to it
    }
}

int main() {
    Parrot* p = new Parrot();
    print(p->speak());
    delete p;
    return 0;
}`,
      output: `(animal) squawk`,
    },
    {
      type: 'callout',
      tone: 'tip',
      md: `Destructor chaining is automatic: deleting a subclass runs \`~Subclass()\` and then the base \`~Animal()\` for you, so each layer can clean up what it owns.`,
    },
    {
      type: 'exercise',
      ex: {
        id: 'inheritance-ex1',
        difficulty: 'medium',
        prompt: `**Predict the output.** Watch the runtime types — dispatch is virtual. Type exactly what this prints.`,
        code: `class Shape {
    Shape() {}
    string kind() { return "shape"; }
}

class Circle extends Shape {
    Circle() : super() {}
    string kind() { return "circle"; }
}

class Square extends Shape {
    Square() : super() {}
    string kind() { return "square"; }
}

int main() {
    Shape* a = new Circle();
    Shape* b = new Square();
    Shape* c = new Shape();
    print(a->kind());
    print(b->kind());
    print(c->kind());
    delete a;
    delete b;
    delete c;
    return 0;
}`,
        check: {
          kind: 'predict',
          expected: `circle
square
shape`,
        },
        hints: [
          'Even though all three are held in `Shape*`, dispatch uses the *runtime* type.',
          '`a` is really a `Circle`, `b` a `Square`, `c` a plain `Shape`.',
        ],
      },
    },
    {
      type: 'exercise',
      ex: {
        id: 'inheritance-ex2',
        difficulty: 'medium',
        prompt: `**Predict the output.** The override calls back into the parent with \`super.\`. Type exactly what this prints.`,
        code: `class Greeter {
    Greeter() {}
    string hello() { return "hi"; }
}

class LoudGreeter extends Greeter {
    LoudGreeter() : super() {}
    string hello() {
        return super.hello() + "!!!";
    }
}

int main() {
    Greeter* g = new LoudGreeter();
    print(g->hello());
    delete g;
    return 0;
}`,
        check: {
          kind: 'predict',
          expected: `hi!!!`,
        },
        hints: [
          '`super.hello()` returns the parent result `"hi"`.',
          'The override concatenates `"!!!"` onto it.',
        ],
      },
    },
  ],
} satisfies Lesson
