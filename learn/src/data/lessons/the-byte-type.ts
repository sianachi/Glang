import type { Lesson } from '../../types.ts'

export default {
  id: 'the-byte-type',
  title: 'The byte Type',
  blurb: 'byte is an unsigned 8-bit octet whose arithmetic wraps modulo 256 — and it keeps its distance from int.',
  blocks: [
    {
      type: 'prose',
      md: `A \`byte\` is an **unsigned 8-bit integer**: it can hold any value from \`0\` to \`255\` and nothing else. It is the substrate for binary data — buffers, octets, raw bytes off a socket or file.

It is its own type. A \`byte\` is **not** an \`int\` (which is 64-bit and signed) and **not** a \`char\` (which is text). Glang keeps all three apart, exactly as it does for every other primitive.`,
    },
    {
      type: 'prose',
      md: `### Wraparound: arithmetic stays in 0..255

Every operation that produces a \`byte\` — arithmetic (\`+ - * / %\`), bitwise (\`& | ^ ~ << >>\`), comparisons, and \`++\`/\`--\` — keeps the result a \`byte\` by **wrapping modulo 256**. There is no overflow error; the value just rolls over.

So \`(byte)200 + (byte)100\` is \`300\` reduced modulo 256, which is \`44\`. Run it:`,
    },
    {
      type: 'run',
      caption: 'wrap.lang',
      code: `int main() {
    byte a = (byte)200;
    byte b = (byte)100;
    print(a + b);       // 300 wraps to 44
    return 0;
}`,
    },
    {
      type: 'prose',
      md: `\`++\` and \`--\` wrap the same way at the edges of the range. Incrementing past \`255\` lands back on \`0\`; decrementing below \`0\` lands on \`255\`.`,
    },
    {
      type: 'run',
      caption: 'wrap-edges.lang',
      code: `int main() {
    byte hi = 255;
    ++hi;
    print(hi);          // 255 + 1 wraps to 0

    byte lo = 0;
    --lo;
    print(lo);          // 0 - 1 wraps to 255
    return 0;
}`,
    },
    {
      type: 'prose',
      md: `### Literals coerce; variables need a cast

There is one convenience: an integer **literal** that already sits in \`0..255\` may be written straight into a \`byte\` with no cast. The range is checked at compile time.`,
    },
    {
      type: 'run',
      caption: 'literals.lang',
      code: `int main() {
    byte ok = 200;      // literal in range: fine, no cast
    byte hex = 0xFF;    // 255: also fine
    print(ok);          // 200
    print(hex);         // 255
    return 0;
}`,
    },
    {
      type: 'static',
      caption: 'literal-out-of-range.lang',
      code: `int main() {
    byte bad = 300;     // 300 is outside 0..255
    return 0;
}`,
      output: `error: integer literal 300 out of range for 'byte'`,
    },
    {
      type: 'callout',
      tone: 'warn',
      md: `The literal shortcut applies **only to literals**. An \`int\` *variable* always needs an explicit \`(byte)\` cast, even if you know its value fits — the compiler will not narrow an \`int\` to a \`byte\` on its own.

\`\`\`
int n = 200;
byte b = n;          // ERROR: cannot assign 'int' to 'byte'
byte b = (byte) n;   // ok: explicit cast
\`\`\``,
    },
    {
      type: 'prose',
      md: `### byte does not mix with int

Because a \`byte\` and an \`int\` are different types, they do not combine in one expression without a cast — the same no-implicit-conversion rule that governs \`int\` and \`float\`. To bring an \`int\` into a \`byte\` computation (or vice versa), cast first.`,
    },
    {
      type: 'run',
      caption: 'no-mix.lang',
      code: `int main() {
    byte b = 10;
    int n = 5;
    // print(b + n);          // ERROR: cannot mix 'byte' and 'int'
    print(b + (byte)n);       // cast the int -> byte arithmetic: 15
    print((int)b + n);        // or cast the byte -> int arithmetic: 15
    return 0;
}`,
    },
    {
      type: 'callout',
      tone: 'note',
      md: `\`print\` on a \`byte\` shows its **numeric value** (\`0..255\`), not a character — that's the difference from \`char\`, which prints as text. \`print((byte)66)\` writes \`66\`, while \`print((char)66)\` writes \`B\`.`,
    },
    {
      type: 'exercise',
      ex: {
        id: 'the-byte-type-ex1',
        difficulty: 'easy',
        prompt: `**Predict the output.** Each line involves \`byte\` wraparound modulo 256.`,
        code: `int main() {
    byte a = (byte)250;
    byte b = (byte)10;
    print(a + b);       // wraps
    byte c = 1;
    --c;
    --c;
    print(c);           // wraps below 0
    return 0;
}`,
        check: {
          kind: 'predict',
          expected: '4\n255',
        },
        hints: [
          '`250 + 10` is `260`; reduce it modulo 256.',
          'Decrementing `1` twice: `1 -> 0 -> ?` — below `0` it wraps to `255`.',
        ],
      },
    },
    {
      type: 'exercise',
      ex: {
        id: 'the-byte-type-ex2',
        difficulty: 'medium',
        prompt: `Demonstrate \`byte\` wraparound yourself. Add two byte values that sum past \`255\` so the result rolls over, and print **only** the wrapped result.

Make your program print exactly:

\`\`\`
44
\`\`\`

(Hint: \`200 + 100\` is \`300\`, and \`300\` modulo \`256\` is \`44\`.)`,
        starter: `int main() {
    // build two bytes that overflow when added, then print the result

    return 0;
}`,
        check: {
          kind: 'output',
          expected: '44',
        },
        hints: [
          'Cast each operand to `byte`, e.g. `byte a = (byte)200;`.',
          'Adding two `byte` values keeps the result a `byte`, so it wraps automatically.',
        ],
        solution: `int main() {
    byte a = (byte)200;
    byte b = (byte)100;
    print(a + b);
    return 0;
}`,
      },
    },
  ],
} satisfies Lesson
