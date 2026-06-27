import type { Lesson } from '../../types.ts'

export default {
  id: 'assignment',
  title: 'Assignment & Increment',
  blurb: 'Update variables with = and the compound operators, and step them with prefix ++ / --.',
  blocks: [
    {
      type: 'prose',
      md: `Once a variable exists, you change its value with **assignment**. The plain form is \`=\`; on top of that there is a family of **compound** operators that combine an arithmetic or bitwise step with the assignment.`,
    },
    {
      type: 'prose',
      md: `## Compound assignment

Each compound operator applies an operation to the variable using the right-hand side, then stores the result back:

- arithmetic: \`+=\` \`-=\` \`*=\` \`/=\` \`%=\`
- bitwise: \`&=\` \`|=\` \`^=\` \`<<=\` \`>>=\`

So \`x += 5\` means exactly \`x = x + 5\`.`,
    },
    {
      type: 'run',
      caption: 'compound.lang',
      code: `int main() {
    int x = 10;
    x += 5;
    print(x);
    x *= 2;
    print(x);
    x /= 3;
    print(x);
    x %= 4;
    print(x);
    return 0;
}`,
    },
    {
      type: 'callout',
      tone: 'note',
      md: `The bitwise compound assignments (\`&=\`, \`|=\`, \`^=\`, \`<<=\`, \`>>=\`) carry the same type rule as the bitwise operators themselves: the operands must be **\`int\` or \`byte\`**. \`x <<= 1\` on a \`float\` is a type error.`,
    },
    {
      type: 'run',
      caption: 'bitwise-assign.lang',
      code: `int main() {
    int bits = 6;
    bits <<= 1;
    print(bits);
    bits &= 9;
    print(bits);
    return 0;
}`,
    },
    {
      type: 'prose',
      md: `## Increment and decrement — prefix only

To step a variable by one, use the **prefix** forms:

- \`++i\` adds one
- \`--i\` subtracts one`,
    },
    {
      type: 'run',
      caption: 'step.lang',
      code: `int main() {
    int i = 0;
    ++i;
    ++i;
    print(i);
    --i;
    print(i);
    return 0;
}`,
    },
    {
      type: 'callout',
      tone: 'gotcha',
      md: `Two limits to remember:

- **No postfix.** \`i++\` and \`i--\` do **not** exist in Glang. Always write \`++i\` / \`--i\`.
- **Assignment is a statement, not an expression.** It produces no value, so you cannot use it inside a larger expression and **chained assignment \`a = b = 5\` is not allowed**. Assign one variable per statement.`,
    },
    {
      type: 'static',
      caption: 'not-allowed.lang',
      code: `int main() {
    int a;
    int b;
    a = b = 5;   // error: assignment has no value to chain
    int c = 0;
    c++;         // error: postfix ++ is not supported, use ++c
    return 0;
}`,
      output: `(does not compile)`,
    },
    {
      type: 'exercise',
      ex: {
        id: 'assignment-ex1',
        difficulty: 'easy',
        prompt: `Start with \`total = 100\`. Using **compound assignment operators only** (no plain \`=\`), subtract \`30\`, then multiply by \`2\`, then print \`total\`.

Expected output:

\`\`\`
140
\`\`\``,
        starter: `int main() {
    int total = 100;
    // subtract 30 with -=
    // multiply by 2 with *=
    print(total);
    return 0;
}`,
        check: {
          kind: 'output',
          expected: '140',
        },
        hints: [
          '`total -= 30` lowers it to 70.',
          'Then `total *= 2` doubles it.',
        ],
        solution: `int main() {
    int total = 100;
    total -= 30;
    total *= 2;
    print(total);
    return 0;
}`,
      },
    },
    {
      type: 'exercise',
      ex: {
        id: 'assignment-ex2',
        difficulty: 'easy',
        prompt: `Start a counter at \`5\`. Increment it twice and decrement it once using **prefix** operators, then print it.

Expected output:

\`\`\`
6
\`\`\``,
        starter: `int main() {
    int count = 5;
    // ++ twice, -- once (prefix only!)
    print(count);
    return 0;
}`,
        check: {
          kind: 'output',
          expected: '6',
        },
        hints: [
          'Remember: `++count`, never `count++`.',
          'Two increments take 5 to 7; one decrement brings it to 6.',
        ],
        solution: `int main() {
    int count = 5;
    ++count;
    ++count;
    --count;
    print(count);
    return 0;
}`,
      },
    },
    {
      type: 'exercise',
      ex: {
        id: 'assignment-ex3',
        difficulty: 'medium',
        prompt: `**Predict the output.** Trace the variable through each statement and type what it prints.`,
        code: `int main() {
    int n = 8;
    n += 4;
    n /= 2;
    --n;
    print(n);
    return 0;
}`,
        check: {
          kind: 'predict',
          expected: '5',
        },
        hints: [
          '`n += 4` makes it 12, then `n /= 2` makes it 6 (integer division).',
          '`--n` subtracts one more.',
        ],
      },
    },
  ],
} satisfies Lesson
