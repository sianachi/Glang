import type { Lesson } from '../../types.ts'

export default {
  id: 'primitives',
  title: 'Primitive Types',
  blurb: 'Glang has six built-in primitive types plus null — each with its own rules and no implicit conversions.',
  blocks: [
    {
      type: 'prose',
      md: `Glang gives you a small, sharp set of **primitive types**. Each one means exactly one thing, and the type checker keeps them apart — Glang never silently converts one to another. Here is the whole table:

| Type | Representation | Notes |
|---|---|---|
| \`int\` | 64-bit signed | integer division when both operands are \`int\` |
| \`float\` | 64-bit IEEE 754 | decimal numbers |
| \`bool\` | 1 byte | **not** an alias of \`int\` |
| \`char\` | 1 byte | ASCII *text*, not arithmetic |
| \`byte\` | unsigned 8-bit | an octet for binary data (\`0..255\`) |
| \`string\` | heap pointer + length | immutable; \`+\` builds a new string |
| \`null\` | — | only for pointer / object types |

Let's meet each one.`,
    },
    {
      type: 'prose',
      md: `### int — whole numbers

An \`int\` is a 64-bit signed integer. The one surprise from other languages: when **both** operands of \`/\` are \`int\`, you get *integer division* (the fractional part is dropped). \`%\` gives the remainder.`,
    },
    {
      type: 'run',
      caption: 'ints.lang',
      code: `int main() {
    int a = 7;
    int b = 2;
    print(a / b);   // integer division: 3, not 3.5
    print(a % b);   // remainder: 1
    print(a * b);   // 14
    return 0;
}`,
    },
    {
      type: 'prose',
      md: `### float — decimal numbers

A \`float\` is a 64-bit IEEE 754 number. Division between floats keeps the fraction. When \`print\` shows a whole-valued float, it still prints one decimal place, so \`10.0\` prints as \`10.0\`.`,
    },
    {
      type: 'run',
      caption: 'floats.lang',
      code: `int main() {
    float x = 7.0;
    float y = 2.0;
    print(x / y);   // 3.5
    print(10.0);    // 10.0  (one decimal place is always shown)
    return 0;
}`,
    },
    {
      type: 'prose',
      md: `### bool — true or false

A \`bool\` is \`true\` or \`false\`. It occupies one byte, but it is **not** an alias for \`int\`: you cannot use an \`int\` where a \`bool\` is expected, and an \`int\` is never "truthy". Logical operators (\`&& || !\`) and comparisons (\`== < >= …\`) all work on \`bool\`.`,
    },
    {
      type: 'run',
      caption: 'bools.lang',
      code: `int main() {
    bool ok = true;
    bool done = false;
    print(ok);              // true
    print(ok && !done);     // true
    print(3 < 5);           // a comparison yields a bool: true
    return 0;
}`,
    },
    {
      type: 'prose',
      md: `### char — a single text character

A \`char\` holds one ASCII character and is written with single quotes: \`'a'\`. It is *text*, not a number — you do not do arithmetic on a \`char\` directly. When you genuinely need its code point, cast it explicitly with \`(int)\` (covered in the casting lesson).`,
    },
    {
      type: 'run',
      caption: 'chars.lang',
      code: `int main() {
    char first = 'G';
    char last = '!';
    print(first);       // G
    print(last);        // !
    print((int)first);  // 71  (explicit cast to its code point)
    return 0;
}`,
    },
    {
      type: 'prose',
      md: `### byte — an unsigned octet

A \`byte\` is an unsigned 8-bit integer, so it ranges \`0..255\`. It is the building block for binary data — buffers and octets. It is distinct from both \`int\` and \`char\`, and its arithmetic *wraps* around at 256. \`print\` shows a \`byte\` as its numeric value.`,
    },
    {
      type: 'run',
      caption: 'bytes.lang',
      code: `int main() {
    byte b = 16;        // an int literal in 0..255 fits a byte directly
    print(b);           // 16
    return 0;
}`,
    },
    {
      type: 'callout',
      tone: 'note',
      md: `\`byte\` has a few special rules — wraparound, literal coercion, and how it refuses to mix with \`int\` — that deserve their own lesson. The next lesson, **The byte Type**, covers them in full.`,
    },
    {
      type: 'prose',
      md: `### string — immutable text

A \`string\` is a heap value (a pointer plus a length) written with double quotes. Strings are **immutable**: you never modify one in place. The \`+\` operator *concatenates* by allocating a brand-new string from its operands.`,
    },
    {
      type: 'run',
      caption: 'strings.lang',
      code: `int main() {
    string hello = "Hello";
    string who = "Glang";
    string msg = hello + ", " + who + "!";  // builds a new string
    print(msg);                              // Hello, Glang!
    return 0;
}`,
    },
    {
      type: 'prose',
      md: `### null — the absence of a pointer

\`null\` is special: it is only assignable to **pointer or object types**, never to a plain \`int\`, \`float\`, \`bool\`, \`char\`, or \`byte\`. A bare primitive always holds a real value. (To let a primitive be absent you use a *nullable* type like \`int?\`, covered in a later lesson.)`,
    },
    {
      type: 'static',
      caption: 'null.lang',
      code: `int main() {
    int* p = null;      // ok: null fits a pointer type
    int x = null;       // ERROR: 'int' is not a pointer type
    return 0;
}`,
      output: `error: cannot assign 'null' to 'int'`,
    },
    {
      type: 'callout',
      tone: 'gotcha',
      md: `**Glang performs no implicit conversions.** An \`int\` is not a \`bool\`, a \`char\` is not an \`int\`, a \`byte\` is not an \`int\`. Code like \`if (5)\` is an error — integers are **not** truthy; \`if\` needs an actual \`bool\`. Whenever you want to move a value between types, you write an explicit cast like \`(int)\` or \`(float)\`.`,
    },
    {
      type: 'exercise',
      ex: {
        id: 'primitives-ex1',
        difficulty: 'intro',
        prompt: `**Predict the output.** Read the program and type exactly what it prints.

Remember: \`int / int\` is integer division, and a whole-valued \`float\` prints with one decimal place.`,
        code: `int main() {
    print(9 / 4);
    print(9.0 / 4.0);
    print('Z');
    print("a" + "b");
    print(true && false);
    return 0;
}`,
        check: {
          kind: 'predict',
          expected: '2\n2.25\nZ\nab\nfalse',
        },
        hints: [
          '`9 / 4` uses integer division because both operands are `int`.',
          '`9.0 / 4.0` are floats, so the fraction is kept.',
          '`+` on two strings concatenates them into one.',
        ],
      },
    },
    {
      type: 'exercise',
      ex: {
        id: 'primitives-ex2',
        difficulty: 'easy',
        prompt: `Declare one variable of **each** of these types and print them in this order:

\`\`\`
42
3.5
true
Q
hi
\`\`\`

Use an \`int\`, a \`float\`, a \`bool\`, a \`char\`, and a \`string\` — one \`print\` per value.`,
        starter: `int main() {
    // declare and print: int, float, bool, char, string

    return 0;
}`,
        check: {
          kind: 'output',
          expected: '42\n3.5\ntrue\nQ\nhi',
        },
        hints: [
          'A `char` literal uses single quotes (`\'Q\'`); a `string` uses double quotes (`"hi"`).',
          'A `float` literal needs a decimal point, e.g. `3.5`.',
        ],
        solution: `int main() {
    int n = 42;
    float f = 3.5;
    bool b = true;
    char c = 'Q';
    string s = "hi";
    print(n);
    print(f);
    print(b);
    print(c);
    print(s);
    return 0;
}`,
      },
    },
  ],
} satisfies Lesson
