import type { Lesson } from '../../types.ts'

export default {
  id: 'declarations',
  title: 'Variable Declarations',
  blurb: 'Declare a variable with its type and a starting value — both are required.',
  blocks: [
    {
      type: 'prose',
      md: `A variable in Glang is introduced by a **declaration**: a type, a name, and a starting value.

\`\`\`
int score = 100;
\`\`\`

Read it left to right: the type \`int\`, the name \`score\`, then \`= 100\` gives it an initial value. Every declaration follows this same shape.`,
    },
    {
      type: 'run',
      caption: 'declare.lang',
      code: `int main() {
    int score = 100;
    float pi = 3.14;
    bool ready = true;
    string name = "Rex";

    print(score);
    print(pi);
    print(ready);
    print(name);
    return 0;
}`,
    },
    {
      type: 'prose',
      md: `Glang is **statically typed**, so the type is part of the declaration — there is no \`var\` or type inference. Two rules follow from this and they are both enforced at compile time:

1. **The type is required.** You always write \`int\`, \`float\`, \`bool\`, \`char\`, \`byte\`, or \`string\` (or a class/enum type) before the name.
2. **An initialiser is required.** A declaration with no value, like \`int x;\`, is a compile error — there is no "uninitialised" state for a Glang variable.`,
    },
    {
      type: 'static',
      caption: 'uninitialised.lang (does NOT compile)',
      code: `int main() {
    int x;        // error: declaration must have an initialiser
    x = 5;
    print(x);
    return 0;
}`,
      output: 'Compile error: variable \'x\' is declared without an initialiser',
    },
    {
      type: 'prose',
      md: `Once a variable exists, you assign to it with \`=\` as often as you like — that is just assignment, not a new declaration. You only give the type the **first** time.`,
    },
    {
      type: 'run',
      caption: 'reassign.lang',
      code: `int main() {
    int count = 1;
    print(count);

    count = 2;
    count = count + 10;
    print(count);
    return 0;
}`,
    },
    {
      type: 'prose',
      md: `### One variable per statement

Each declaration introduces exactly **one** variable. C-style comma lists like \`int x = 1, y = 2;\` are not allowed — write a separate statement for each.`,
    },
    {
      type: 'run',
      caption: 'one-per-line.lang',
      code: `int main() {
    int x = 1;
    int y = 2;
    print(x + y);
    return 0;
}`,
    },
    {
      type: 'callout',
      tone: 'gotcha',
      md: `Two declaration mistakes the compiler rejects:

- **No multiple declarations.** \`int x = 1, y = 2;\` is an error — give each variable its own statement.
- **No uninitialised variables.** \`int x;\` is an error — every variable must be given a value as it is declared.`,
    },
    {
      type: 'exercise',
      ex: {
        id: 'declarations-ex1',
        difficulty: 'intro',
        prompt: `Declare three variables and print each on its own line:

- a \`string\` named \`title\` holding \`"Glang"\`
- an \`int\` named \`year\` holding \`2026\`
- a \`bool\` named \`stable\` holding \`false\`

Expected output:

\`\`\`
Glang
2026
false
\`\`\``,
        starter: `int main() {
    // declare title, year, and stable, then print each

    return 0;
}`,
        check: {
          kind: 'output',
          expected: 'Glang\n2026\nfalse',
        },
        hints: [
          'Each declaration is `type name = value;` — one variable per statement.',
          'Remember the type comes first: `string title = "Glang";`.',
        ],
        solution: `int main() {
    string title = "Glang";
    int year = 2026;
    bool stable = false;
    print(title);
    print(year);
    print(stable);
    return 0;
}`,
      },
    },
    {
      type: 'exercise',
      ex: {
        id: 'declarations-ex2',
        difficulty: 'easy',
        prompt: `**Predict the output.** The variable \`total\` is declared once, then reassigned. Type exactly what this prints.`,
        code: `int main() {
    int total = 5;
    print(total);
    total = total + 5;
    print(total);
    total = 100;
    print(total);
    return 0;
}`,
        check: {
          kind: 'predict',
          expected: '5\n15\n100',
        },
        hints: [
          'The type `int` appears only on the first line — the rest are assignments.',
          'Each `print` shows the value of `total` at that moment.',
        ],
      },
    },
  ],
} satisfies Lesson
