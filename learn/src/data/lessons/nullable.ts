import type { Lesson } from '../../types.ts'

export default {
  id: 'nullable',
  title: 'Nullable Types (T?)',
  blurb: 'Letting a value be absent with T?, and unwrapping it safely with the ?? operator.',
  blocks: [
    {
      type: 'prose',
      md: `Sometimes a value is genuinely *absent* — a count not yet known, a lookup that found nothing. Glang models this with a **nullable type**, written by adding \`?\` to any non-pointer type:

\`\`\`c
int?    // an int, or null
string? // a string, or null
bool?   // a bool, or null
\`\`\`

A nullable variable may hold either \`null\` or a value of its base type. The **zero value** of a nullable is \`null\` — absence is the default.`,
    },
    {
      type: 'callout',
      tone: 'note',
      md: `Pointer types (\`T*\`) are **already nullable** — a pointer can always be \`null\` — so they reject the \`?\` suffix. Writing \`int*?\` is an error. Use \`?\` only on non-pointer types.`,
    },
    {
      type: 'prose',
      md: `You can assign \`null\` or a plain base-type value to a nullable. Assigning a base value **auto-promotes** it: an \`int\` flows into an \`int?\` with no cast.

\`\`\`c
int? count  = null;   // explicitly absent
int? count2 = 42;     // auto-promotes int -> int?
\`\`\`

The interesting direction is the other way. You **cannot** assign an \`int?\` straight into a plain \`int\` — the \`int?\` might be \`null\`, and a plain \`int\` has no room for absence. That's a compile-time error.`,
    },
    {
      type: 'prose',
      md: `To get a plain value back out, use the **null-coalescing operator** \`??\`. The expression \`a ?? b\` evaluates to \`a\`'s value when \`a\` is non-null, and to \`b\` otherwise:

\`\`\`c
int x = count ?? 0;   // count's value, or 0 if count is null
\`\`\`

This is the safe way to unwrap: you always supply a fallback, so the result is a real \`int\`.`,
    },
    {
      type: 'run',
      caption: 'coalesce.lang',
      code: `int main() {
    int? count = null;
    int x = count ?? 0;     // null -> use the fallback
    print(x);               // 0

    int? have = 42;
    int y = have ?? 99;     // non-null -> use have's value
    print(y);               // 42
    return 0;
}`,
    },
    {
      type: 'prose',
      md: `\`??\` **short-circuits**: when the left operand is non-null, the right operand is **not evaluated at all**. That matters when the fallback has a side effect or is expensive — it only runs when it's actually needed.

In the demo below, \`fallback\` prints a line whenever it runs. Notice it runs for the \`null\` case but is skipped entirely for the non-null one.`,
    },
    {
      type: 'run',
      caption: 'shortcircuit.lang',
      code: `int fallback() {
    print("fallback ran");
    return -1;
}

int main() {
    int? have = 5;
    int v = have ?? fallback();   // have is non-null: fallback() is skipped
    print(v);                     // 5

    int? missing = null;
    int w = missing ?? fallback();  // missing is null: fallback() runs
    print(w);                       // -1
    return 0;
}`,
    },
    {
      type: 'callout',
      tone: 'gotcha',
      md: `Assigning a \`T?\` to a plain \`T\` is a **compile error**, not a silent unwrap:

\`\`\`c
int? maybe = 7;
int  n = maybe;        // error: cannot assign 'int?' to 'int'
int  m = maybe ?? 0;   // ok: ?? supplies a fallback
\`\`\`

Always go through \`??\` (or an explicit null check) to cross from nullable to plain.`,
    },
    {
      type: 'exercise',
      ex: {
        id: 'nullable-ex1',
        difficulty: 'easy',
        prompt: `Use \`??\` to give \`label\` a sensible default. \`name\` is \`null\`, so the program should print \`anonymous\`.`,
        starter: `int main() {
    string? name = null;
    string label = /* unwrap name, defaulting to "anonymous" */;
    print(label);
    return 0;
}`,
        check: {
          kind: 'output',
          expected: 'anonymous',
        },
        hints: [
          'The pattern is `value ?? fallback`.',
          'Write `name ?? "anonymous"`.',
        ],
        solution: `int main() {
    string? name = null;
    string label = name ?? "anonymous";
    print(label);
    return 0;
}`,
      },
    },
    {
      type: 'exercise',
      ex: {
        id: 'nullable-ex2',
        difficulty: 'medium',
        prompt: `**Predict the output.** Two nullables are unwrapped with \`??\`; only one of them is \`null\`.`,
        code: `int main() {
    int? a = 8;
    int? b = null;
    int x = a ?? 100;
    int y = b ?? 100;
    print(x);
    print(y);
    print(x + y);
    return 0;
}`,
        check: {
          kind: 'predict',
          expected: '8\n100\n108',
        },
        hints: [
          '`a` is non-null, so `x` is `a`\'s value (8); the fallback 100 is skipped.',
          '`b` is null, so `y` falls back to 100.',
        ],
      },
    },
  ],
} satisfies Lesson
