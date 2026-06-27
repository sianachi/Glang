import type { Lesson } from '../../types.ts'

export default {
  id: 'identifiers-keywords',
  title: 'Identifiers & Keywords',
  blurb: 'How to name things in Glang — and the reserved words you cannot use as names.',
  blocks: [
    {
      type: 'prose',
      md: `An **identifier** is a name you give to something: a variable, a function, a class, an enum. Glang follows the classic C rule.

An identifier must **start** with a letter (\`a\`–\`z\`, \`A\`–\`Z\`) or an underscore (\`_\`), and may be **followed** by any number of letters, digits (\`0\`–\`9\`), or underscores. Written as a pattern:

\`\`\`
[a-zA-Z_][a-zA-Z0-9_]*
\`\`\`

So \`count\`, \`_temp\`, \`maxValue\`, \`row2\`, and \`HTTP_PORT\` are all valid. But \`2fast\` is not (it starts with a digit), and \`my-var\` is not (\`-\` is not allowed inside a name).`,
    },
    {
      type: 'run',
      caption: 'identifiers.lang',
      code: `int main() {
    int count = 3;
    int _hidden = 10;
    int row2 = 7;
    int HTTP_PORT = 8080;
    print(count + _hidden + row2 + HTTP_PORT);
    return 0;
}`,
    },
    {
      type: 'callout',
      tone: 'note',
      md: `Identifiers are **case-sensitive**: \`count\`, \`Count\`, and \`COUNT\` are three different names.`,
    },
    {
      type: 'prose',
      md: `## Keywords

Some words are **reserved** by the language. They have a fixed meaning and you may **not** use them as identifiers. Here is the reserved keyword list from the spec:

\`\`\`
alloc     bool      break     byte      catch     char
class     const     continue  delete    else      enum
extends   false     float     fn        for       free
if        implements  import  int       interface modifier
namespace new       null      private   protected public
return    static    string    super     this      throw
true      try       using     void      while
\`\`\`

You will recognise many of these from other lessons: type names (\`int\`, \`float\`, \`bool\`, \`char\`, \`byte\`, \`string\`, \`void\`), the literals \`true\`/\`false\`/\`null\`, and control-flow words like \`if\`, \`else\`, \`while\`, \`for\`, \`return\`, \`break\`, \`continue\`.`,
    },
    {
      type: 'callout',
      tone: 'gotcha',
      md: `Some reserved words look like perfectly ordinary variable names, which makes them easy to trip on. \`fn\` (function-pointer types), \`in\` (used by \`foreach\`), \`match\` (union pattern-matching), and \`super\` are all reserved — so \`int fn = 3;\` or \`string match = "x";\` will **not** compile. The toolchain also reserves a few words beyond the table above, including \`var\`, \`do\`, \`foreach\`, \`in\`, and \`managed\`. When in doubt, pick a more descriptive name (\`fnPtr\`, \`pattern\`, \`isIn\`).`,
    },
    {
      type: 'prose',
      md: `The fix is always simple: rename. If you wanted a counter called \`for\`, call it \`forCount\` or \`i\` instead.`,
    },
    {
      type: 'exercise',
      ex: {
        id: 'identifiers-keywords-ex1',
        difficulty: 'easy',
        prompt: `This program **does not compile** because it tries to use a reserved keyword as a variable name. Rename the offending variable (and every use of it) to something valid so the program prints \`15\`.`,
        starter: `int main() {
    int new = 15;   // 'new' is a reserved keyword!
    print(new);
    return 0;
}`,
        check: {
          kind: 'output',
          expected: '15',
        },
        hints: [
          '`new` is in the keyword list, so it cannot name a variable.',
          'Pick a legal identifier such as `count` and use it in both the declaration and the `print` call.',
        ],
        solution: `int main() {
    int count = 15;
    print(count);
    return 0;
}`,
      },
    },
    {
      type: 'exercise',
      ex: {
        id: 'identifiers-keywords-ex2',
        difficulty: 'easy',
        prompt: `**Predict the output.** All of these are *valid, distinct* identifiers. Type exactly what the program prints.`,
        code: `int main() {
    int value = 1;
    int Value = 2;
    int _value = 3;
    print(value + Value + _value);
    return 0;
}`,
        check: {
          kind: 'predict',
          expected: '6',
        },
        hints: [
          'Identifiers are case-sensitive, so `value` and `Value` are two different variables.',
          '`_value` is also legal because identifiers may start with an underscore.',
        ],
      },
    },
  ],
} satisfies Lesson
