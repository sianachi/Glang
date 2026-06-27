import type { Lesson } from '../../types.ts'

export default {
  id: 'running-programs',
  title: 'Running a Program',
  blurb: 'The main entry point, exit codes, and the two ways to run Glang code.',
  blocks: [
    {
      type: 'prose',
      md: `Every Glang program must define **exactly one** function named \`main\`:

\`\`\`
int main() {
    // ...
    return 0;
}
\`\`\`

Execution starts there. The \`int\` it returns is the **process exit code** handed back to the operating system: \`0\` means success, and any non-zero value signals an error.`,
    },
    {
      type: 'callout',
      tone: 'note',
      md: `There is exactly one \`main\`, it takes no parameters (v1 has no command-line arguments), and it returns \`int\`. Forgetting the \`return\`, or returning the wrong type, is a compile-time error.`,
    },
    {
      type: 'prose',
      md: `### The exit code matters

The number you \`return\` from \`main\` *is* the program's result. Run this — it prints a line and then reports exit code \`0\`:`,
    },
    {
      type: 'run',
      caption: 'ok.lang',
      code: `int main() {
    print("doing work...");
    print("done");
    return 0;
}`,
    },
    {
      type: 'prose',
      md: `Now consider a program that decides its own exit code. By convention \`0\` is success and a non-zero code reports a specific failure. Here we return \`2\` when an input is invalid:`,
    },
    {
      type: 'run',
      caption: 'exitcode.lang',
      code: `int main() {
    int input = -5;
    if (input < 0) {
        print("invalid input");
        return 2;
    }
    print("ok");
    return 0;
}`,
    },
    {
      type: 'callout',
      tone: 'tip',
      md: `The exit code is how a shell or another program knows whether yours succeeded. On a terminal you can inspect it with \`echo $?\` right after the program runs. Pick small, meaningful non-zero codes for distinct failures; reserve \`0\` for success.`,
    },
    {
      type: 'prose',
      md: `### The two ways to run it

The same \`.lang\` file can be executed two ways, and both share one front-end so the behaviour matches.

**1. The interpreter (Python reference).** Fast to start, no build step:

\`\`\`
python3 main.py run path/to/program.lang
\`\`\`

**2. The self-hosted compiler.** Translate the program to C, then compile that C to a native binary:

\`\`\`
./glangc path/to/program.lang out.c
gcc out.c runtime/glang_runtime.c -o program
./program
\`\`\`

The first is ideal while learning and iterating; the second produces a standalone, fast executable.`,
    },
    {
      type: 'callout',
      tone: 'note',
      md: `Ready-to-run example programs live in the \`examples/\` directory, each paired with a golden-output file. They are a good place to see idiomatic Glang once you have the basics.`,
    },
    {
      type: 'exercise',
      ex: {
        id: 'running-programs-ex1',
        difficulty: 'intro',
        prompt: `Write a \`main\` that prints the word \`start\`, then prints \`finish\`, and returns the success exit code.

Expected output:

\`\`\`
start
finish
\`\`\``,
        starter: `int main() {
    // print two lines, then return success

    return 0;
}`,
        check: {
          kind: 'output',
          expected: 'start\nfinish',
        },
        hints: [
          'Use two `print` calls — each writes its own line.',
          'Success is `return 0;` — the lines you print are separate from the exit code.',
        ],
        solution: `int main() {
    print("start");
    print("finish");
    return 0;
}`,
      },
    },
    {
      type: 'exercise',
      ex: {
        id: 'running-programs-ex2',
        difficulty: 'easy',
        prompt: `**Predict the output.** This program returns a non-zero exit code, but the exit code is *not* printed. Type exactly the text it prints to the screen.`,
        code: `int main() {
    int code = 3;
    print("checking");
    if (code != 0) {
        print("failed");
        return code;
    }
    print("passed");
    return 0;
}`,
        check: {
          kind: 'predict',
          expected: 'checking\nfailed',
        },
        hints: [
          'The return value becomes the exit code; it is not written to output.',
          'Once a `return` runs, the function stops — later prints never happen.',
        ],
      },
    },
  ],
} satisfies Lesson
