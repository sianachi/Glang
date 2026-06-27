import type { Lesson } from '../../types.ts'

export default {
  id: 'arrays',
  title: 'Fixed-Size Arrays',
  blurb: 'Stack-allocated arrays whose size is fixed at compile time, indexed from zero.',
  blocks: [
    {
      type: 'prose',
      md: `A **fixed-size array** holds a contiguous run of values whose count is baked into the type. You declare one by putting the size in the type:

\`\`\`c
int[10] buf;     // 10 ints, laid out on the stack
char[256] name;  // 256 chars
\`\`\`

The size is part of the type — \`int[10]\` and \`int[20]\` are different types. The array lives directly on the stack; there is no heap allocation and nothing to free.`,
    },
    {
      type: 'callout',
      tone: 'note',
      md: `The array size must be a **compile-time constant**. You can write \`int[10]\` or \`int[SIZE]\` where \`SIZE\` is a constant, but not \`int[n]\` where \`n\` is a runtime variable. If you need a length decided at runtime, that's a job for a dynamic container (see below).`,
    },
    {
      type: 'prose',
      md: `Arrays are **zero-indexed**: the first element is at index \`0\`, and an array of length \`N\` has valid indices \`0\` through \`N - 1\`. You read and write elements with \`[ ]\`.`,
    },
    {
      type: 'static',
      caption: 'sum.lang',
      code: `int main() {
    int[5] buf;
    for (int i = 0; i < 5; ++i) {
        buf[i] = i * 10;     // 0, 10, 20, 30, 40
    }

    int sum = 0;
    for (int i = 0; i < 5; ++i) {
        sum += buf[i];
    }
    print(buf[0]);   // first element
    print(buf[4]);   // last valid element
    print(sum);      // 0 + 10 + 20 + 30 + 40
    return 0;
}`,
      output: '0\n40\n100',
    },
    {
      type: 'callout',
      tone: 'gotcha',
      md: `**Out-of-bounds access is undefined behaviour.** For \`int[5] buf\`, the only valid indices are \`0..4\`. Reading or writing \`buf[5]\` (or any negative index) is not checked — it may read garbage, corrupt other variables, or crash. Glang does not insert bounds checks; keeping indices in range is your responsibility.`,
    },
    {
      type: 'prose',
      md: `Fixed arrays are deliberately simple: a known number of slots on the stack. When you need a collection that **grows and shrinks at runtime**, reach for the standard library's \`List<T>\` instead — that's where dynamic sizing, appending, and removal live. Fixed arrays stay out of that business by design.`,
    },
    {
      type: 'callout',
      tone: 'note',
      md: `Fixed arrays are not supported by the in-browser runner, so the samples on this page are shown with their output rather than executed. Everything here is valid in the full Glang compiler.`,
    },
    {
      type: 'exercise',
      ex: {
        id: 'arrays-ex1',
        difficulty: 'easy',
        prompt: `**Predict the output.** The array is filled, then two elements are read back.`,
        code: `int main() {
    int[4] xs;
    xs[0] = 2;
    xs[1] = 4;
    xs[2] = 6;
    xs[3] = 8;
    print(xs[1]);
    print(xs[3]);
    print(xs[1] + xs[2]);
    return 0;
}`,
        check: {
          kind: 'predict',
          expected: '4\n8\n10',
        },
        hints: [
          'Indexing is zero-based, so `xs[1]` is the second element (4).',
          '`xs[1] + xs[2]` is `4 + 6`.',
        ],
      },
    },
    {
      type: 'exercise',
      ex: {
        id: 'arrays-ex2',
        difficulty: 'medium',
        prompt: `**Predict the output.** Trace the loop that writes into the array, then the loop that reads it.`,
        code: `int main() {
    int[5] sq;
    for (int i = 0; i < 5; ++i) {
        sq[i] = i * i;
    }
    int total = 0;
    for (int i = 0; i < 5; ++i) {
        total += sq[i];
    }
    print(sq[2]);
    print(sq[4]);
    print(total);
    return 0;
}`,
        check: {
          kind: 'predict',
          expected: '4\n16\n30',
        },
        hints: [
          'The array holds 0, 1, 4, 9, 16 (the squares of 0..4).',
          'The total is `0 + 1 + 4 + 9 + 16`.',
        ],
      },
    },
  ],
} satisfies Lesson
