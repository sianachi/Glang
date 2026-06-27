import type { Lesson } from '../../types.ts'

export default {
  id: 'arithmetic',
  title: 'Arithmetic Operators',
  blurb: 'Add, subtract, multiply, divide, and take remainders — and watch how types change the result.',
  blocks: [
    {
      type: 'prose',
      md: `Glang has the five arithmetic operators you would expect:

| Operator | Meaning |
|---|---|
| \`+\` | Addition (also string concatenation) |
| \`-\` | Subtraction |
| \`*\` | Multiplication |
| \`/\` | Division |
| \`%\` | Modulo (remainder) |

Let's start with the straightforward four.`,
    },
    {
      type: 'run',
      caption: 'basics.lang',
      code: `int main() {
    print(2 + 3);
    print(10 - 4);
    print(6 * 7);
    print(20 - 8 * 2);
    return 0;
}`,
    },
    {
      type: 'prose',
      md: `### \`+\` also joins strings

When both operands are strings, \`+\` **concatenates** them instead of adding. There is no automatic number-to-string coercion, so both sides must already be strings.`,
    },
    {
      type: 'run',
      caption: 'concat.lang',
      code: `int main() {
    string greeting = "Hello, " + "Glang";
    print(greeting);
    print("ab" + "cd");
    return 0;
}`,
    },
    {
      type: 'prose',
      md: `### Division depends on the types

This is the rule that surprises people most. The behaviour of \`/\` is decided by the **types of its operands**:

- If **both** operands are \`int\`, you get **integer division** — the result is truncated toward zero, dropping any fractional part. So \`7 / 2\` is \`3\`, not \`3.5\`.
- If either operand is a \`float\`, you get **float division** — the fractional part is kept. So \`7.0 / 2.0\` is \`3.5\`.`,
    },
    {
      type: 'run',
      caption: 'division.lang',
      code: `int main() {
    print(7 / 2);      // int / int -> integer division
    print(7.0 / 2.0);  // float / float -> float division
    print(8 / 2);      // exact, still an int
    print(8.0 / 2.0);  // exact, but printed as a float
    return 0;
}`,
    },
    {
      type: 'callout',
      tone: 'gotcha',
      md: `**Integer division truncates.** \`7 / 2\` is \`3\`, and \`1 / 2\` is \`0\` — the remainder is simply discarded when both operands are \`int\`.

If you want a fractional answer, make at least one operand a \`float\`: write \`7.0 / 2.0\` (or cast with \`(float)\`). A whole-valued float prints with one decimal place, so \`8.0 / 2.0\` prints \`4.0\`, not \`4\`.`,
    },
    {
      type: 'prose',
      md: `### Modulo: the remainder

\`%\` gives the remainder of a division. It works on \`int\` and \`byte\` operands. It is the classic tool for "is this even?" and for wrapping a value into a range.`,
    },
    {
      type: 'run',
      caption: 'modulo.lang',
      code: `int main() {
    print(7 % 2);    // remainder of 7 / 2
    print(10 % 5);   // divides evenly -> 0
    print(13 % 12);  // wrap a clock hour
    return 0;
}`,
    },
    {
      type: 'prose',
      md: `### Byte arithmetic wraps at 256

A \`byte\` holds a value in \`0..255\`. When **both** operands are \`byte\`, every arithmetic operator produces a \`byte\`, and the result **wraps modulo 256** instead of overflowing into a larger range. So a \`byte\` sum of \`300\` becomes \`300 - 256 = 44\`.`,
    },
    {
      type: 'run',
      caption: 'byte-wrap.lang',
      code: `int main() {
    byte a = 200;
    byte b = 100;
    print(a + b);   // 300 wraps to 44
    print(a - b);   // 100, in range
    return 0;
}`,
    },
    {
      type: 'exercise',
      ex: {
        id: 'arithmetic-ex1',
        difficulty: 'easy',
        prompt: `Print the quotient and the remainder of \`17\` divided by \`5\`, each on its own line, using integer division and modulo.

Expected output:

\`\`\`
3
2
\`\`\``,
        starter: `int main() {
    int n = 17;
    int d = 5;
    // print n / d, then n % d

    return 0;
}`,
        check: {
          kind: 'output',
          expected: '3\n2',
        },
        hints: [
          'With two `int` operands, `/` truncates: `17 / 5` is `3`.',
          '`%` gives the leftover: `17 % 5` is `2`.',
        ],
        solution: `int main() {
    int n = 17;
    int d = 5;
    print(n / d);
    print(n % d);
    return 0;
}`,
      },
    },
    {
      type: 'exercise',
      ex: {
        id: 'arithmetic-ex2',
        difficulty: 'medium',
        prompt: `**Predict the output.** Mind the difference between integer and float division. Type exactly what this prints (a whole-valued float prints with one decimal place).`,
        code: `int main() {
    print(9 / 4);
    print(9.0 / 4.0);
    print(8 / 4);
    print(8.0 / 4.0);
    return 0;
}`,
        check: {
          kind: 'predict',
          expected: '2\n2.25\n2\n2.0',
        },
        hints: [
          '`9 / 4` is int/int, so it truncates to `2`.',
          '`8.0 / 4.0` is exact but still a float, so it prints `2.0`.',
        ],
      },
    },
    {
      type: 'exercise',
      ex: {
        id: 'arithmetic-ex3',
        difficulty: 'medium',
        prompt: `**Predict the output.** Both operands are \`byte\`, so the result wraps modulo 256. Type exactly what this prints.`,
        code: `int main() {
    byte x = 250;
    byte y = 10;
    print(x + y);
    print(x % y);
    return 0;
}`,
        check: {
          kind: 'predict',
          expected: '4\n0',
        },
        hints: [
          '`250 + 10` is `260`, which wraps: `260 - 256 = 4`.',
          '`250 % 10` divides evenly, so the remainder is `0`.',
        ],
      },
    },
  ],
} satisfies Lesson
