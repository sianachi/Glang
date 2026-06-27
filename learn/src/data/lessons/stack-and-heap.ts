import type { Lesson } from '../../types.ts'

export default {
  id: 'stack-and-heap',
  title: 'Stack vs Heap',
  blurb: 'Where values live: automatic stack storage versus explicit heap allocation.',
  blocks: [
    {
      type: 'prose',
      md: `Glang is **manually managed** — there is no garbage collector. But that does not mean you allocate everything by hand. Memory comes from two places, and most of the time the language handles one of them for you.

- The **stack** holds local variables. Allocation and cleanup are automatic.
- The **heap** holds memory you ask for explicitly, and that you are responsible for releasing.

This lesson is about the stack — the part you get for free. The next lessons cover the heap.`,
    },
    {
      type: 'prose',
      md: `## What lives on the stack

Two kinds of declarations are stack-allocated:

1. **Primitive variables** declared inside a function or block — \`int\`, \`float\`, \`bool\`, \`char\`, \`byte\`.
2. **Fixed-size arrays** — \`int[64] buf;\` reserves 64 ints inline, right there on the stack.

Both are created when control reaches the declaration and **freed automatically when the enclosing scope exits**. You never write \`free\` for them.`,
    },
    {
      type: 'static',
      caption: 'stack.lang',
      code: `int main() {
    int x = 5;        // stack
    int[64] buf;      // stack — 64 ints, allocated inline
    buf[0] = x;
    print(buf[0]);
    return 0;
}                     // x and buf freed automatically here`,
      output: `5`,
    },
    {
      type: 'prose',
      md: `When \`main\` returns, both \`x\` and \`buf\` are gone — no \`free\` call, no leak. The same is true of any nested block: a variable declared inside \`{ ... }\` dies at the closing brace.`,
    },
    {
      type: 'static',
      caption: 'scope.lang',
      code: `int main() {
    int a = 1;
    {
        int b = 2;    // lives only inside this block
        print(a + b);
    }                 // b freed here
    print(a);
    return 0;
}                     // a freed here`,
      output: `3
1`,
    },
    {
      type: 'callout',
      tone: 'note',
      md: `Stack storage is tied to **scope**, not to the variable's name. Entering a block creates a fresh set of locals; leaving it destroys them. This is why recursion works: each call gets its own copy of every local on the stack.`,
    },
    {
      type: 'prose',
      md: `## What does *not* live on the stack

Anything created with \`alloc\`, \`new\`, or a growing standard-library collection (\`List<T>\`, \`Map<K,V>\`) lives on the **heap**. Heap memory outlives the scope that created it and must be released explicitly with \`free\` or \`delete\`. The stack/heap split is the whole reason those keywords exist — you reach for the heap when a value needs to outlive the function that made it, or when its size is not known until runtime.

A fixed array like \`int[64] buf\` is stack memory with a size fixed at compile time. A *sized* heap block like \`alloc(int, n)\` can size itself from a runtime value — that flexibility is exactly what costs you the manual \`free\`.`,
    },
    {
      type: 'callout',
      tone: 'tip',
      md: `Rule of thumb: if you did not type \`alloc\`, \`new\`, or use a collection that grows, the value is on the stack and you owe nothing. The moment you *do* type one of those, you own a release.`,
    },
    {
      type: 'prose',
      md: `Stack primitives behave exactly like the values you have already been printing — assignment copies the value, and arithmetic produces new values. Let's confirm your intuition with a couple of predictions.`,
    },
    {
      type: 'exercise',
      ex: {
        id: 'stack-and-heap-ex1',
        difficulty: 'easy',
        prompt: `**Predict the output.** A nested block introduces its own \`y\`. Type exactly what the program prints.`,
        code: `int main() {
    int x = 10;
    {
        int y = x + 5;
        print(y);
    }
    print(x);
    return 0;
}`,
        check: {
          kind: 'predict',
          expected: '15\n10',
        },
        hints: [
          '`y` is computed from `x` inside the block and printed there.',
          'After the block, `y` is gone but `x` is unchanged.',
        ],
      },
    },
    {
      type: 'exercise',
      ex: {
        id: 'stack-and-heap-ex2',
        difficulty: 'easy',
        prompt: `Write a program with two stack variables \`a = 7\` and \`b = 3\`. Print their sum, then their difference, so the output is:

\`\`\`
10
4
\`\`\``,
        starter: `int main() {
    // declare a and b, then print sum and difference

    return 0;
}`,
        check: {
          kind: 'output',
          expected: '10\n4',
        },
        hints: [
          'Both `a` and `b` are plain `int` stack variables — no `alloc` needed.',
          'Print `a + b` first, then `a - b`.',
        ],
        solution: `int main() {
    int a = 7;
    int b = 3;
    print(a + b);
    print(a - b);
    return 0;
}`,
      },
    },
  ],
} satisfies Lesson
