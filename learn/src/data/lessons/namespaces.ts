import type { Lesson } from '../../types.ts'

export default {
  id: 'namespaces',
  title: 'Namespaces',
  blurb: 'Group related top-level declarations under a name and reach them with the `ns::name` form.',
  blocks: [
    {
      type: 'prose',
      md: `A **\`namespace\`** block groups top-level declarations — functions, classes, interfaces, enums, and even nested namespaces — under a shared name. From *outside* the block, you reach a member with the qualified **\`ns::name\`** form.`,
    },
    {
      type: 'static',
      caption: 'geo.lang',
      code: `namespace geo {
    class Point {
        int x;
        Point(int x) { this.x = x; }
    }
    int getX(Point p) { return p.x; }   // sibling reference needs no prefix
}

int main() {
    geo::Point p = geo::Point(7);
    return geo::getX(p);
}`,
      output: '',
    },
    {
      type: 'prose',
      md: `Notice two things in that example:

- From \`main\` (outside \`geo\`), every reference is qualified: \`geo::Point\`, \`geo::getX\`.
- Inside \`geo\`, the function \`getX\` refers to its sibling type \`Point\` **with no prefix** — members of the same namespace see each other directly.

(The program returns \`7\` as its exit code; it prints nothing.)`,
    },
    {
      type: 'prose',
      md: `### Resolution rules

Inside a namespace, an **unqualified** name is looked up:

1. in the enclosing namespaces, **innermost first**,
2. then the global (top-level) scope,
3. then the builtins.

**Local variables and parameters always shadow namespace members** — if a parameter is named \`abs\`, that wins over a \`math::abs\` in scope. Outside a namespace you must qualify (\`math::abs(x)\`), unless a \`using\` declaration has opened it (next lesson).`,
    },
    {
      type: 'callout',
      tone: 'note',
      md: `Namespaces are **compiled away before type-checking**. Each member just becomes an ordinary top-level declaration whose name carries the prefix — so the rest of the compiler, and the error messages, see plain qualified names like \`math::abs\`. A namespace is organisation, not a runtime construct.`,
    },
    {
      type: 'prose',
      md: `### Qualified names work *everywhere* a name does

The \`ns::name\` form is not limited to calls. It is valid anywhere the language expects a name:

- **Types:** \`geo::Point* p\`
- **Construction:** \`new geo::Point(7)\`
- **Casts:** \`(traffic::Light)1\`
- **Enum variants:** \`traffic::Light.GREEN\`
- **Static members:** \`cfg::Defaults.get()\`
- **Generics:** \`col::Pair<int>\`
- **\`extends\` / \`implements\` clauses**
- **Function references:** \`fn(int) -> int f = math::twice;\``,
    },
    {
      type: 'static',
      caption: 'lights.lang',
      code: `namespace traffic {
    enum Light { RED, YELLOW, GREEN }
}

int main() {
    traffic::Light go = traffic::Light.GREEN;
    print((int)go);            // variant index
    traffic::Light first = (traffic::Light)0;
    print(first == traffic::Light.RED);
    return 0;
}`,
      output: '2\ntrue',
    },
    {
      type: 'prose',
      md: `\`GREEN\` is the third variant, so \`(int)traffic::Light.GREEN\` is \`2\`. The cast \`(traffic::Light)0\` rebuilds \`RED\`, which compares equal to \`traffic::Light.RED\`.`,
    },
    {
      type: 'prose',
      md: `### Extending and nesting namespaces

- **Re-declaring a namespace extends it** — in the same file *or another file*. A namespace can therefore span multiple modules: open \`namespace util { … }\` in two files and the members merge. **Duplicate members** (the same name declared twice in the namespace) remain a compile error.
- **\`namespace a::b { … }\`** is shorthand for nesting \`b\` inside \`a\`. Members are then reached as \`a::b::name\`.`,
    },
    {
      type: 'static',
      caption: 'extend.lang',
      code: `namespace shapes {
    int unitArea() { return 1; }
}

// Re-opening shapes extends it rather than replacing it.
namespace shapes {
    int doubled() { return unitArea() * 2; }
}

namespace outer::inner {
    int answer() { return 42; }
}

int main() {
    print(shapes::unitArea());
    print(shapes::doubled());
    print(outer::inner::answer());
    return 0;
}`,
      output: '1\n2\n42',
    },
    {
      type: 'callout',
      tone: 'gotcha',
      md: `Re-opening a namespace **extends**; it does not overwrite. But declaring the *same member name twice* in that namespace — say two \`int unitArea()\` — is a duplicate-member compile error, just like declaring the same global twice.`,
    },
    {
      type: 'exercise',
      ex: {
        id: 'namespaces-ex1',
        difficulty: 'easy',
        prompt: `**Predict the output.** A sibling call inside a namespace needs no prefix; from \`main\` you must qualify.

\`\`\`
namespace mathx {
    int twice(int n) { return n * 2; }
    int quad(int n)  { return twice(twice(n)); }   // sibling, no prefix
}
\`\`\``,
        code: `int main() {
    print(mathx::twice(5));
    print(mathx::quad(3));
    return 0;
}`,
        check: {
          kind: 'predict',
          expected: '10\n12',
        },
        hints: [
          '`quad` calls its sibling `twice` directly (no `mathx::`), so `quad(3)` is `twice(twice(3))`.',
          '`twice(3)` is `6`; `twice(6)` is `12`.',
        ],
      },
    },
    {
      type: 'exercise',
      ex: {
        id: 'namespaces-ex2',
        difficulty: 'medium',
        prompt: `**Predict the output.** This uses nesting (\`a::b\`), an extended namespace, and a qualified enum cast. Trace it carefully.

\`\`\`
namespace color {
    enum Channel { R, G, B }
}

namespace box {
    int side() { return 4; }
}
namespace box {                       // extends box
    int area() { return side() * side(); }
}
\`\`\``,
        code: `int main() {
    color::Channel c = (color::Channel)2;
    print(c == color::Channel.B);
    print((int)color::Channel.G);
    print(box::area());
    return 0;
}`,
        check: {
          kind: 'predict',
          expected: 'true\n1\n16',
        },
        hints: [
          '`(color::Channel)2` is the variant at index 2, which is `B`.',
          '`G` is the second variant, index `1`. `box::area()` is `side() * side()` = `4 * 4`.',
        ],
      },
    },
  ],
} satisfies Lesson
