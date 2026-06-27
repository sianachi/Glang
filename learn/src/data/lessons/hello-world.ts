import type { Lesson } from '../../types.ts'

// Exemplar lesson — the canonical shape every lesson file follows.
export default {
  id: 'hello-world',
  title: 'Hello, Glang',
  blurb: 'Your first program: main, print, and the exit code.',
  blocks: [
    {
      type: 'prose',
      md: `Every Glang program starts at a single function named **\`main\`**. It returns an \`int\` — the process exit code, where \`0\` means success.

The runtime gives you exactly one built-in for output: **\`print\`**. It writes one value followed by a newline. Let's run the smallest complete program.`,
    },
    {
      type: 'run',
      caption: 'hello.lang',
      code: `int main() {
    print("Hello, Glang!");
    return 0;
}`,
    },
    {
      type: 'prose',
      md: `Press **Run** above — the code is editable, so change the message and run it again.

A few things are already visible here:
- Statements end with a semicolon \`;\`.
- String literals use double quotes.
- The function body is wrapped in braces \`{ }\`.
- \`return 0;\` hands the exit code back to the operating system.`,
    },
    {
      type: 'callout',
      tone: 'note',
      md: `\`print\` takes **exactly one** argument of a primitive type (\`int\`, \`float\`, \`bool\`, \`char\`, \`byte\`, or \`string\`) and returns \`void\`. It is not a keyword and cannot be redefined, but it is also not variadic — \`print("x", "y")\` is an error.`,
    },
    {
      type: 'prose',
      md: `\`print\` adapts to the type you give it. A \`bool\` prints as \`true\`/\`false\`, a \`char\` prints as its character, and a \`byte\` prints as its numeric value (\`0..255\`).`,
    },
    {
      type: 'run',
      caption: 'kinds.lang',
      code: `int main() {
    print(42);
    print(3.14);
    print(true);
    print('a');
    print("hello");
    return 0;
}`,
    },
    {
      type: 'exercise',
      ex: {
        id: 'hello-world-ex1',
        difficulty: 'intro',
        prompt: `Write a program that prints these three lines, in order:

\`\`\`
Glang
is
fun
\`\`\`

Use three \`print\` calls.`,
        starter: `int main() {
    // print three lines here

    return 0;
}`,
        check: {
          kind: 'output',
          expected: 'Glang\nis\nfun',
        },
        hints: [
          'Each `print` call writes its own line automatically — you do not need to add `\\n`.',
          'You need exactly three `print` statements, one per word.',
        ],
        solution: `int main() {
    print("Glang");
    print("is");
    print("fun");
    return 0;
}`,
      },
    },
    {
      type: 'exercise',
      ex: {
        id: 'hello-world-ex2',
        difficulty: 'intro',
        prompt: `**Predict the output.** Read the program and type exactly what it prints.`,
        code: `int main() {
    print('G');
    print(7 + 5);
    print(false);
    return 0;
}`,
        check: {
          kind: 'predict',
          expected: 'G\n12\nfalse',
        },
        hints: ['`7 + 5` is evaluated before printing.', 'A `char` prints as its letter; a `bool` prints as `true`/`false`.'],
      },
    },
  ],
} satisfies Lesson
