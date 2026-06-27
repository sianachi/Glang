import type { Lesson } from '../../types.ts'

export default {
  id: 'comments',
  title: 'Comments',
  blurb: 'Leave notes for humans: line comments, block comments, and why they never nest.',
  blocks: [
    {
      type: 'prose',
      md: `Comments are text the compiler ignores. They exist purely for the humans reading your code. Glang has two kinds, both borrowed from C.

A **line comment** starts with \`//\` and runs to the end of the line:

A **block comment** is wrapped in \`/* ... */\` and can span multiple lines.`,
    },
    {
      type: 'run',
      caption: 'comments.lang',
      code: `int main() {
    // This whole line is ignored.
    print("visible");   // a trailing comment after a statement

    /* A block comment
       can stretch across
       several lines. */
    print("also visible");
    return 0;
}`,
    },
    {
      type: 'prose',
      md: `Run it: only the two \`print\` calls produce output. The comments — including the trailing one — change nothing. You can drop a comment anywhere whitespace is allowed: on its own line, at the end of a statement, or in the middle of an expression with a block comment.`,
    },
    {
      type: 'callout',
      tone: 'gotcha',
      md: `**Block comments do not nest.** A \`/* ... */\` block ends at the **first** \`*/\` it finds, no matter how many \`/*\` came before it. So this:

\`\`\`
/* outer /* inner */ still code here */
\`\`\`

closes at the first \`*/\` — the text \`still code here */\` is back to being real code, and will almost certainly cause a syntax error. To comment out a region that already contains a block comment, use \`//\` line comments instead.`,
    },
    {
      type: 'prose',
      md: `Because comments are stripped before anything else runs, you can use them to temporarily disable a line of code while you experiment — just put \`//\` in front of it.`,
    },
    {
      type: 'exercise',
      ex: {
        id: 'comments-ex1',
        difficulty: 'intro',
        prompt: `**Predict the output.** Read the program carefully — remember that \`//\` runs to the end of the line and a block comment ends at the first \`*/\`. Type exactly what it prints.`,
        code: `int main() {
    print("a");
    // print("b");
    print("c"); /* print("d"); */
    /* print("e");
       print("f"); */
    print("g");
    return 0;
}`,
        check: {
          kind: 'predict',
          expected: 'a\nc\ng',
        },
        hints: [
          'The `// print("b");` line is entirely a comment, so it prints nothing.',
          'Everything between `/*` and the next `*/` is ignored, including the lines printing `e` and `f`.',
        ],
      },
    },
  ],
} satisfies Lesson
