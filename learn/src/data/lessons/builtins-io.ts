import type { Lesson } from '../../types.ts'

export default {
  id: 'builtins-io',
  title: 'Built-in Functions & I/O',
  blurb: 'The runtime functions you get for free: print, string helpers, and file I/O.',
  blocks: [
    {
      type: 'prose',
      md: `Glang's runtime ships a small set of **built-in functions** that are always available — no \`import\` required. You have already met \`print\`, which writes one primitive value followed by a newline. This lesson covers the rest: string helpers you can run right here, and file/byte helpers that touch the filesystem.`,
    },
    {
      type: 'prose',
      md: `### String built-ins

These operate on \`string\` values and return new values (Glang strings are immutable, so nothing is modified in place):

- \`len(s)\` → \`int\`, the number of characters.
- \`substr(s, start)\` / \`substr(s, start, length)\` → a slice of \`s\`.
- \`indexOf(s, needle)\` → \`int\`, the first index of \`needle\` (\`-1\` if absent).
- \`startsWith(s, p)\`, \`endsWith(s, p)\`, \`contains(s, p)\` → \`bool\`.
- \`parseInt(s)\` → \`int\`, \`parseFloat(s)\` → \`float\`.
- \`toString(v)\` → the textual form of any primitive \`v\`.`,
    },
    {
      type: 'run',
      caption: 'strings.lang',
      code: `int main() {
    string s = "Glang rocks";
    print(len(s));
    print(substr(s, 0, 5));
    print(indexOf(s, "rocks"));
    print(startsWith(s, "Glang"));
    print(contains(s, "zzz"));
    return 0;
}`,
    },
    {
      type: 'prose',
      md: `\`parseInt\` and \`parseFloat\` turn text into numbers, and \`toString\` goes the other way — handy for building messages out of numbers.`,
    },
    {
      type: 'run',
      caption: 'convert.lang',
      code: `int main() {
    int n = parseInt("42");
    float f = parseFloat("3.5");
    print(n + 8);
    print(f * 2.0);
    print("n = " + toString(n));
    return 0;
}`,
    },
    {
      type: 'callout',
      tone: 'note',
      md: `\`substr(s, start, length)\` takes a **length**, not an end index: \`substr("Glang rocks", 0, 5)\` is \`"Glang"\`. With only two arguments, \`substr(s, start)\` runs to the end of the string.`,
    },
    {
      type: 'prose',
      md: `### File I/O built-ins

The runtime also provides three file helpers that operate on paths relative to the process working directory:

- \`writeFile(path, contents)\` → \`void\` — writes (or overwrites) a file.
- \`fileExists(path)\` → \`bool\`.
- \`readFile(path)\` → \`string\` — reads the whole file; errors if it is missing.

These touch the real filesystem, so the in-browser runner cannot execute them. The example below shows how they fit together (output shown is what it would print when run natively).`,
    },
    {
      type: 'static',
      caption: 'files.lang',
      code: `int main() {
    writeFile("greeting.txt", "hello\\n");
    if (fileExists("greeting.txt")) {
        string s = readFile("greeting.txt");
        print(s);
    }
    return 0;
}`,
      output: `hello
`,
    },
    {
      type: 'prose',
      md: `### Byte interop built-ins

Two more built-ins bridge \`string\` and raw \`byte\` blocks:

- \`bytesFromString(s)\` → \`byte*\` — allocates a **heap** block holding the string's code units (masked to 8 bits). The caller **owns** it and must \`free\` it.
- \`stringFromBytes(bs, len)\` → \`string\` — rebuilds a string from the first \`len\` bytes (an out-of-bounds \`len\` is a runtime error).

Because they allocate heap memory and work with pointers, these are not available in the in-browser runner.`,
    },
    {
      type: 'static',
      caption: 'bytes.lang',
      code: `int main() {
    byte* bs = bytesFromString("Hi!");
    string s = stringFromBytes(bs, 3);
    print(s);
    free(bs);
    return 0;
}`,
      output: `Hi!`,
    },
    {
      type: 'callout',
      tone: 'warn',
      md: `\`bytesFromString\` hands you an owned heap block — you must \`free\` it exactly once when done, or you leak memory. Higher-level, line-oriented helpers built on these primitives live in \`std/io.lang\`.`,
    },
    {
      type: 'exercise',
      ex: {
        id: 'builtins-io-ex1',
        difficulty: 'easy',
        prompt: `Given \`string s = "interactive"\`, print its length, then print \`true\` if it ends with \`"active"\`.

Expected output:

\`\`\`
11
true
\`\`\``,
        starter: `int main() {
    string s = "interactive";
    // print len(s)
    // print endsWith(s, "active")
    return 0;
}`,
        check: {
          kind: 'output',
          expected: '11\ntrue',
        },
        hints: [
          '`len(s)` gives the character count.',
          'Use `endsWith(s, "active")`, which returns a `bool`.',
        ],
        solution: `int main() {
    string s = "interactive";
    print(len(s));
    print(endsWith(s, "active"));
    return 0;
}`,
      },
    },
    {
      type: 'exercise',
      ex: {
        id: 'builtins-io-ex2',
        difficulty: 'medium',
        prompt: `Use \`indexOf\` and \`substr\` to print the part of \`"name=Ada"\` **after** the \`=\`.

Expected output:

\`\`\`
Ada
\`\`\``,
        starter: `int main() {
    string s = "name=Ada";
    int eq = indexOf(s, "=");
    // print everything after the '=' using substr
    return 0;
}`,
        check: {
          kind: 'output',
          expected: 'Ada',
        },
        hints: [
          '`indexOf(s, "=")` is `4`, the position of the `=`.',
          'Start one past it: `substr(s, eq + 1)` runs to the end of the string.',
        ],
        solution: `int main() {
    string s = "name=Ada";
    int eq = indexOf(s, "=");
    print(substr(s, eq + 1));
    return 0;
}`,
      },
    },
    {
      type: 'exercise',
      ex: {
        id: 'builtins-io-ex3',
        difficulty: 'medium',
        prompt: `**Predict the output.** Read the program and type exactly what it prints.`,
        code: `int main() {
    string s = "hello world";
    print(contains(s, "lo w"));
    print(indexOf(s, "z"));
    print(substr(s, 6));
    return 0;
}`,
        check: {
          kind: 'predict',
          expected: 'true\n-1\nworld',
        },
        hints: [
          '`contains` checks for the substring `"lo w"`, which spans the space.',
          '`indexOf` returns `-1` when the needle is absent; `substr(s, 6)` runs from index 6 to the end.',
        ],
      },
    },
  ],
} satisfies Lesson
