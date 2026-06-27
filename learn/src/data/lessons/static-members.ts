import type { Lesson } from '../../types.ts'

export default {
  id: 'static-members',
  title: 'Static Members',
  blurb: 'Class-level state and behaviour: shared static fields, static methods, and the live-instance count pattern.',
  blocks: [
    {
      type: 'prose',
      md: `Most members belong to an *object*: every instance has its own \`name\`, its own \`area\`. **Static** members belong to the *class itself* — there is exactly one copy, shared by every instance and reachable without any object at all.

> Classes are not runnable in the in-browser interpreter, so the programs here are read-only \`static\` samples with their output shown beneath them.`,
    },
    {
      type: 'prose',
      md: `### Static fields

A static field is declared with the \`static\` keyword and **must have an initialiser** — there is no constructor to fall back on, because the field exists before any instance does. It is accessed through the class name, \`ClassName.field\`, both inside and outside the class.`,
    },
    {
      type: 'static',
      caption: 'config.lang',
      code: `class Config {
    static int maxRetries = 3;   // shared, initialised once
}

int main() {
    print(Config.maxRetries);
    Config.maxRetries = 5;       // one shared slot — visible everywhere
    print(Config.maxRetries);
    return 0;
}`,
      output: `3
5`,
    },
    {
      type: 'callout',
      tone: 'gotcha',
      md: `Access static members **only** through the class name — \`Config.maxRetries\`, never \`c.maxRetries\` or \`c->maxRetries\` on an instance. Forgetting the initialiser (\`static int maxRetries;\`) is an error: static fields must be given a starting value.`,
    },
    {
      type: 'prose',
      md: `### Static methods

A static method also belongs to the class. It has **no \`this\`**, so it cannot read instance fields — it works only with its parameters and the class's static fields. You call it as \`ClassName.method(args)\`.`,
    },
    {
      type: 'static',
      caption: 'mathx.lang',
      code: `class MathX {
    static int doubled(int n) {   // no \`this\` — pure class-level helper
        return n * 2;
    }
}

int main() {
    print(MathX.doubled(21));
    return 0;
}`,
      output: `42`,
    },
    {
      type: 'prose',
      md: `### The live-instance count pattern

A classic use of statics is counting how many instances currently exist: bump a shared counter in the **constructor**, and decrement it in the **destructor**. Because \`delete\` runs the destructor, the count tracks live objects exactly.`,
    },
    {
      type: 'static',
      caption: 'widget.lang',
      code: `class Widget {
    static int alive = 0;   // how many Widgets exist right now
    string label;

    Widget(string l) {
        this.label = l;
        Widget.alive += 1;  // one more is alive
    }

    ~Widget() {
        Widget.alive -= 1;  // this one is going away
    }

    static int count() {
        return Widget.alive;
    }
}

int main() {
    Widget* a = new Widget("a");
    Widget* b = new Widget("b");
    print(Widget.count());   // both alive
    delete a;
    print(Widget.count());   // a destroyed
    delete b;
    print(Widget.count());   // none left
    return 0;
}`,
      output: `2
1
0`,
    },
    {
      type: 'callout',
      tone: 'tip',
      md: `The destructor decrement is what keeps the count honest. Pair every \`new\` with a \`delete\` and the live count returns to zero — a handy sanity check that you are not leaking objects.`,
    },
    {
      type: 'exercise',
      ex: {
        id: 'static-members-ex1',
        difficulty: 'easy',
        prompt: `**Predict the output.** Trace the shared counter as objects are created and deleted. Type exactly what this prints.`,
        code: `class Session {
    static int active = 0;

    Session() {
        Session.active += 1;
    }

    ~Session() {
        Session.active -= 1;
    }
}

int main() {
    Session* s1 = new Session();
    Session* s2 = new Session();
    Session* s3 = new Session();
    print(Session.active);
    delete s2;
    print(Session.active);
    delete s1;
    delete s3;
    print(Session.active);
    return 0;
}`,
        check: {
          kind: 'predict',
          expected: `3
2
0`,
        },
        hints: [
          'Each `new Session()` adds 1; each `delete` runs the destructor and subtracts 1.',
          'After three constructions the count is 3; one delete drops it to 2; the last two deletes bring it to 0.',
        ],
      },
    },
    {
      type: 'exercise',
      ex: {
        id: 'static-members-ex2',
        difficulty: 'medium',
        prompt: `**Predict the output.** A static field assigns IDs while a static method reports the running total. Type exactly what this prints.`,
        code: `class Ticket {
    static int next = 1;   // next id to hand out
    int id;

    Ticket() {
        this.id = Ticket.next;
        Ticket.next += 1;
    }

    static int issued() {
        return Ticket.next - 1;
    }
}

int main() {
    Ticket* t1 = new Ticket();
    Ticket* t2 = new Ticket();
    print(t1->id);
    print(t2->id);
    print(Ticket.issued());
    delete t1;
    delete t2;
    return 0;
}`,
        check: {
          kind: 'predict',
          expected: `1
2
2`,
        },
        hints: [
          '`next` starts at 1: t1 takes id 1 (next becomes 2), t2 takes id 2 (next becomes 3).',
          '`issued()` returns `next - 1`, i.e. `3 - 1`.',
        ],
      },
    },
  ],
} satisfies Lesson
