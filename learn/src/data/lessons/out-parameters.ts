import type { Lesson } from '../../types.ts'

export default {
  id: 'out-parameters',
  title: 'Multiple Returns via Out-Parameters',
  blurb: 'Glang has no tuples — return several values through pointer parameters.',
  blocks: [
    {
      type: 'prose',
      md: `A function can only \`return\` a **single** value, and Glang has **no tuples** to bundle several values together. When you need to produce more than one result, you pass in **pointers** and write the answers through them. These are called *out-parameters*.

A parameter of type \`int*\` is a pointer to an \`int\`. Inside the function, \`*q = ...\` writes to the location the pointer refers to. At the call site, \`&q\` produces the address of the variable \`q\`.`,
    },
    {
      type: 'run',
      caption: 'divmod.lang',
      code: `void divmod(int a, int b, int* q, int* r) {
    *q = a / b;
    *r = a % b;
}

int main() {
    int q = 0;
    int r = 0;
    divmod(17, 5, &q, &r);
    print(q);
    print(r);
    return 0;
}`,
    },
    {
      type: 'prose',
      md: `Trace it through:
- \`q\` and \`r\` start at \`0\`.
- \`&q\` and \`&r\` pass their addresses into \`divmod\`.
- Inside, \`*q = 17 / 5\` stores \`3\` (integer division), and \`*r = 17 % 5\` stores \`2\`.
- Back in \`main\`, the variables now hold those values.

The function itself returns \`void\` — all of its output flows through the pointers.`,
    },
    {
      type: 'callout',
      tone: 'tip',
      md: `Always initialise the variables you pass by address (\`int q = 0;\`). A pointer only gives the function a place to write; the variable still needs a valid starting value in case a path leaves it untouched.`,
    },
    {
      type: 'callout',
      tone: 'gotcha',
      md: `Inside the function you must dereference with \`*q\` to read or write the pointed-to value. Writing \`q = a / b;\` instead would try to reassign the *pointer* itself (a type error), not the \`int\` it points at.`,
    },
    {
      type: 'prose',
      md: `Out-parameters compose naturally with a normal return value: use the return for the "main" result and pointers for the extras. Here \`minmax\` reports both the smaller and larger of two numbers.`,
    },
    {
      type: 'run',
      caption: 'minmax.lang',
      code: `void minmax(int a, int b, int* lo, int* hi) {
    if (a < b) {
        *lo = a;
        *hi = b;
    } else {
        *lo = b;
        *hi = a;
    }
}

int main() {
    int lo = 0;
    int hi = 0;
    minmax(8, 3, &lo, &hi);
    print(lo);
    print(hi);
    return 0;
}`,
    },
    {
      type: 'exercise',
      ex: {
        id: 'out-parameters-ex1',
        difficulty: 'easy',
        prompt: `Write \`void addsub(int a, int b, int* sum, int* diff)\` that stores \`a + b\` through \`sum\` and \`a - b\` through \`diff\`. Call it with \`addsub(10, 4, &s, &d)\` and print \`s\` then \`d\`.

Expected output:

\`\`\`
14
6
\`\`\``,
        starter: `void addsub(int a, int b, int* sum, int* diff) {
    // write a + b through sum, a - b through diff
}

int main() {
    int s = 0;
    int d = 0;
    addsub(10, 4, &s, &d);
    print(s);
    print(d);
    return 0;
}`,
        check: {
          kind: 'output',
          expected: '14\n6',
        },
        hints: [
          'Use `*sum = a + b;` and `*diff = a - b;`.',
          'The call site already passes `&s` and `&d` — you just fill in the body.',
        ],
        solution: `void addsub(int a, int b, int* sum, int* diff) {
    *sum = a + b;
    *diff = a - b;
}

int main() {
    int s = 0;
    int d = 0;
    addsub(10, 4, &s, &d);
    print(s);
    print(d);
    return 0;
}`,
      },
    },
    {
      type: 'exercise',
      ex: {
        id: 'out-parameters-ex2',
        difficulty: 'medium',
        prompt: `**Predict the output.** Read the program and type exactly what it prints.`,
        code: `void swap(int* a, int* b) {
    int tmp = *a;
    *a = *b;
    *b = tmp;
}

int main() {
    int x = 1;
    int y = 9;
    swap(&x, &y);
    print(x);
    print(y);
    return 0;
}`,
        check: {
          kind: 'predict',
          expected: '9\n1',
        },
        hints: [
          '`tmp` saves the original `*a` (which is `x`, i.e. `1`).',
          'After the writes, `x` holds the old `y` and `y` holds the old `x`.',
        ],
      },
    },
  ],
} satisfies Lesson
