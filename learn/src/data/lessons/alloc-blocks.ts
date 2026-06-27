import type { Lesson } from '../../types.ts'

export default {
  id: 'alloc-blocks',
  title: 'Heap Allocation: alloc & free',
  blurb: 'Asking for heap memory by hand with alloc, and giving it back with free.',
  blocks: [
    {
      type: 'prose',
      md: `When a value must outlive the scope that created it, or when its size is only known at runtime, you allocate it on the **heap** with \`alloc\`. Heap memory is yours until you hand it back with \`free\`.

> Heap code (\`alloc\`/\`free\`) cannot run in the in-browser sandbox, so every program on this page is a read-only sample with its output shown. Trace them by hand — that is exactly the skill manual memory management demands.`,
    },
    {
      type: 'prose',
      md: `## A single cell

\`alloc(T)\` reserves enough memory for **one** value of type \`T\` and returns a \`T*\` — a pointer to it. The memory is **uninitialised**: you must write before you read. \`free(p)\` releases it.`,
    },
    {
      type: 'static',
      caption: 'one_cell.lang',
      code: `int main() {
    int* p = alloc(int);   // a T* to one uninitialised int
    *p = 42;               // write through the pointer
    print(*p);             // read it back
    free(p);               // release the memory
    return 0;
}`,
      output: `42`,
    },
    {
      type: 'callout',
      tone: 'gotcha',
      md: `Behaviour **after \`free\`** is undefined. Once you call \`free(p)\`, the pointer \`p\` is dangling — reading \`*p\`, writing \`*p\`, or calling \`free(p)\` a second time are all bugs. Drop the pointer the instant you free it.`,
    },
    {
      type: 'callout',
      tone: 'warn',
      md: `\`alloc(T)\` gives you **uninitialised** memory. Reading \`*p\` before you have written to it yields garbage. (The *sized* form below is the exception — it zero-fills.)`,
    },
    {
      type: 'prose',
      md: `## A sized block

Pass a count — \`alloc(T, n)\` — and you get a **contiguous block of \`n\` cells**, all **zero-initialised**. You index it straight through the pointer with \`xs[i]\`, and a single \`free\` releases the whole block.`,
    },
    {
      type: 'static',
      caption: 'block.lang',
      code: `int main() {
    int* xs = alloc(int, 8);   // 8 zeroed ints, contiguous
    print(xs[0]);              // 0 — zero-initialised
    xs[3] = 42;
    print(xs[3]);              // 42  (in-bounds)
    free(xs);                  // frees all 8 cells at once
    return 0;
}`,
      output: `0
42`,
    },
    {
      type: 'callout',
      tone: 'gotcha',
      md: `Indexing **out of bounds** — \`xs[8]\` or \`xs[-1]\` on a block of 8 — is a **runtime error**. The block knows its length; there is no silently reading past the end the way raw C would.`,
    },
    {
      type: 'prose',
      md: `## Why this matters

A sized \`alloc\` plus pointer indexing is the primitive the whole standard library is built on. A \`List<T>\` that "grows" is really doing this under the hood:

1. \`alloc\` a bigger block,
2. copy the existing elements into it,
3. \`free\` the old block,
4. keep using the new one.

\`Map<K,V>\` and the other collections grow the same way. When you call \`list.push(x)\` you are, several layers down, hitting \`alloc\` and \`free\`.`,
    },
    {
      type: 'static',
      caption: 'grow.lang',
      code: `int main() {
    int* xs = alloc(int, 2);   // start small
    xs[0] = 1;
    xs[1] = 2;

    // "grow": allocate bigger, copy, free old
    int* ys = alloc(int, 4);
    ys[0] = xs[0];
    ys[1] = xs[1];
    free(xs);                  // old block returned
    ys[2] = 3;

    print(ys[0]);
    print(ys[2]);
    free(ys);
    return 0;
}`,
      output: `1
3`,
    },
    {
      type: 'callout',
      tone: 'tip',
      md: `Every \`alloc\` should have exactly one matching \`free\` on every path out of the function. Forget the \`free\` and you leak; call it twice and you corrupt the heap. The \`using\` block (a later lesson) automates this pairing.`,
    },
    {
      type: 'exercise',
      ex: {
        id: 'alloc-blocks-ex1',
        difficulty: 'medium',
        prompt: `**Predict the output.** The block is zero-initialised, then two cells are written. Type exactly what prints.`,
        code: `int main() {
    int* xs = alloc(int, 4);
    xs[0] = 10;
    xs[2] = xs[0] + 5;
    print(xs[0]);
    print(xs[1]);
    print(xs[2]);
    free(xs);
    return 0;
}`,
        check: {
          kind: 'predict',
          expected: '10\n0\n15',
        },
        hints: [
          'A sized `alloc` zero-fills every cell, so untouched cells read as `0`.',
          '`xs[1]` was never written; `xs[2]` is `xs[0] + 5`.',
        ],
      },
    },
    {
      type: 'exercise',
      ex: {
        id: 'alloc-blocks-ex2',
        difficulty: 'medium',
        prompt: `**Predict the output.** Watch the order of operations carefully — one line is a bug.

\`\`\`
int main() {
    int* p = alloc(int);
    *p = 7;
    print(*p);
    free(p);
    print(*p);     // <-- reading after free
    return 0;
}
\`\`\`

The first \`print\` is well-defined. Type what it prints, then on a second line type the word \`undefined\` to mark the behaviour of the second \`print\`.`,
        code: `int main() {
    int* p = alloc(int);
    *p = 7;
    print(*p);
    free(p);
    print(*p);     // reading after free is undefined
    return 0;
}`,
        check: {
          kind: 'predict',
          expected: '7\nundefined',
        },
        hints: [
          'The first `print(*p)` happens while `p` is still valid.',
          'After `free(p)`, dereferencing `p` is undefined behaviour — there is no guaranteed value to print.',
        ],
      },
    },
  ],
} satisfies Lesson
