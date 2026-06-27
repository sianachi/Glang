import type { Lesson } from '../../types.ts'

export default {
  id: 'using-declarations',
  title: 'using Declarations',
  blurb: 'Drop the `ns::` prefix with `using namespace` and `using ns::member` — and keep them private to your file.',
  blocks: [
    {
      type: 'prose',
      md: `Qualifying every reference as \`math::abs\` gets noisy. A **\`using\`** declaration removes the need to qualify. It comes in two forms, both written at the **top level of a file**:

- **\`using namespace math;\`** — a *directive* that opens **every** member of \`math\`.
- **\`using io::appendFile;\`** — a *declaration* that imports a **single** member.`,
    },
    {
      type: 'static',
      caption: 'log.lang',
      code: `import "std/math.lang";
import "std/io.lang";

using namespace math;       // directive: opens every member of math
using io::appendFile;       // declaration: imports just appendFile

int main() {
    print(abs(-7));         // resolves to math::abs
    appendFile("log.txt", "hi\\n");
    return 0;
}`,
      output: '7',
    },
    {
      type: 'prose',
      md: `With \`using namespace math;\` in effect, \`abs(-7)\` resolves to \`math::abs\` without the prefix. With \`using io::appendFile;\`, the single name \`appendFile\` is available unqualified (the other \`io::\` members still need their prefix).`,
    },
    {
      type: 'callout',
      tone: 'gotcha',
      md: `Don't confuse this with the **\`using (T x = expr) { … }\`** *resource block* (section 8.6). That parenthesised form lives **inside a function body** and deterministically disposes a resource at scope exit — a completely different construct. The namespace-import forms on this page take **no parentheses** and appear **only at the top level** of a file.`,
    },
    {
      type: 'prose',
      md: `### Scope: position to end-of-file, never into importers

A \`using\` applies **from its position to the end of that file**. Two consequences:

- A name used *above* the \`using\` is still unresolved there — order matters.
- A \`using\` **never leaks into files that import yours.** A library can \`using namespace internal;\` for its own convenience and importers are completely unaffected — they still see fully qualified names. Your \`using\` choices stay private.`,
    },
    {
      type: 'callout',
      tone: 'note',
      md: `Both forms work for **functions, classes, enums, and interfaces** alike. After \`using namespace geo;\`, you can write \`Point p = Point(3);\` and \`new Point(4)\` with no \`geo::\` prefix.`,
    },
    {
      type: 'prose',
      md: `### Resolution order

When an unqualified name appears, the compiler resolves it in this strict order:

1. **Local variables** (and parameters),
2. **Enclosing namespaces**, innermost first,
3. **Explicitly declared top-level names** (globals),
4. **Single-member \`using\`** imports (\`using ns::member;\`),
5. **\`using namespace\`** opens.

Two important tie-breakers:

- A name found in **two opened namespaces** is a compile-time **ambiguity error** — qualify it to disambiguate.
- A **global always wins** over a name from an opened namespace. And a **single-member \`using\` that collides with a global** of the same name is a compile error.`,
    },
    {
      type: 'static',
      caption: 'resolve.lang',
      code: `namespace fx {
    int level() { return 9; }
}

using namespace fx;

int level() { return 1; }   // a real global

int main() {
    // The global 'level' wins over the opened fx::level.
    print(level());
    print(fx::level());     // qualify to reach the namespace one
    return 0;
}`,
      output: '1\n9',
    },
    {
      type: 'prose',
      md: `Even though \`using namespace fx;\` opened \`fx::level\`, the **global \`level\` wins** (rule: globals beat opened namespaces), so \`level()\` calls the global and prints \`1\`. To reach the namespace version you qualify it: \`fx::level()\` prints \`9\`.`,
    },
    {
      type: 'callout',
      tone: 'warn',
      md: `If \`a::foo\` and \`b::foo\` are both opened with \`using namespace\` and you reference bare \`foo\`, that's an **ambiguity error**, not a silent pick. Write \`a::foo\` or \`b::foo\` to resolve it. Likewise, \`using a::foo;\` when a global \`foo\` already exists is a hard error.`,
    },
    {
      type: 'exercise',
      ex: {
        id: 'using-declarations-ex1',
        difficulty: 'easy',
        prompt: `**Predict the output.** \`using namespace mathx;\` opens the namespace, so its members are reachable unqualified.

\`\`\`
namespace mathx {
    int sq(int n)   { return n * n; }
    int cube(int n) { return n * n * n; }
}

using namespace mathx;
\`\`\``,
        code: `int main() {
    print(sq(4));
    print(cube(2));
    return 0;
}`,
        check: {
          kind: 'predict',
          expected: '16\n8',
        },
        hints: [
          'After `using namespace mathx;`, `sq` and `cube` resolve to `mathx::sq` and `mathx::cube` with no prefix.',
          '`sq(4)` is `16`; `cube(2)` is `8`.',
        ],
      },
    },
    {
      type: 'exercise',
      ex: {
        id: 'using-declarations-ex2',
        difficulty: 'medium',
        prompt: `**Predict the output.** A single-member \`using\` is in effect, and there is also a global with a *different* name. Apply the resolution order: a global wins over an opened namespace, but a single-member \`using\` brings in exactly one name.

\`\`\`
namespace units {
    int meters(int n) { return n; }
    int feet(int n)   { return n * 3; }
}

using units::feet;          // bring in ONLY feet, unqualified

int meters(int n) { return n * 100; }   // an unrelated global 'meters'
\`\`\``,
        code: `int main() {
    print(feet(2));            // units::feet, unqualified
    print(meters(2));          // the global meters, NOT units::meters
    print(units::meters(2));   // qualified -> the namespace one
    return 0;
}`,
        check: {
          kind: 'predict',
          expected: '6\n200\n2',
        },
        hints: [
          '`using units::feet;` makes only `feet` unqualified — so `feet(2)` is `units::feet(2)` = `2 * 3`.',
          'Bare `meters` resolves to the global (which wins), `2 * 100`; only `units::meters(2)` reaches the namespace version, which returns `2`.',
        ],
      },
    },
  ],
} satisfies Lesson
