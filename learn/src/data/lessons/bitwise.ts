import type { Lesson } from '../../types.ts'

export default {
  id: 'bitwise',
  title: 'Bitwise Operators',
  blurb: 'Manipulate individual bits with AND, OR, XOR, NOT, and the shift operators.',
  blocks: [
    {
      type: 'prose',
      md: `Bitwise operators work on the raw binary representation of a number, one bit at a time. Glang gives you six:

- \`&\` — AND (1 only where **both** bits are 1)
- \`|\` — OR (1 where **either** bit is 1)
- \`^\` — XOR (1 where the bits **differ**)
- \`~\` — NOT (flips every bit)
- \`<<\` — left shift (move bits left, filling with 0)
- \`>>\` — right shift (move bits right)`,
    },
    {
      type: 'callout',
      tone: 'note',
      md: `Bitwise operators apply only to integers. Both operands must be the **same** integer type: either **both \`int\`** or **both \`byte\`**. You cannot mix an \`int\` with a \`byte\`, and they never apply to \`float\`, \`bool\`, or \`string\`.`,
    },
    {
      type: 'prose',
      md: `## With \`int\`

Here are all six operators on \`int\` values.`,
    },
    {
      type: 'run',
      caption: 'bits.lang',
      code: `int main() {
    print(12 & 10);
    print(12 | 10);
    print(12 ^ 10);
    print(~5);
    print(1 << 4);
    print(40 >> 2);
    return 0;
}`,
    },
    {
      type: 'prose',
      md: `\`12 & 10\` is \`8\`: in binary \`1100 & 1010 = 1000\`. \`1 << 4\` shifts the single bit four places left, giving \`16\` (the same as multiplying by 2 four times).`,
    },
    {
      type: 'prose',
      md: `## Arithmetic right shift

For signed \`int\`, \`>>\` is an **arithmetic** shift: it sign-extends, copying the sign bit in from the left so the result keeps its sign. Shifting a negative number right keeps it negative.`,
    },
    {
      type: 'run',
      caption: 'arith-shift.lang',
      code: `int main() {
    print(-8 >> 1);
    print(-8 >> 2);
    return 0;
}`,
    },
    {
      type: 'prose',
      md: `\`-8 >> 1\` is \`-4\`, not a large positive number — the sign is preserved.`,
    },
    {
      type: 'prose',
      md: `## With \`byte\`

When both operands are \`byte\`, the result is a \`byte\` **masked to \`0..255\`**. This matters for \`~\` and \`<<\`, which can otherwise produce values outside a byte's range — the mask keeps them in range.`,
    },
    {
      type: 'static',
      caption: 'byte-bits.lang',
      code: `int main() {
    byte b = (byte)200;
    byte c = (byte)15;
    print(b & c);       // 200 & 15
    print(b | c);       // 200 | 15
    print(~b);          // flipped, then masked to 0..255
    print((byte)64 << 2); // 256 wraps back into range
    return 0;
}`,
      output: `8
207
55
0`,
    },
    {
      type: 'prose',
      md: `\`~b\` on the \`int\` \`200\` would be \`-201\`, but as a \`byte\` it is masked to \`55\`. Likewise \`64 << 2\` is \`256\`, which masks down to \`0\`. The low 8 bits are all that survive.`,
    },
    {
      type: 'exercise',
      ex: {
        id: 'bitwise-ex1',
        difficulty: 'easy',
        prompt: `Print the result of combining \`12\` and \`10\` with bitwise XOR (\`^\`), then on the next line print \`6 << 2\`.

Expected output:

\`\`\`
6
24
\`\`\``,
        starter: `int main() {
    // print 12 ^ 10
    // print 6 << 2
    return 0;
}`,
        check: {
          kind: 'output',
          expected: '6\n24',
        },
        hints: [
          '`^` is 1 where the two bits differ: `1100 ^ 1010 = 0110`.',
          '`6 << 2` shifts the bits of 6 two places left.',
        ],
        solution: `int main() {
    print(12 ^ 10);
    print(6 << 2);
    return 0;
}`,
      },
    },
    {
      type: 'exercise',
      ex: {
        id: 'bitwise-ex2',
        difficulty: 'medium',
        prompt: `Two \`byte\` values, \`flags = 12\` and \`mask = 10\`, are given. Print their bitwise AND, then their bitwise OR — each on its own line.

Expected output:

\`\`\`
8
14
\`\`\``,
        starter: `int main() {
    byte flags = (byte)12;
    byte mask = (byte)10;
    // print flags & mask
    // print flags | mask
    return 0;
}`,
        check: {
          kind: 'output',
          expected: '8\n14',
        },
        hints: [
          'Both operands are already `byte`, so `&` and `|` work directly.',
          '`12 & 10` keeps only the bits set in both: `1100 & 1010 = 1000` = 8.',
        ],
        solution: `int main() {
    byte flags = (byte)12;
    byte mask = (byte)10;
    print(flags & mask);
    print(flags | mask);
    return 0;
}`,
      },
    },
  ],
} satisfies Lesson
