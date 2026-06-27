import type { Lesson } from '../../types.ts'

export default {
  id: 'precedence',
  title: 'Operator Precedence',
  blurb: 'Know which operators bind first — and reach for parentheses when in doubt.',
  blocks: [
    {
      type: 'prose',
      md: `When an expression mixes operators, **precedence** decides which ones bind first. \`2 + 3 * 4\` is \`14\`, not \`20\`, because \`*\` binds tighter than \`+\` — multiplication happens before addition, exactly like in ordinary maths.`,
    },
    {
      type: 'prose',
      md: `## The precedence table (high to low)

Operators higher in this list bind **more tightly**:

1. unary: \`!\` \`~\` \`++\` \`--\` \`&\` \`*\` (address-of / dereference), casts
2. \`*\` \`/\` \`%\`
3. \`+\` \`-\`
4. \`<<\` \`>>\`
5. \`<\` \`>\` \`<=\` \`>=\`
6. \`==\` \`!=\`
7. \`&\`
8. \`^\`
9. \`|\`
10. \`&&\`
11. \`||\`
12. assignment: \`=\` \`+=\` \`-=\` … \`>>=\`

A few consequences that surprise people: shifts (\`<<\` \`>>\`) bind **looser** than \`+\`, and the bitwise operators \`&\` \`^\` \`|\` bind **looser** than comparisons. So \`a & b == c\` means \`a & (b == c)\` — almost never what you want.`,
    },
    {
      type: 'callout',
      tone: 'tip',
      md: `You do not have to memorise all twelve levels. **When in doubt, parenthesise.** Explicit parentheses make intent obvious and cost nothing at runtime.`,
    },
    {
      type: 'prose',
      md: `## Precedence in action

Watch how parentheses change the result. \`*\` runs before \`+\`, and \`+\` runs before \`<<\` — adding parentheses overrides both.`,
    },
    {
      type: 'run',
      caption: 'precedence.lang',
      code: `int main() {
    print(2 + 3 * 4);
    print((2 + 3) * 4);
    print(1 << 2 + 3);
    print((1 << 2) + 3);
    return 0;
}`,
    },
    {
      type: 'prose',
      md: `Line by line:

- \`2 + 3 * 4\` → \`3 * 4\` first, then \`2 + 12\` = **14**.
- \`(2 + 3) * 4\` → parentheses force \`5 * 4\` = **20**.
- \`1 << 2 + 3\` → \`+\` binds tighter than \`<<\`, so it is \`1 << 5\` = **32**.
- \`(1 << 2) + 3\` → now the shift happens first: \`4 + 3\` = **7**.`,
    },
    {
      type: 'prose',
      md: `Logical operators sit near the bottom, and \`&&\` binds tighter than \`||\`. So \`true || false && false\` evaluates the \`&&\` first (\`false && false\` is \`false\`), leaving \`true || false\` = \`true\`.`,
    },
    {
      type: 'run',
      caption: 'logic-precedence.lang',
      code: `int main() {
    print(true || false && false);
    print(6 & 2 + 1);
    return 0;
}`,
    },
    {
      type: 'prose',
      md: `\`6 & 2 + 1\` is a classic trap: \`+\` outranks \`&\`, so it is \`6 & 3\` = **2**, not \`(6 & 2) + 1\`.`,
    },
    {
      type: 'exercise',
      ex: {
        id: 'precedence-ex1',
        difficulty: 'easy',
        prompt: `**Predict the output.** Apply the precedence rules carefully — type each printed line.`,
        code: `int main() {
    int x = 10 - 2 * 3;
    print(x);
    print(1 << 1 + 1);
    print(8 & 4 | 2);
    return 0;
}`,
        check: {
          kind: 'predict',
          expected: '4\n4\n2',
        },
        hints: [
          '`*` binds tighter than `-`, so `10 - 2 * 3` is `10 - 6`.',
          '`+` binds tighter than `<<`, and `&` binds tighter than `|`.',
        ],
      },
    },
    {
      type: 'exercise',
      ex: {
        id: 'precedence-ex2',
        difficulty: 'easy',
        prompt: `Print \`2 + 3 * 4\` exactly as written on the first line. Then, using **parentheses**, print a version that adds before multiplying so it yields \`20\`.

Expected output:

\`\`\`
14
20
\`\`\``,
        starter: `int main() {
    // print 2 + 3 * 4 as-is
    // print a parenthesised version that equals 20
    return 0;
}`,
        check: {
          kind: 'output',
          expected: '14\n20',
        },
        hints: [
          'Without parentheses `*` wins, giving 14.',
          'Wrap the addition: `(2 + 3) * 4`.',
        ],
        solution: `int main() {
    print(2 + 3 * 4);
    print((2 + 3) * 4);
    return 0;
}`,
      },
    },
  ],
} satisfies Lesson
