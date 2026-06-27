import type { Lesson } from '../../types.ts'

export default {
  id: 'if-else',
  title: 'If / Else',
  blurb: 'Branch your program with if, else if, and else.',
  blocks: [
    {
      type: 'prose',
      md: `Programs become interesting when they can make decisions. Glang uses the familiar **\`if\` / \`else if\` / \`else\`** chain. The shape is:

\`\`\`
if (condition) {
    // runs when condition is true
} else if (other) {
    // runs when other is true
} else {
    // runs otherwise
}
\`\`\`

Each branch is tested in order; the first one whose condition is \`true\` runs, and the rest are skipped.`,
    },
    {
      type: 'run',
      caption: 'sign.lang',
      code: `int main() {
    int x = -4;
    if (x > 0) {
        print("positive");
    } else if (x == 0) {
        print("zero");
    } else {
        print("negative");
    }
    return 0;
}`,
    },
    {
      type: 'prose',
      md: `The \`else if\` and \`else\` parts are optional — a bare \`if\` on its own is perfectly fine. Change \`x\` above and re-run to watch a different branch fire.`,
    },
    {
      type: 'callout',
      tone: 'gotcha',
      md: `**Braces are ALWAYS required**, even for a single-statement body. There is no brace-less \`if (c) doThing();\` form in Glang. Writing \`if (x > 0)\` followed by a lone statement is a syntax error — wrap every branch in \`{ }\`.`,
    },
    {
      type: 'callout',
      tone: 'gotcha',
      md: `The condition **must be a \`bool\`**. Unlike C, an \`int\` is not automatically "truthy". \`if (x)\` where \`x\` is an \`int\` is a type error — write an explicit comparison like \`if (x != 0)\`.`,
    },
    {
      type: 'prose',
      md: `Conditions are built from comparisons (\`==\`, \`!=\`, \`<\`, \`<=\`, \`>\`, \`>=\`) and the logical operators \`&&\` (and), \`||\` (or), and \`!\` (not). They all produce \`bool\` values, which is exactly what \`if\` wants.`,
    },
    {
      type: 'run',
      caption: 'classify.lang',
      code: `int main() {
    int age = 17;
    bool hasPass = true;

    if (age >= 18) {
        print("adult");
    } else if (age >= 13 && hasPass) {
        print("teen with pass");
    } else {
        print("denied");
    }
    return 0;
}`,
    },
    {
      type: 'exercise',
      ex: {
        id: 'if-else-ex1',
        difficulty: 'easy',
        prompt: `Complete \`main\` so it prints \`even\` when \`n\` is divisible by 2 and \`odd\` otherwise. The starter sets \`n = 7\`, so the expected output is:

\`\`\`
odd
\`\`\`

Hint: the remainder operator \`%\` gives the leftover after division.`,
        starter: `int main() {
    int n = 7;
    // print "even" or "odd"

    return 0;
}`,
        check: {
          kind: 'output',
          expected: 'odd',
        },
        hints: [
          '`n % 2` is `0` for even numbers and `1` for odd ones.',
          'Your condition must be a `bool`: write `n % 2 == 0`, not just `n % 2`.',
        ],
        solution: `int main() {
    int n = 7;
    if (n % 2 == 0) {
        print("even");
    } else {
        print("odd");
    }
    return 0;
}`,
      },
    },
    {
      type: 'exercise',
      ex: {
        id: 'if-else-ex2',
        difficulty: 'easy',
        prompt: `**Predict the output.** Read the program and type exactly what it prints.`,
        code: `int main() {
    int score = 82;
    if (score >= 90) {
        print("A");
    } else if (score >= 80) {
        print("B");
    } else if (score >= 70) {
        print("C");
    } else {
        print("F");
    }
    return 0;
}`,
        check: {
          kind: 'predict',
          expected: 'B',
        },
        hints: [
          'Branches are tested top to bottom; the first true one wins.',
          '`82 >= 90` is false, but `82 >= 80` is true.',
        ],
      },
    },
  ],
} satisfies Lesson
