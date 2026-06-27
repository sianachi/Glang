import type { Lesson } from '../../types.ts'

export default {
  id: 'function-pointers',
  title: 'Function Pointers & Closures',
  blurb: 'Treat functions as values: store them, pass them, and capture state with closures.',
  blocks: [
    {
      type: 'prose',
      md: `Glang lets you treat a function as a **value**. A function-pointer type is written \`fn(<param-types>) -> <return-type>\`. For example, \`fn(int) -> int\` is "a function taking one \`int\` and returning an \`int\`", and \`fn(int, int) -> int\` takes two \`int\`s.

You can store a named function in a variable of the matching type and call it through that variable just like any function.`,
    },
    {
      type: 'callout',
      tone: 'note',
      md: `Function pointers and closures compile to C in the real toolchain but are **outside the in-browser interpreter's subset**, so the programs on this page are shown with their expected output rather than executed live.`,
    },
    {
      type: 'static',
      caption: 'fnptr.lang',
      code: `int add(int a, int b) {
    return a + b;
}

int multiply(int a, int b) {
    return a * b;
}

int main() {
    fn(int, int) -> int op = add;
    print(op(40, 2));      // calls add
    op = multiply;
    print(op(6, 7));       // calls multiply
    return 0;
}`,
      output: `42
42`,
    },
    {
      type: 'prose',
      md: `Because a function pointer is just a value, you can pass one as a **parameter**. This is the essence of a *higher-order function* — a function that takes another function. Here \`apply\` doesn't know or care which transformation it runs; the caller supplies it.`,
    },
    {
      type: 'static',
      caption: 'higher_order.lang',
      code: `int apply(fn(int) -> int f, int x) {
    return f(x);
}

int inc(int n) {
    return n + 1;
}

int main() {
    print(apply(inc, 41));   // 42
    return 0;
}`,
      output: `42`,
    },
    {
      type: 'prose',
      md: `### Lambdas

You don't need a named function to make a callable value. A **lambda** (anonymous function) is written with a typed parameter list, \`->\`, the return type, and a braced body:

\`\`\`
(int x) -> int { return x + 1; }
\`\`\`

This expression has type \`fn(int) -> int\`, so you can assign it to a variable, pass it to \`apply\`, or call it on the spot.`,
    },
    {
      type: 'static',
      caption: 'lambda.lang',
      code: `int apply(fn(int) -> int f, int x) {
    return f(x);
}

int main() {
    fn(int) -> int square = (int x) -> int { return x * x; };
    print(square(9));                                  // 81
    print(apply((int x) -> int { return x + 1; }, 41)); // 42
    return 0;
}`,
      output: `81
42`,
    },
    {
      type: 'prose',
      md: `### Closures capture variables

A lambda can refer to variables from the surrounding scope. When it does, it **captures** them — the value is bundled into the closure and stays available even after the enclosing function returns. The factory \`make_bonus\` below returns a closure that remembers its \`bonus\` argument.`,
    },
    {
      type: 'static',
      caption: 'closure.lang',
      code: `fn(int) -> int make_bonus(int bonus) {
    return (int score) -> int {
        return score + bonus;   // captures bonus
    };
}

int main() {
    fn(int) -> int plus5 = make_bonus(5);
    fn(int) -> int plus100 = make_bonus(100);
    print(plus5(10));      // 15
    print(plus100(10));    // 110
    print((make_bonus(12))(30));  // 42, called directly
    return 0;
}`,
      output: `15
110
42`,
    },
    {
      type: 'callout',
      tone: 'gotcha',
      md: `Captured variables are taken **by value** at the time the closure is created. If you build a filter from \`fn(int) -> bool keep = make_minimum_filter(70);\` and later change the original variable, the closure still uses the \`70\` it captured — not the new value.`,
    },
    {
      type: 'callout',
      tone: 'tip',
      md: `Lambdas returning \`bool\` (type \`fn(T) -> bool\`) are the workhorse of predicate-style APIs. The standard library's \`std/linq.lang\` uses exactly this shape: \`nums.where((int x) -> bool { return x % 2 == 0; })\` keeps the even numbers.`,
    },
    {
      type: 'exercise',
      ex: {
        id: 'function-pointers-ex1',
        difficulty: 'medium',
        prompt: `**Predict the output.** The program reassigns a function pointer between calls.

\`\`\`
(read the code, then type the exact output)
\`\`\``,
        code: `int twice(int n) {
    return n * 2;
}

int negate(int n) {
    return -n;
}

int apply(fn(int) -> int f, int x) {
    return f(x);
}

int main() {
    fn(int) -> int g = twice;
    print(apply(g, 5));    // ?
    g = negate;
    print(apply(g, 5));    // ?
    return 0;
}`,
        check: {
          kind: 'predict',
          expected: '10\n-5',
        },
        hints: [
          'First `g` points at `twice`, so `apply(g, 5)` is `twice(5)`.',
          'After `g = negate;`, the same call runs `negate(5)`.',
        ],
      },
    },
    {
      type: 'exercise',
      ex: {
        id: 'function-pointers-ex2',
        difficulty: 'hard',
        prompt: `**Predict the output.** A closure captures \`step\` by value; the original variable changes afterwards.`,
        code: `fn(int) -> int make_adder(int step) {
    return (int x) -> int {
        return x + step;
    };
}

int main() {
    int step = 3;
    fn(int) -> int addStep = make_adder(step);
    step = 100;                 // does NOT affect the closure
    print(addStep(10));         // ?
    print(make_adder(7)(10));   // ?
    return 0;
}`,
        check: {
          kind: 'predict',
          expected: '13\n17',
        },
        hints: [
          '`addStep` captured `step` when it was `3`; reassigning `step` to `100` later has no effect on it.',
          '`make_adder(7)` builds a fresh closure capturing `7`, then immediately called on `10`.',
        ],
      },
    },
  ],
} satisfies Lesson
