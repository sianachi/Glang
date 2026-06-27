import type { Lesson } from '../../types.ts'

export default {
  id: 'while-loops',
  title: 'While Loops',
  blurb: 'Repeat a block of code while a condition stays true.',
  blocks: [
    {
      type: 'prose',
      md: `A **\`while\`** loop runs its body over and over, as long as a condition holds:

\`\`\`
while (condition) {
    // body runs each time condition is true
}
\`\`\`

Before every pass, the condition is checked. The moment it becomes \`false\`, the loop stops and the program continues after the closing brace. As with \`if\`, the condition must be a \`bool\` and the braces are required.`,
    },
    {
      type: 'run',
      caption: 'countdown.lang',
      code: `int main() {
    int n = 5;
    while (n > 0) {
        print(n);
        --n;
    }
    print("liftoff");
    return 0;
}`,
    },
    {
      type: 'prose',
      md: `Notice the **\`--n\`** inside the body. Something in the loop must move the condition toward \`false\`, or the loop never ends. Here each pass shrinks \`n\` until \`n > 0\` finally fails.`,
    },
    {
      type: 'callout',
      tone: 'warn',
      md: `If the condition can never become \`false\`, you get an **infinite loop**. Always make sure the body changes a variable the condition depends on — like the \`--n\` above.`,
    },
    {
      type: 'prose',
      md: `\`while\` is great for accumulating a result. Here we add up \`1 + 2 + ... + 5\` by keeping a running \`total\` and a counter \`i\`.`,
    },
    {
      type: 'run',
      caption: 'sum.lang',
      code: `int main() {
    int i = 1;
    int total = 0;
    while (i <= 5) {
        total += i;
        ++i;
    }
    print(total);
    return 0;
}`,
    },
    {
      type: 'prose',
      md: `\`total += i\` is shorthand for \`total = total + i\`, and \`++i\` adds one to \`i\`. After the loop, \`total\` holds \`15\`.`,
    },
    {
      type: 'exercise',
      ex: {
        id: 'while-loops-ex1',
        difficulty: 'easy',
        prompt: `Use a \`while\` loop to print the numbers \`1\` through \`3\`, one per line:

\`\`\`
1
2
3
\`\`\``,
        starter: `int main() {
    int i = 1;
    // loop while i <= 3, printing i each time

    return 0;
}`,
        check: {
          kind: 'output',
          expected: '1\n2\n3',
        },
        hints: [
          'Start with `i = 1` and loop while `i <= 3`.',
          'Print `i`, then move it forward with `++i` so the loop can end.',
        ],
        solution: `int main() {
    int i = 1;
    while (i <= 3) {
        print(i);
        ++i;
    }
    return 0;
}`,
      },
    },
    {
      type: 'exercise',
      ex: {
        id: 'while-loops-ex2',
        difficulty: 'easy',
        prompt: `**Predict the output.** Trace the loop and type exactly what it prints.`,
        code: `int main() {
    int x = 16;
    while (x > 1) {
        print(x);
        x /= 2;
    }
    return 0;
}`,
        check: {
          kind: 'predict',
          expected: '16\n8\n4\n2',
        },
        hints: [
          '`x /= 2` halves `x` each pass (integer division).',
          'The loop stops as soon as `x > 1` is false — when `x` reaches `1`.',
        ],
      },
    },
  ],
} satisfies Lesson
