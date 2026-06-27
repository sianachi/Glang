import type { Lesson } from '../../types.ts'

export default {
  id: 'literals-escapes',
  title: 'Literals & Escape Sequences',
  blurb: 'Writing values directly in source: numbers, bools, chars, strings, null — and the escape codes.',
  blocks: [
    {
      type: 'prose',
      md: `A **literal** is a value written directly in your source code — \`42\`, \`3.14\`, \`true\`, \`'a'\`, \`"hi"\`, \`null\`. Each kind has its own spelling rules.

## Integer literals

Integers can be written in three bases, and you may use \`_\` as a visual separator anywhere inside the digits (it is ignored by the compiler):

- decimal: \`0\`, \`42\`, \`-7\`
- hexadecimal with a \`0x\` prefix: \`0xFF\` (= 255)
- binary with a \`0b\` prefix: \`0b1010\` (= 10)
- grouped for readability: \`1_000_000\` (= 1000000)`,
    },
    {
      type: 'run',
      caption: 'integers.lang',
      code: `int main() {
    print(0xFF);        // hex -> 255
    print(0b1010);      // binary -> 10
    print(1_000_000);   // separators -> 1000000
    print(0xCAFE);      // hex -> 51966
    return 0;
}`,
    },
    {
      type: 'prose',
      md: `## Float literals

A float has a decimal point, an exponent, or both. The exponent uses \`e\` (or \`E\`) and may be negative:

- \`3.14\`, \`-0.5\`
- \`1e10\` — scientific notation for 10000000000
- \`1.5e-3\` — for 0.0015

When \`print\` shows a float whose value is a whole number, it always includes one decimal place — so \`1e10\` prints as \`10000000000.0\`.`,
    },
    {
      type: 'run',
      caption: 'floats.lang',
      code: `int main() {
    print(3.14);     // 3.14
    print(1e10);     // 10000000000.0
    print(1.5e-3);   // 0.0015
    return 0;
}`,
    },
    {
      type: 'prose',
      md: `## Bool, null, char, and string

- **Bool** has exactly two literals: \`true\` and \`false\`.
- **Null** is the single literal \`null\` — the absence of a value.
- **Char** is a single character in single quotes: \`'a'\`, \`'9'\`, \`'\\n'\`.
- **String** is text in double quotes: \`"hello"\`.

Both chars and strings can contain **escape sequences** — a backslash followed by a code that stands for a character you cannot type directly (or that would otherwise end the literal, like a quote).`,
    },
    {
      type: 'prose',
      md: `## Escape sequences

These work inside both char literals (\`'...'\`) and string literals (\`"..."\`):

| Sequence | Meaning         |
|----------|-----------------|
| \`\\n\`     | Newline         |
| \`\\t\`     | Tab             |
| \`\\r\`     | Carriage return |
| \`\\\\\`     | Backslash       |
| \`\\"\`     | Double quote    |
| \`\\'\`     | Single quote    |
| \`\\0\`     | Null byte       |
| \`\\xHH\`   | Hex byte (two hex digits) |

So \`"say \\"hi\\""\` holds the text \`say "hi"\`, and \`"a\\tb"\` puts a tab between \`a\` and \`b\`.`,
    },
    {
      type: 'run',
      caption: 'escapes.lang',
      code: `int main() {
    print("say \\"hi\\"");   // embedded double quotes
    print("col1\\tcol2");    // a tab between the columns
    print("line1\\nline2");  // a newline splits this into two lines
    print('A');              // a plain char
    return 0;
}`,
    },
    {
      type: 'prose',
      md: `Run it: the second line shows a real tab, and \`line1\\nline2\` becomes two output lines because the \`\\n\` is an actual newline inside the string (on top of the newline \`print\` always adds).`,
    },
    {
      type: 'callout',
      tone: 'note',
      md: `The \`\\xHH\` escape names a byte by its two-digit hexadecimal code, so \`'\\x41'\` is the character \`A\` (0x41 = 65). The in-browser runner does not support \`\\xHH\`, so the example below is shown with its expected output rather than executed.`,
    },
    {
      type: 'static',
      caption: 'hexescape.lang',
      output: 'A\n65',
      code: `int main() {
    char c = '\\x41';   // 0x41 = 65 = 'A'
    print(c);           // prints the character: A
    print((int)c);      // its code point: 65
    return 0;
}`,
    },
    {
      type: 'callout',
      tone: 'gotcha',
      md: `A backslash that is not part of a valid escape is an error, so to put a *literal* backslash in a string you must double it: \`"C:\\\\path"\` holds \`C:\\path\`. Likewise, use \`\\"\` for a quote inside a string and \`\\'\` for a quote inside a char.`,
    },
    {
      type: 'exercise',
      ex: {
        id: 'literals-escapes-ex1',
        difficulty: 'easy',
        prompt: `**Predict the output.** These are all integer and float literals in different spellings. Type exactly what the program prints.`,
        code: `int main() {
    print(0x10);    // hex
    print(0b111);   // binary
    print(2_500);   // separators
    print(2.0);     // float
    return 0;
}`,
        check: {
          kind: 'predict',
          expected: '16\n7\n2500\n2.0',
        },
        hints: [
          '`0x10` is hexadecimal: 1*16 + 0 = 16. `0b111` is binary: 4 + 2 + 1 = 7.',
          'Underscores are ignored, so `2_500` is just `2500`. A whole-valued float prints with one decimal place.',
        ],
      },
    },
    {
      type: 'exercise',
      ex: {
        id: 'literals-escapes-ex2',
        difficulty: 'easy',
        prompt: `Print a single line that reads exactly:

\`\`\`
name	Ada
\`\`\`

where \`name\` and \`Ada\` are separated by a **tab** character (not spaces). Use one \`print\` call and the right escape sequence.`,
        starter: `int main() {
    // print "name", a tab, then "Ada"
    print("");
    return 0;
}`,
        check: {
          kind: 'output',
          expected: 'name\tAda',
        },
        hints: [
          'A tab is written `\\t` inside a string literal.',
          'Put it all in one string: `"name\\tAda"`.',
        ],
        solution: `int main() {
    print("name\\tAda");
    return 0;
}`,
      },
    },
  ],
} satisfies Lesson
