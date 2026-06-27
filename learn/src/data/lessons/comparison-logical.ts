import type { Lesson } from '../../types.ts'

export default {
  id: 'comparison-logical',
  title: 'Comparison & Logical Operators',
  blurb: 'Build conditions with comparisons and combine them with short-circuit logic.',
  blocks: [
    {
      type: 'prose',
      md: `Conditions are made of two ingredients: **comparisons** that ask a yes/no question about values, and **logical operators** that combine those answers. Both produce a \`bool\` — and in Glang only a \`bool\` is allowed where a condition is expected.`,
    },
    {
      type: 'prose',
      md: `## Comparison operators

There are six, and **every one of them returns \`bool\`**:

- \`==\` equal to
- \`!=\` not equal to
- \`<\` less than
- \`>\` greater than
- \`<=\` less than or equal to
- \`>=\` greater than or equal to`,
    },
    {
      type: 'run',
      caption: 'compare.lang',
      code: `int main() {
    int a = 7;
    int b = 10;
    print(a < b);
    print(a == b);
    print(a != b);
    print(a >= 7);
    return 0;
}`,
    },
    {
      type: 'prose',
      md: `## Comparing pointers

Comparison also works on pointers. **Comparing a pointer to \`null\` is valid** — it is the normal way to check whether a pointer points at anything:

\`\`\`c
if (p == null) {
    // nothing to dereference
}
\`\`\`

**Comparing two pointers checks address equality** — \`p == q\` is \`true\` only when both hold the same address, not when the values they point at happen to be equal.`,
    },
    {
      type: 'callout',
      tone: 'note',
      md: `Pointer comparison is about *identity*, not contents. \`p == q\` asks "do these point at the same storage location?" To compare the values behind two pointers, dereference first: \`*p == *q\`.`,
    },
    {
      type: 'prose',
      md: `## Logical operators

Use these to combine \`bool\` values:

- \`&&\` — AND, true only when both sides are true
- \`||\` — OR, true when either side is true
- \`!\` — NOT, flips a \`bool\`

\`&&\` and \`||\` **short-circuit**: \`&&\` stops at the first \`false\`, and \`||\` stops at the first \`true\`, so the right-hand side is not evaluated when the answer is already decided.`,
    },
    {
      type: 'run',
      caption: 'logic.lang',
      code: `int main() {
    bool sunny = true;
    bool warm = false;
    print(sunny && warm);
    print(sunny || warm);
    print(!warm);
    print(sunny && !warm);
    return 0;
}`,
    },
    {
      type: 'callout',
      tone: 'gotcha',
      md: `**Integers are not truthy.** Logical operators and conditions require \`bool\` operands. Writing \`if (5)\` or \`if (count)\` is a **type error** — there is no implicit "non-zero means true" rule like in C. Compare explicitly instead: \`if (count != 0)\`.`,
    },
    {
      type: 'run',
      caption: 'explicit.lang',
      code: `int main() {
    int count = 3;
    // Wrong: if (count) { ... }  -- count is an int, not a bool
    if (count != 0) {
        print("not empty");
    }
    return 0;
}`,
    },
    {
      type: 'exercise',
      ex: {
        id: 'comparison-logical-ex1',
        difficulty: 'easy',
        prompt: `A value is "in range" when it is at least \`10\` **and** at most \`20\`. Complete the program so it prints \`true\` for \`x = 15\`.

Use a single \`&&\` expression in the condition.`,
        starter: `int main() {
    int x = 15;
    bool inRange = false; // replace with the right comparison
    print(inRange);
    return 0;
}`,
        check: {
          kind: 'output',
          expected: 'true',
        },
        hints: [
          'You need two comparisons joined with `&&`: one for the lower bound, one for the upper.',
          'Try `x >= 10 && x <= 20`.',
        ],
        solution: `int main() {
    int x = 15;
    bool inRange = x >= 10 && x <= 20;
    print(inRange);
    return 0;
}`,
      },
    },
    {
      type: 'exercise',
      ex: {
        id: 'comparison-logical-ex2',
        difficulty: 'easy',
        prompt: `**Predict the output.** Read the program and type exactly what it prints (one value per line).`,
        code: `int main() {
    int a = 4;
    int b = 9;
    print(a < b);
    print(a == b);
    print(!(a < b));
    print(a < b || a > b);
    return 0;
}`,
        check: {
          kind: 'predict',
          expected: 'true\nfalse\nfalse\ntrue',
        },
        hints: [
          'Each comparison produces `true` or `false` independently.',
          '`!(a < b)` flips the result of `a < b`.',
        ],
      },
    },
  ],
} satisfies Lesson
