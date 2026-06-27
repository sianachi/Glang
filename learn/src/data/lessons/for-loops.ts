import type { Lesson } from '../../types.ts'

export default {
  id: 'for-loops',
  title: 'For Loops',
  blurb: 'Count through a range with the three-part for loop.',
  blocks: [
    {
      type: 'prose',
      md: `When you know how many times to repeat, a **\`for\`** loop keeps the counter logic in one tidy header:

\`\`\`
for (int i = 0; i < n; ++i) {
    // body
}
\`\`\`

The header has three sections separated by semicolons:
1. **init** — \`int i = 0\` runs once, before the loop starts.
2. **condition** — \`i < n\` is checked before every pass; the loop runs while it is \`true\`.
3. **post** — \`++i\` runs at the end of every pass, just before the condition is re-checked.`,
    },
    {
      type: 'run',
      caption: 'count.lang',
      code: `int main() {
    for (int i = 0; i < 5; ++i) {
        print(i);
    }
    return 0;
}`,
    },
    {
      type: 'prose',
      md: `This prints \`0\` through \`4\`. The loop variable \`i\` starts at \`0\`, the body runs while \`i < 5\`, and \`++i\` advances it each time.`,
    },
    {
      type: 'callout',
      tone: 'gotcha',
      md: `**All three sections are required.** Glang has no \`for (;;)\` shorthand and no way to omit the init, condition, or post. If you want an open-ended loop, reach for \`while\` instead.`,
    },
    {
      type: 'callout',
      tone: 'gotcha',
      md: `The post section uses **prefix** increment: \`++i\`, not \`i++\`. Glang only supports the prefix forms \`++i\` and \`--i\`. Writing \`i++\` is a syntax error.`,
    },
    {
      type: 'callout',
      tone: 'note',
      md: `The loop variable is **scoped to the loop body**. The \`i\` declared in \`for (int i = ...)\` does not exist after the closing brace — you cannot read it once the loop finishes.`,
    },
    {
      type: 'prose',
      md: `The condition and post can be anything you like — count down, step by twos, or accumulate a value. Here we sum the even numbers from \`0\` to \`8\`.`,
    },
    {
      type: 'run',
      caption: 'evens.lang',
      code: `int main() {
    int total = 0;
    for (int i = 0; i <= 8; i += 2) {
        total += i;
    }
    print(total);
    return 0;
}`,
    },
    {
      type: 'exercise',
      ex: {
        id: 'for-loops-ex1',
        difficulty: 'easy',
        prompt: `Write a \`for\` loop that prints the numbers \`1\` through \`4\`, one per line:

\`\`\`
1
2
3
4
\`\`\``,
        starter: `int main() {
    // for loop here

    return 0;
}`,
        check: {
          kind: 'output',
          expected: '1\n2\n3\n4',
        },
        hints: [
          'Start `i` at `1` and loop while `i <= 4`.',
          'Remember the post section is prefix: `++i`, not `i++`.',
        ],
        solution: `int main() {
    for (int i = 1; i <= 4; ++i) {
        print(i);
    }
    return 0;
}`,
      },
    },
    {
      type: 'exercise',
      ex: {
        id: 'for-loops-ex2',
        difficulty: 'medium',
        prompt: `Use a \`for\` loop to compute and print the factorial of \`5\` (that is \`1 * 2 * 3 * 4 * 5\`). Expected output:

\`\`\`
120
\`\`\``,
        starter: `int main() {
    int result = 1;
    // multiply result by each value from 1 to 5

    print(result);
    return 0;
}`,
        check: {
          kind: 'output',
          expected: '120',
        },
        hints: [
          'Start `result` at `1`, then multiply it by `i` each pass.',
          'Loop `i` from `1` to `5` inclusive: `for (int i = 1; i <= 5; ++i)`.',
        ],
        solution: `int main() {
    int result = 1;
    for (int i = 1; i <= 5; ++i) {
        result *= i;
    }
    print(result);
    return 0;
}`,
      },
    },
    {
      type: 'exercise',
      ex: {
        id: 'for-loops-ex3',
        difficulty: 'easy',
        prompt: `**Predict the output.** Trace the counting-down loop and type exactly what it prints.`,
        code: `int main() {
    for (int i = 3; i >= 0; --i) {
        print(i);
    }
    return 0;
}`,
        check: {
          kind: 'predict',
          expected: '3\n2\n1\n0',
        },
        hints: [
          'The post section `--i` decreases `i` each pass.',
          'The loop runs while `i >= 0`, so it stops after printing `0`.',
        ],
      },
    },
  ],
} satisfies Lesson
