import type { Lesson } from '../../types.ts'

export default {
  id: 'imports',
  title: 'Imports & Modules',
  blurb: 'Split a program across files with `import`, and pull in the bundled standard library with the `std/` prefix.',
  blocks: [
    {
      type: 'prose',
      md: `A Glang program rarely lives in one file. The **\`import\`** statement pulls another source file into the current one:

\`\`\`
import "path/to/file.lang";
\`\`\`

Importing a file makes **all of its top-level declarations** — functions, classes, enums, interfaces, namespaces — visible in the importing file, exactly as if you could see into it. There is no per-symbol export list: everything at the top level is shared.`,
    },
    {
      type: 'callout',
      tone: 'note',
      md: `Import paths are **relative to the source file** doing the importing, not to the current working directory. So \`import "util/strings.lang";\` looks for \`util/strings.lang\` sitting next to the file that wrote that line.`,
    },
    {
      type: 'prose',
      md: `Here is a two-file program. \`mathlib.lang\` defines a helper; \`main.lang\` imports it and calls the helper as if it were local.`,
    },
    {
      type: 'static',
      caption: 'mathlib.lang',
      code: `int square(int n) {
    return n * n;
}

int cube(int n) {
    return n * n * n;
}`,
      output: '',
    },
    {
      type: 'static',
      caption: 'main.lang',
      code: `import "mathlib.lang";

int main() {
    print(square(5));
    print(cube(3));
    return 0;
}`,
      output: '25\n27',
    },
    {
      type: 'prose',
      md: `Because \`mathlib.lang\` was imported, both \`square\` and \`cube\` are in scope inside \`main\`. The helper file has no \`main\` of its own — a module that only exports declarations is perfectly valid.`,
    },
    {
      type: 'prose',
      md: `### Two rules the compiler enforces

- **Circular imports are a compile error.** If \`a.lang\` imports \`b.lang\` and \`b.lang\` imports \`a.lang\`, the compiler rejects the program rather than looping forever.
- **Duplicate imports are silently ignored.** If the same file is imported more than once — directly, or transitively through several other modules — it is loaded exactly once. This is *include-guard* behaviour: importing a widely-used module from many places is safe and cheap.`,
    },
    {
      type: 'callout',
      tone: 'tip',
      md: `Because of the include-guard, you never need to worry about "have I already imported this?" — just \`import\` what you depend on in each file. The loader de-duplicates for you.`,
    },
    {
      type: 'prose',
      md: `### The \`std/\` prefix

An import path that begins with **\`std/\`** is special: it resolves against the bundled **standard-library directory**, not against the importing file's folder — and it does so *regardless of the current working directory*.

\`\`\`
import "std/list.lang";   // resolves to <project>/stdlib/list.lang
import "std/math.lang";
\`\`\`

So \`import "std/math.lang";\` always finds the shipped \`math\` module no matter where your program sits on disk.`,
    },
    {
      type: 'static',
      caption: 'totals.lang',
      code: `import "std/math.lang";

int main() {
    print(math::abs(-9));
    print(math::max(4, 7));
    return 0;
}`,
      output: '9\n7',
    },
    {
      type: 'callout',
      tone: 'note',
      md: `The standard library's *function* modules (\`math\`, \`chars\`, \`strings\`, \`io\`) live inside namespaces, so you call them as \`math::abs(x)\`. The *collection* classes (\`List\`, \`Map\`, …) are global once imported. You'll meet namespaces in the next lesson and tour the stdlib later.`,
    },
    {
      type: 'callout',
      tone: 'gotcha',
      md: `The file-I/O built-ins \`readFile\`, \`writeFile\`, and \`fileExists\` are part of the runtime — they need **no** import. But the richer \`io::\` helpers (\`appendFile\`, \`dieWith\`, …) live in \`std/io.lang\` and **do** require \`import "std/io.lang";\`.`,
    },
    {
      type: 'exercise',
      ex: {
        id: 'imports-ex1',
        difficulty: 'easy',
        prompt: `**Predict the output.** Two files. \`greet.lang\` defines helpers; \`app.lang\` imports it. Type exactly what running \`app.lang\` prints.

\`\`\`
// greet.lang
string greeting(string who) {
    return "Hi, " + who;
}

int loud(int n) {
    return n * 100;
}
\`\`\``,
        code: `import "greet.lang";

int main() {
    print(greeting("Ada"));
    print(loud(3));
    return 0;
}`,
        check: {
          kind: 'predict',
          expected: 'Hi, Ada\n300',
        },
        hints: [
          'Importing `greet.lang` makes both `greeting` and `loud` visible in `app.lang`.',
          '`greeting("Ada")` concatenates `"Hi, "` and `"Ada"`; `loud(3)` is `3 * 100`.',
        ],
      },
    },
    {
      type: 'exercise',
      ex: {
        id: 'imports-ex2',
        difficulty: 'medium',
        prompt: `**Predict the output.** \`b.lang\` imports \`a.lang\`, and \`main.lang\` imports **both** \`a.lang\` and \`b.lang\`. Remember the include-guard: each file loads exactly once, so this is legal and \`a.lang\` is shared, not duplicated.

\`\`\`
// a.lang
int base() { return 10; }

// b.lang
import "a.lang";
int boosted() { return base() + 5; }
\`\`\``,
        code: `import "a.lang";
import "b.lang";

int main() {
    print(base());
    print(boosted());
    return 0;
}`,
        check: {
          kind: 'predict',
          expected: '10\n15',
        },
        hints: [
          'Even though `a.lang` is reachable twice (directly, and through `b.lang`), the include-guard loads it once — no error.',
          '`base()` is `10`; `boosted()` is `base() + 5`.',
        ],
      },
    },
  ],
} satisfies Lesson
