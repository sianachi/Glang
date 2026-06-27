import type { Lesson } from '../../types.ts'

export default {
  id: 'constants',
  title: 'Constants & Conventions',
  blurb: 'Glang v1 has no const keyword — a naming convention marks values that should not change.',
  blocks: [
    {
      type: 'prose',
      md: `Many languages have a \`const\` keyword to mark a value as unchangeable. **Glang v1 does not.** The word \`const\` is *reserved* — set aside for a future version — but it has no effect today, so you cannot use it to lock a variable down.

Instead, Glang relies on a **convention**: name values that should not change in \`ALL_CAPS\`. This signals intent to every reader, even though the compiler still allows reassignment.`,
    },
    {
      type: 'run',
      caption: 'limits.lang',
      code: `int main() {
    int MAX_SIZE = 1024;
    int used = 768;

    print(MAX_SIZE);
    print(MAX_SIZE - used);
    return 0;
}`,
    },
    {
      type: 'prose',
      md: `\`MAX_SIZE\` is an ordinary \`int\` — the \`ALL_CAPS\` name is purely a message to humans: *"treat this as a fixed value; do not reassign it."* The compiler will not stop you if you do, so the discipline is yours to keep.

A pseudo-constant is handy when the same fixed number appears in several places. Declare it once with a clear name, then refer to the name.`,
    },
    {
      type: 'run',
      caption: 'seconds.lang',
      code: `int main() {
    int SECONDS_PER_MINUTE = 60;
    int minutes = 5;

    print(minutes * SECONDS_PER_MINUTE);
    return 0;
}`,
    },
    {
      type: 'callout',
      tone: 'note',
      md: `Because \`ALL_CAPS\` is only a convention, nothing technically prevents \`MAX_SIZE = 2048;\` later in the code. Treat such a reassignment as a code smell: if a name is in capitals, leave its value alone.`,
    },
    {
      type: 'callout',
      tone: 'gotcha',
      md: `Do not reach for the \`const\` keyword — it is reserved for a future version and is not usable in v1. Use an \`ALL_CAPS\` name on a normal declaration instead.`,
    },
    {
      type: 'exercise',
      ex: {
        id: 'constants-ex1',
        difficulty: 'intro',
        prompt: `Declare a pseudo-constant \`int PRICE\` equal to \`25\`, and an \`int qty\` equal to \`4\`. Print the total cost (\`PRICE * qty\`).

Expected output:

\`\`\`
100
\`\`\``,
        starter: `int main() {
    // declare PRICE and qty, then print the total

    return 0;
}`,
        check: {
          kind: 'output',
          expected: '100',
        },
        hints: [
          'Use an ALL_CAPS name for the fixed value: `int PRICE = 25;`.',
          'The total is `PRICE * qty`.',
        ],
        solution: `int main() {
    int PRICE = 25;
    int qty = 4;
    print(PRICE * qty);
    return 0;
}`,
      },
    },
    {
      type: 'exercise',
      ex: {
        id: 'constants-ex2',
        difficulty: 'easy',
        prompt: `**Predict the output.** Read the program and type exactly what it prints. (Remember: \`ALL_CAPS\` is only a convention — reassignment is still allowed.)`,
        code: `int main() {
    int MAX = 10;
    print(MAX);
    MAX = 20;
    print(MAX);
    return 0;
}`,
        check: {
          kind: 'predict',
          expected: '10\n20',
        },
        hints: [
          'The capitals signal "do not change me", but the compiler does not enforce it.',
          'The second assignment really does change `MAX`.',
        ],
      },
    },
  ],
} satisfies Lesson
