import type { Lesson } from '../../types.ts'

export default {
  id: 'defining-functions',
  title: 'Defining Functions',
  blurb: 'Declare reusable functions with required return and parameter types.',
  blocks: [
    {
      type: 'prose',
      md: `A function packages a piece of behaviour behind a name you can call. In Glang every function declares its **return type** first, then its name, then a parenthesised list of **typed parameters**, then a body in braces:

\`\`\`
<return-type> name(<type> p1, <type> p2, ...) { ... }
\`\`\`

Both the return type and every parameter type are **required** — Glang never guesses them. A function that returns nothing uses the return type \`void\`.`,
    },
    {
      type: 'run',
      caption: 'add.lang',
      code: `int add(int a, int b) {
    return a + b;
}

int main() {
    int sum = add(40, 2);
    print(sum);
    return 0;
}`,
    },
    {
      type: 'prose',
      md: `You **call** a function by writing its name followed by arguments in parentheses. The arguments are matched to the parameters by position, and each must have the matching type. The call \`add(40, 2)\` evaluates to \`42\`, which we store in \`sum\` and print.

A \`void\` function does work but yields no value, so you call it as its own statement rather than assigning its result.`,
    },
    {
      type: 'run',
      caption: 'greet.lang',
      code: `void greet(string name) {
    print("Hello, " + name + "!");
}

int main() {
    greet("Ada");
    greet("Linus");
    return 0;
}`,
    },
    {
      type: 'callout',
      tone: 'note',
      md: `Glang has **no default parameter values** and **no overloading** — each function name must be unique within its scope. You cannot declare two functions both named \`add\`. If you need a variant, give it a different name (for example \`addThree\`).`,
    },
    {
      type: 'callout',
      tone: 'gotcha',
      md: `A non-\`void\` function must \`return\` a value of its declared type on every path. \`return a + b;\` in \`add\` hands back an \`int\`; forgetting it (or returning the wrong type) is a compile error.`,
    },
    {
      type: 'exercise',
      ex: {
        id: 'defining-functions-ex1',
        difficulty: 'easy',
        prompt: `Write a function \`int square(int n)\` that returns \`n * n\`, then print \`square(9)\` from \`main\`.

Expected output:

\`\`\`
81
\`\`\``,
        starter: `int square(int n) {
    // return n * n
}

int main() {
    // print square(9)
    return 0;
}`,
        check: {
          kind: 'output',
          expected: '81',
        },
        hints: [
          'The body is just `return n * n;`.',
          'Call it inside `print(...)`: `print(square(9));`.',
        ],
        solution: `int square(int n) {
    return n * n;
}

int main() {
    print(square(9));
    return 0;
}`,
      },
    },
    {
      type: 'exercise',
      ex: {
        id: 'defining-functions-ex2',
        difficulty: 'easy',
        prompt: `**Predict the output.** Read the program and type exactly what it prints.`,
        code: `int twice(int x) {
    return x + x;
}

int main() {
    print(twice(5));
    print(twice(twice(3)));
    return 0;
}`,
        check: {
          kind: 'predict',
          expected: '10\n12',
        },
        hints: [
          '`twice(5)` is `5 + 5`.',
          'For the second line, evaluate the inner call first: `twice(3)` is `6`, then `twice(6)`.',
        ],
      },
    },
  ],
} satisfies Lesson
