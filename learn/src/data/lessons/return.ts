import type { Lesson } from '../../types.ts'

export default {
  id: 'return',
  title: 'Return',
  blurb: 'Hand a value back from a function — and satisfy every code path.',
  blocks: [
    {
      type: 'prose',
      md: `A function uses **\`return\`** to finish and (optionally) hand a value back to its caller. There are two forms:

\`\`\`
return;          // in a void function — just stop here
return value;    // in a typed function — give back a value
\`\`\`

A \`void\` function returns nothing, so it uses the bare \`return;\` (or simply runs off the end). A function declared with a result type — like \`int\` or \`string\` — must \`return\` a value of that type.`,
    },
    {
      type: 'run',
      caption: 'square.lang',
      code: `int square(int x) {
    return x * x;
}

int main() {
    print(square(6));
    print(square(9));
    return 0;
}`,
    },
    {
      type: 'prose',
      md: `\`square\` takes an \`int\` and returns an \`int\`. The moment \`return x * x;\` runs, the function ends and the result flows back to where it was called. \`main\` itself returns an \`int\` — the exit code.`,
    },
    {
      type: 'prose',
      md: `\`return\` also lets you exit early. Once a \`return\` executes, the rest of the function is skipped — which is handy for handling a special case up front.`,
    },
    {
      type: 'run',
      caption: 'abs.lang',
      code: `int abs(int n) {
    if (n < 0) {
        return -n;
    }
    return n;
}

int main() {
    print(abs(-7));
    print(abs(4));
    return 0;
}`,
    },
    {
      type: 'prose',
      md: `For a negative \`n\`, the first \`return\` runs and the function is done. Otherwise control falls through to the second \`return\`. Either way, **every path returns an \`int\`** — which is exactly the rule below.`,
    },
    {
      type: 'callout',
      tone: 'gotcha',
      md: `**Every non-void code path must return a value**, and this is enforced at compile time. If an \`if\` returns but its missing \`else\` branch does not, the compiler rejects the function. Make sure there is no way to reach the closing \`}\` of a typed function without hitting a \`return\`.`,
    },
    {
      type: 'static',
      caption: 'missing-return.lang (does NOT compile)',
      code: `int sign(int n) {
    if (n > 0) {
        return 1;
    } else if (n < 0) {
        return -1;
    }
    // falls off the end when n == 0 — compile error!
}`,
      output: 'error: not all code paths return a value',
    },
    {
      type: 'prose',
      md: `The fix is to make the final case unconditional — for example replace the last \`else if\` with a plain \`else\`, or add a trailing \`return 0;\` to cover \`n == 0\`.`,
    },
    {
      type: 'exercise',
      ex: {
        id: 'return-ex1',
        difficulty: 'easy',
        prompt: `Finish the \`max\` function so it returns the larger of its two arguments. With the calls in \`main\`, the expected output is:

\`\`\`
8
20
\`\`\``,
        starter: `int max(int a, int b) {
    // return the larger of a and b

}

int main() {
    print(max(3, 8));
    print(max(20, 11));
    return 0;
}`,
        check: {
          kind: 'output',
          expected: '8\n20',
        },
        hints: [
          'Compare with `if (a > b)` and return `a`, otherwise return `b`.',
          'Make sure both paths return — an `if`/`else` covers every case.',
        ],
        solution: `int max(int a, int b) {
    if (a > b) {
        return a;
    } else {
        return b;
    }
}

int main() {
    print(max(3, 8));
    print(max(20, 11));
    return 0;
}`,
      },
    },
    {
      type: 'exercise',
      ex: {
        id: 'return-ex2',
        difficulty: 'medium',
        prompt: `**Predict the output.** \`isEven\` returns a \`bool\`. Trace the calls and type exactly what \`main\` prints.`,
        code: `bool isEven(int n) {
    if (n % 2 == 0) {
        return true;
    }
    return false;
}

int main() {
    print(isEven(10));
    print(isEven(7));
    return 0;
}`,
        check: {
          kind: 'predict',
          expected: 'true\nfalse',
        },
        hints: [
          '`10 % 2` is `0`, so `isEven(10)` returns `true`.',
          'A `bool` prints as `true` or `false`.',
        ],
      },
    },
  ],
} satisfies Lesson
