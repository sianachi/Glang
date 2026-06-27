import type { Lesson } from '../../types.ts'

// Lesson: Memory-Safety Violations (README §16)
export default {
  id: 'memory-safety',
  title: 'Memory-Safety Violations',
  blurb: 'Operations that are programming errors — which the reference interpreter catches, and which it leaves undefined.',
  blocks: [
    {
      type: 'prose',
      md: `Glang is **manually managed**: you take pointers, you \`alloc\`/\`free\`, you \`new\`/\`delete\`. That power comes with a class of mistakes that are simply *programming errors* — the language defines no way to recover from them.

The spec splits these into two groups: ones the **reference interpreter checks** (it aborts the program with a \`RuntimeError\` instead of limping on), and ones that are **undefined behaviour** (not detected — the result is unspecified). Knowing which is which keeps your intuition honest, especially because a future backend may treat them differently.`,
    },
    {
      type: 'prose',
      md: `### Checked: the interpreter aborts

When the reference interpreter hits one of these, it stops with a runtime-error diagnostic rather than continuing with garbage:

- **Dereferencing a null pointer** — \`*p\` (or \`p->field\`) where \`p == null\`.
- **Use-after-free** — dereferencing a pointer after its block was freed.
- **Out-of-bounds array access** — indexing past the end (or before the start) of an array.
- **Double delete / double free** — calling \`delete\` or \`free\` twice on the same pointer.
- **Free of a non-heap pointer** — \`free\`-ing something that was never heap-allocated (e.g. \`&localVar\`).
- **Division or modulo by zero** — \`a / 0\` or \`a % 0\`.`,
    },
    {
      type: 'static',
      caption: 'divzero.lang',
      code: `int main() {
    int a = 10;
    int b = 0;
    print(a / b);   // division by zero
    return 0;
}`,
      output: 'RuntimeError: division by zero',
    },
    {
      type: 'callout',
      tone: 'gotcha',
      md: `The same fail-fast rule covers **modulo**: \`a % 0\` aborts exactly like \`a / 0\`. Guard a divisor you do not control — \`if (b != 0) { ... }\` — before dividing.`,
    },
    {
      type: 'static',
      caption: 'use-after-free.lang',
      code: `int main() {
    int* p = alloc(int, 1);
    *p = 7;
    print(*p);      // 7
    free(p);
    print(*p);      // use-after-free: aborts here
    return 0;
}`,
      output: '7\nRuntimeError: use of freed pointer',
    },
    {
      type: 'static',
      caption: 'double-free.lang',
      code: `int main() {
    int* p = alloc(int, 4);
    p[0] = 1;
    free(p);
    free(p);        // second free of the same pointer: aborts
    return 0;
}`,
      output: 'RuntimeError: double free',
    },
    {
      type: 'callout',
      tone: 'warn',
      md: `These checked behaviours are a property of the **reference interpreter**, not a guarantee of the language. The exact wording of each diagnostic is an implementation detail — do not write programs that depend on a particular message, or even on the abort happening at all.`,
    },
    {
      type: 'prose',
      md: `### Undefined behaviour: not detected

These the interpreter does **not** catch. The result is unspecified — your program may appear to work, then break under a different build:

- **Reading an uninitialised \`alloc\`'d value.** The interpreter happens to zero-fill fresh blocks, but programs must not rely on it — always write before you read.
- **Integer overflow.** Arithmetic that exceeds the type's range wraps on most platforms, but that is not guaranteed.
- **Casting to an incompatible pointer type and dereferencing.** Reinterpreting one pointer type as another and reading through it is unspecified.`,
    },
    {
      type: 'callout',
      tone: 'note',
      md: `**Direction.** The reference interpreter deliberately favours fail-fast safety, so most classic C hazards above are *checked* rather than silently undefined. A future optimising or native backend may **downgrade some checked cases to true undefined behaviour** for performance. Portable programs should depend on neither the check firing nor on any particular post-violation result — just don't commit the violation.`,
    },
    {
      type: 'prose',
      md: `The practical takeaway is short: **null-check before you dereference, bound-check before you index, write before you read, and free each block exactly once.** Code that obeys those rules never touches either column above.`,
    },
    {
      type: 'static',
      caption: 'safe.lang',
      code: `int main() {
    int* p = alloc(int, 3);
    // write before read — no UB
    p[0] = 10;
    p[1] = 20;
    p[2] = 30;

    int sum = 0;
    for (int i = 0; i < 3; ++i) {
        sum += p[i];        // in-bounds: 0, 1, 2
    }
    print(sum);             // 60

    free(p);                // freed exactly once
    return 0;
}`,
      output: '60',
    },
    {
      type: 'exercise',
      ex: {
        id: 'memory-safety-ex1',
        difficulty: 'easy',
        prompt: `**Predict the output.** This program guards its divisor before dividing, so it never trips the divide-by-zero check. What does it print?`,
        code: `int safeDiv(int a, int b) {
    if (b == 0) {
        return -1;          // sentinel instead of dividing
    }
    return a / b;
}

int main() {
    print(safeDiv(20, 4));
    print(safeDiv(7, 0));
    print(safeDiv(9, 2));   // integer division
    return 0;
}`,
        check: {
          kind: 'predict',
          expected: '5\n-1\n4',
        },
        hints: [
          'The middle call passes `b == 0`, so it returns the sentinel `-1` without ever dividing.',
          'Both operands are `int`, so `9 / 2` is integer division: `4`.',
        ],
      },
    },
    {
      type: 'exercise',
      ex: {
        id: 'memory-safety-ex2',
        difficulty: 'medium',
        prompt: `**Predict the output.** One of the lines below commits a *checked* violation. Trace the program: print the lines that run, and on the line that violates safety, type the interpreter's abort diagnostic (it begins with \`RuntimeError\`).`,
        code: `int main() {
    int* p = alloc(int, 2);
    p[0] = 100;
    p[1] = 200;
    print(p[0]);            // ok
    print(p[1]);            // ok
    print(p[2]);            // out-of-bounds read
    free(p);
    return 0;
}`,
        check: {
          kind: 'predict',
          expected: '100\n200\nRuntimeError: out-of-bounds access',
        },
        hints: [
          'A block of `alloc(int, 2)` has valid indices `0` and `1` only — index `2` is one past the end.',
          'The first two prints succeed and produce output; the third index aborts the program before `free` ever runs.',
          'The exact wording is an implementation detail — the key idea is that an out-of-bounds access is *checked* and aborts with a `RuntimeError`.',
        ],
      },
    },
  ],
} satisfies Lesson
