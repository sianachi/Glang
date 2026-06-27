import type { Lesson } from '../../types.ts'

export default {
  id: 'stdlib-tour',
  title: 'Standard Library Tour',
  blurb: 'A guided look at the bundled `std/` modules: math, chars, strings, io, and the generic collections.',
  blocks: [
    {
      type: 'prose',
      md: `The bundled standard library lives in \`stdlib/\` and is imported with the **\`std/\`** prefix (e.g. \`import "std/list.lang";\`). It splits into two flavours:

- **Function modules** are wrapped in **namespaces** — \`math\`, \`chars\`, \`strings\`, \`io\` — so you call their members qualified: \`math::abs(x)\`, \`chars::isDigit(c)\`. (Three of the names are pluralised or shortened because \`char\` and \`string\` are type keywords.)
- **Collection classes** (\`List\`, \`Stack\`, \`Queue\`, \`Map\`, \`Option\`, \`Span\`, \`MemoryOwner\`) are **global** once imported — no namespace prefix.`,
    },
    {
      type: 'callout',
      tone: 'note',
      md: `The file-I/O *built-ins* \`readFile\`, \`writeFile\`, and \`fileExists\` are part of the runtime and need **no import**. The richer \`io::\` helpers below are in \`std/io.lang\` and must be imported.`,
    },
    {
      type: 'prose',
      md: `### The module table

| Module | Provides |
|---|---|
| \`std/math.lang\` | \`math::\` — \`abs\`, \`fabs\`, \`min\`/\`max\`, \`fmin\`/\`fmax\`, \`clamp\`, \`sign\`, \`ipow\`, \`gcd\`, \`lcm\`, \`isqrt\`, \`factorial\` |
| \`std/char.lang\` | \`chars::\` — \`isDigit\`/\`isAlpha\`/\`isAlnum\`/\`isSpace\`/\`isUpper\`/\`isLower\`, \`toUpper\`/\`toLower\`, \`digitToInt\` |
| \`std/string.lang\` | \`strings::\` — \`toUpperStr\`/\`toLowerStr\`, \`reverse\`, \`repeat\`, \`trim\`, \`padLeft\`, \`count\`, \`replaceChar\`, \`equalsIgnoreCase\` |
| \`std/io.lang\` | \`io::\` — \`appendFile\`, \`readLineCount\`, \`dieWith\` (built on the I/O built-ins) |
| \`std/list.lang\` | \`List<T>\` — growable list: \`add\`, \`get\`, \`set\`, \`contains\`, \`removeAt\`, \`length\`, \`isEmpty\`, \`clear\`, \`span\` |
| \`std/stack.lang\` | \`Stack<T>\` — \`push\`, \`pop\`, \`peek\`, \`length\`, \`isEmpty\` |
| \`std/queue.lang\` | \`Queue<T>\` — ring buffer: \`enqueue\`, \`dequeue\`, \`peek\`, \`length\`, \`isEmpty\` |
| \`std/map.lang\` | \`Map<K,V>\` — association map: \`set\`, \`getOr\`, \`has\`, \`remove\`, \`length\` |
| \`std/option.lang\` | \`Option<T>\` — \`setSome\`/\`setNone\`, \`isSome\`/\`isNone\`, \`get\`, \`getOr\` |
| \`std/span.lang\` | \`Span<T>\` — non-owning bounds-checked view: \`get\`, \`set\`, \`slice\`, \`length\`, \`isEmpty\` |
| \`std/memory.lang\` | \`MemoryOwner<T>\` — owning heap block: \`get\`, \`set\`, \`span\`, \`length\`, \`dispose\` |`,
    },
    {
      type: 'prose',
      md: `### \`math::\` — numeric helpers

Glang has no ternary and its ordering comparisons work on \`int\`/\`float\` only, so the module is plain numeric helpers. Here are a few: \`gcd\`, \`lcm\`, \`isqrt\`, \`factorial\`.`,
    },
    {
      type: 'static',
      caption: 'numbers.lang',
      code: `import "std/math.lang";

int main() {
    print(math::gcd(12, 18));    // greatest common divisor
    print(math::lcm(4, 6));      // least common multiple
    print(math::isqrt(20));      // floor of the square root
    print(math::factorial(5));   // 5*4*3*2*1
    return 0;
}`,
      output: '6\n12\n4\n120',
    },
    {
      type: 'prose',
      md: `\`gcd(12, 18)\` is \`6\`; \`lcm(4, 6)\` is \`12\`; \`isqrt(20)\` floors √20 to \`4\`; \`factorial(5)\` is \`120\`.`,
    },
    {
      type: 'prose',
      md: `### \`chars::\` and \`strings::\` — text helpers

\`chars::\` classifies and transforms a single \`char\` (\`isDigit\`, \`toUpper\`, \`digitToInt\`, …). \`strings::\` works on whole strings (\`reverse\`, \`repeat\`, \`trim\`, \`padLeft\`, …).`,
    },
    {
      type: 'static',
      caption: 'text.lang',
      code: `import "std/char.lang";
import "std/string.lang";

int main() {
    print(strings::reverse("glang"));   // characters reversed
    print(strings::repeat("ab", 3));    // "ab" three times
    print(chars::toUpper('q'));         // a single uppercased char
    print(chars::digitToInt('7'));      // the digit's int value
    return 0;
}`,
      output: 'gnalg\nababab\nQ\n7',
    },
    {
      type: 'prose',
      md: `\`reverse("glang")\` gives \`"gnalg"\`; \`repeat("ab", 3)\` gives \`"ababab"\`; \`toUpper('q')\` is the char \`'Q'\`; \`digitToInt('7')\` is the integer \`7\`.`,
    },
    {
      type: 'prose',
      md: `### \`io::\` — file helpers

\`std/io.lang\` builds on the runtime I/O built-ins: \`io::appendFile(path, text)\` adds to a file, \`io::readLineCount(path)\` counts its lines, and \`io::dieWith(msg, code)\` prints a message and exits. (We don't run these here since they touch the filesystem.)`,
    },
    {
      type: 'prose',
      md: `### The collections are global and generic

Each collection is backed by a contiguous \`alloc(T, cap)\` block that **doubles when full**, so they grow on demand. They are *global* — no namespace — so you use \`List<int>\`, \`Map<string, int>\`, etc. directly after importing. The \`Map\` uses linear search, so any key type with \`==\` works.`,
    },
    {
      type: 'static',
      caption: 'list.lang',
      code: `import "std/list.lang";

int main() {
    List<int> xs = List<int>();
    xs.add(10);
    xs.add(20);
    print(xs.length());
    print(xs.get(1));
    return 0;
}`,
      output: '2\n20',
    },
    {
      type: 'callout',
      tone: 'tip',
      md: `\`MemoryOwner<T>\` **owns** a heap block and frees it; \`Span<T>\` is a non-owning, bounds-checked *view* over a block, and \`slice\` makes zero-copy sub-views that alias the same storage. A span is valid only while its backing owner is live — free with \`dispose()\` (or \`delete\` a \`new\`'d handle), but never both.`,
    },
    {
      type: 'exercise',
      ex: {
        id: 'stdlib-tour-ex1',
        difficulty: 'easy',
        prompt: `**Predict the output.** Function modules are namespaced; trace each \`math::\` call.

\`\`\`
import "std/math.lang";
\`\`\``,
        code: `int main() {
    print(math::abs(-15));
    print(math::clamp(99, 0, 10));
    print(math::ipow(2, 5));
    return 0;
}`,
        check: {
          kind: 'predict',
          expected: '15\n10\n32',
        },
        hints: [
          '`abs(-15)` is `15`. `clamp(99, 0, 10)` pulls 99 down into `[0, 10]`, giving the high bound.',
          '`ipow(2, 5)` is 2 raised to the 5th power.',
        ],
      },
    },
    {
      type: 'exercise',
      ex: {
        id: 'stdlib-tour-ex2',
        difficulty: 'medium',
        prompt: `**Predict the output.** Mixes \`strings::\` and \`chars::\`. \`count(s, c)\` returns how many times \`c\` appears in \`s\`; \`isDigit\` returns a \`bool\`.

\`\`\`
import "std/string.lang";
import "std/char.lang";
\`\`\``,
        code: `int main() {
    print(strings::count("banana", 'a'));
    print(strings::toUpperStr("go"));
    print(chars::isDigit('x'));
    print(chars::isAlpha('x'));
    return 0;
}`,
        check: {
          kind: 'predict',
          expected: '3\nGO\nfalse\ntrue',
        },
        hints: [
          '`"banana"` has three `a` characters. `toUpperStr("go")` uppercases the whole string.',
          '`isDigit(\'x\')` is `false`; `isAlpha(\'x\')` is `true`. Booleans print as `true`/`false`.',
        ],
      },
    },
  ],
} satisfies Lesson
