import type { Lesson } from '../../types.ts'

export default {
  id: 'defining-classes',
  title: 'Defining Classes',
  blurb: 'Bundle data and behaviour together: fields, constructors, destructors, methods, and `this`.',
  blocks: [
    {
      type: 'prose',
      md: `A **class** groups related data (fields) with the functions that operate on it (methods). You declare one with the \`class\` keyword and a brace-delimited body.

> The in-browser interpreter does **not** run classes, \`new\`, or \`delete\`. Every program on this page is a read-only \`static\` sample with its output shown beneath it — hand-trace them and predict-the-output exercises check your understanding.`,
    },
    {
      type: 'prose',
      md: `### Fields

**Instance fields** are declared at the top of the class body with their type. Each object gets its own copy. **Static fields** use the \`static\` keyword and **must** have an initialiser — there is one shared copy for the whole class.

All fields are **public** in v1.`,
    },
    {
      type: 'static',
      caption: 'animal.lang',
      code: `class Animal {
    string name;     // instance field
    int legs;        // instance field

    Animal(string n, int l) {   // constructor: same name as the class, no return type
        this.name = n;
        this.legs = l;
    }

    string describe() {         // instance method
        return this.name;
    }
}

int main() {
    Animal* a = new Animal("cat", 4);
    print(a->describe());
    print(a->legs);
    delete a;
    return 0;
}`,
      output: `cat
4`,
    },
    {
      type: 'prose',
      md: `### Constructors

A **constructor** has the *same name as the class* and *no return type*. You invoke it with **\`new ClassName(args)\`**, which allocates an object on the heap and returns a pointer (\`Animal*\`). Inside the constructor you initialise fields through \`this\`.

Because \`new\` gives back a pointer, you reach members with the arrow operator \`->\` (e.g. \`a->legs\`, \`a->describe()\`), and you release the object with \`delete\` when you are done.`,
    },
    {
      type: 'prose',
      md: `### \`this\` is a pointer

Inside any instance method or constructor, \`this\` is a **pointer to the current instance**. Read and write fields with \`this.name\`, and call sibling methods with \`this.method()\`.`,
    },
    {
      type: 'callout',
      tone: 'note',
      md: `**Default constructor.** A class with *no* explicit constructor automatically gets a zero-argument default constructor that **zero-initialises every field** (\`0\`, \`0.0\`, \`false\`, \`'\\0'\`, \`""\`/null as appropriate). The moment you write *any* explicit constructor, that free default disappears — you must call one of the constructors you declared.`,
    },
    {
      type: 'static',
      caption: 'default_ctor.lang',
      code: `class Point {
    int x;
    int y;
    // no constructor declared -> zero-arg default that zero-inits fields
}

int main() {
    Point* p = new Point();
    print(p->x);
    print(p->y);
    delete p;
    return 0;
}`,
      output: `0
0`,
    },
    {
      type: 'prose',
      md: `### Static members

Static fields and static methods belong to the *class*, not to any instance, so you access them through the class name: \`ClassName.member\`. A static method has no \`this\`. Below, a shared \`Counter.total\` is bumped each time a \`Counter\` is constructed.`,
    },
    {
      type: 'static',
      caption: 'counter.lang',
      code: `class Counter {
    static int total = 0;   // static field — needs an initialiser

    Counter() {
        Counter.total += 1; // static field reached via the class name
    }

    static int count() {    // static method — no access to \`this\`
        return Counter.total;
    }
}

int main() {
    Counter* a = new Counter();
    Counter* b = new Counter();
    print(Counter.count());
    delete a;
    delete b;
    return 0;
}`,
      output: `2`,
    },
    {
      type: 'callout',
      tone: 'gotcha',
      md: `Static members are reached **only** through the class name — \`Counter.total\`, never \`a.total\` or \`a->total\`. Instance members are reached through an object — \`this.name\` inside the class, \`a->name\` through a pointer outside it.`,
    },
    {
      type: 'prose',
      md: `### Destructors

A **destructor** is named \`~ClassName()\` — no parameters, no return type. It runs automatically when you \`delete\` the object, and is the place to release any resources the object owns. A class with no explicit destructor gets a no-op one for free.`,
    },
    {
      type: 'exercise',
      ex: {
        id: 'defining-classes-ex1',
        difficulty: 'easy',
        prompt: `**Predict the output.** Trace the program and type exactly what it prints.`,
        code: `class Box {
    int w;
    int h;

    Box(int w, int h) {
        this.w = w;
        this.h = h;
    }

    int area() {
        return this.w * this.h;
    }
}

int main() {
    Box* b = new Box(3, 5);
    print(b->w);
    print(b->area());
    delete b;
    return 0;
}`,
        check: {
          kind: 'predict',
          expected: `3
15`,
        },
        hints: [
          'The constructor stores `w = 3` and `h = 5` through `this`.',
          '`area()` returns `this.w * this.h`, i.e. `3 * 5`.',
        ],
      },
    },
    {
      type: 'exercise',
      ex: {
        id: 'defining-classes-ex2',
        difficulty: 'medium',
        prompt: `**Predict the output.** A static field is shared across every instance. Type exactly what this prints.`,
        code: `class Robot {
    static int built = 0;
    int id;

    Robot() {
        Robot.built += 1;
        this.id = Robot.built;
    }
}

int main() {
    Robot* r1 = new Robot();
    Robot* r2 = new Robot();
    Robot* r3 = new Robot();
    print(r1->id);
    print(r3->id);
    print(Robot.built);
    delete r1;
    delete r2;
    delete r3;
    return 0;
}`,
        check: {
          kind: 'predict',
          expected: `1
3
3`,
        },
        hints: [
          '`Robot.built` is shared and increments to 1, then 2, then 3 as each robot is built.',
          'Each robot copies the *current* `built` into its own `id`: r1 gets 1, r2 gets 2, r3 gets 3.',
        ],
      },
    },
  ],
} satisfies Lesson
