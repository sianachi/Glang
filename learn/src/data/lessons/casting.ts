import type { Lesson } from '../../types.ts'

export default {
  id: 'casting',
  title: 'Type Casting',
  blurb: 'Every conversion in Glang is an explicit cast — here are the ones that are allowed and exactly what each does.',
  blocks: [
    {
      type: 'prose',
      md: `Glang never converts a value's type for you. If you want a value of one type to become another, you write an **explicit cast**: the target type in parentheses in front of the value, like \`(int) f\`.

This is the deliberate flip side of the no-implicit-conversion rule. There is no surprising widening, no silent narrowing, no \`int\`/\`bool\` blurring — a conversion happens only where you typed one.`,
    },
    {
      type: 'prose',
      md: `### The allowed primitive casts

Only these conversions between primitives are legal:

- \`int <-> float\`
- \`int <-> char\`
- \`int <-> byte\`
- \`char <-> byte\`

Anything else (for example \`bool\` to \`int\`, or \`string\` to \`int\`) is **not** a cast — there is no such conversion in the language.`,
    },
    {
      type: 'prose',
      md: `### float to int truncates

Casting a \`float\` to an \`int\` drops the fractional part — it **truncates toward zero**, it does not round. So \`(int) 3.9\` is \`3\`.`,
    },
    {
      type: 'run',
      caption: 'truncate.lang',
      code: `int main() {
    float f = 3.9;
    print((int) f);        // 3  (truncated, not rounded)
    print((float) 7);      // 7.0  (int -> float)
    print((float) 7 / 2);  // 3.5 (the cast binds before /)
    return 0;
}`,
    },
    {
      type: 'callout',
      tone: 'tip',
      md: `A cast binds tighter than a binary operator. \`(float) 7 / 2\` means \`((float) 7) / 2\` → \`7.0 / 2\` → \`3.5\`, *not* \`(float)(7 / 2)\`. When in doubt, add parentheses to make the grouping obvious.`,
    },
    {
      type: 'prose',
      md: `### Casting to byte masks to 0..255

Casting *to* \`byte\` keeps only the low 8 bits — it **masks** the value into \`0..255\`. So \`(byte) 511\` is \`255\` (the low 8 bits of \`511\` are all ones), and \`(byte) 256\` is \`0\`. Going back the other way, \`(int) b\` just widens the byte to a full \`int\`.`,
    },
    {
      type: 'run',
      caption: 'mask.lang',
      code: `int main() {
    byte b = (byte) 511;   // low 8 bits -> 255
    print(b);              // 255
    print((int) b);        // 255  (byte -> int)
    print((byte) 256);     // 0    (wraps to the low 8 bits)
    return 0;
}`,
    },
    {
      type: 'prose',
      md: `### char and byte and int

A \`char\` is one byte of text, so it converts freely with \`int\` (its code point) and with \`byte\` (its raw octet). \`(int) 'A'\` is \`65\`; \`(char) 66\` is \`'B'\`; \`(byte) 'A'\` is \`65\`.`,
    },
    {
      type: 'run',
      caption: 'char-casts.lang',
      code: `int main() {
    print((int) 'A');      // 65   (char -> int)
    print((char) 66);      // B    (int  -> char)
    print((byte) 'A');     // 65   (char -> byte)
    print((char) (byte)67);// C    (byte -> char)
    return 0;
}`,
    },
    {
      type: 'prose',
      md: `### Pointer casts

Casts also work on pointers, and they too are explicit. \`void*\` is the untyped pointer that can hold any pointer value; you cast *to* \`void*\` to erase the type and *back* to a concrete pointer type to use it again.

\`\`\`
void* p = (void*) myPtr;   // erase the type
Dog*  d = (Dog*) p;        // recover a typed pointer
\`\`\`

These are static, type-level conversions — there is no value to "compute", so the in-browser runner does not execute pointer examples. They matter once you reach pointers, objects, and the memory model.`,
    },
    {
      type: 'callout',
      tone: 'gotcha',
      md: `Casting does **not** unlock conversions that don't exist. There is **no implicit widening or narrowing**, and crucially **no \`bool\` ↔ \`int\` conversion** at all — you cannot write \`(int) true\` to get \`1\`, and you cannot use an \`int\` where a \`bool\` is required. If you need a \`bool\` from a number, write a comparison such as \`n != 0\`.`,
    },
    {
      type: 'exercise',
      ex: {
        id: 'casting-ex1',
        difficulty: 'easy',
        prompt: `**Predict the output.** Apply the cast rules: \`float -> int\` truncates, casting *to* \`byte\` masks to \`0..255\`, and a cast binds before a binary operator.`,
        code: `int main() {
    print((int) 9.99);
    print((byte) 300);
    print((int) 'a');
    print((float) 5 / 2);
    return 0;
}`,
        check: {
          kind: 'predict',
          expected: '9\n44\n97\n2.5',
        },
        hints: [
          '`(int) 9.99` truncates toward zero.',
          '`(byte) 300` keeps the low 8 bits: `300 - 256 = 44`.',
          "`(int) 'a'` is the ASCII code point of lowercase a.",
          '`(float) 5 / 2` is `((float) 5) / 2` = `5.0 / 2`.',
        ],
      },
    },
    {
      type: 'exercise',
      ex: {
        id: 'casting-ex2',
        difficulty: 'medium',
        prompt: `You are given a \`float\` average and need a whole-number percentage.

Cast the float \`87.6\` to an \`int\` and print the result. Then cast the int literal \`511\` to a \`byte\` and print that. Your program should print exactly:

\`\`\`
87
255
\`\`\``,
        starter: `int main() {
    float avg = 87.6;
    // print the truncated int, then the masked byte

    return 0;
}`,
        check: {
          kind: 'output',
          expected: '87\n255',
        },
        hints: [
          'Use `(int) avg` — it truncates `87.6` to `87`.',
          'Use `(byte) 511` — masking to the low 8 bits gives `255`.',
        ],
        solution: `int main() {
    float avg = 87.6;
    print((int) avg);
    print((byte) 511);
    return 0;
}`,
      },
    },
  ],
} satisfies Lesson
