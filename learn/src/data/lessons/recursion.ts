import type { Lesson } from '../../types.ts'

export default {
  id: 'recursion',
  title: 'Recursion',
  blurb: 'Functions that call themselves — with a base case to stop.',
  blocks: [
    {
      type: 'prose',
      md: `A **recursive** function calls itself to solve a smaller version of the same problem. Every recursion needs two parts:

1. A **base case** that returns directly without recursing.
2. A **recursive case** that calls the function on a smaller input and combines the result.

Glang supports recursion directly. The classic example is factorial: \`n! = n * (n-1)!\`, with \`0! = 1\` as the base case.`,
    },
    {
      type: 'run',
      caption: 'factorial.lang',
      code: `int factorial(int n) {
    if (n <= 1) {
        return 1;
    }
    return n * factorial(n - 1);
}

int main() {
    print(factorial(5));
    return 0;
}`,
    },
    {
      type: 'prose',
      md: `\`factorial(5)\` unfolds as \`5 * factorial(4)\` → \`5 * 4 * factorial(3)\` → … → \`5 * 4 * 3 * 2 * 1\` = \`120\`. The \`if (n <= 1)\` branch stops the descent; without it the function would call itself forever.

Some problems recurse more than once per call. Fibonacci adds the two previous numbers, so each call spawns two sub-calls.`,
    },
    {
      type: 'run',
      caption: 'fibonacci.lang',
      code: `int fib(int n) {
    if (n < 2) {
        return n;
    }
    return fib(n - 1) + fib(n - 2);
}

int main() {
    int i = 0;
    while (i < 10) {
        print(fib(i));
        ++i;
    }
    return 0;
}`,
    },
    {
      type: 'callout',
      tone: 'warn',
      md: `Glang v1 makes **no tail-call optimisation guarantee**. Each pending call uses a stack frame, so very deep recursion can overflow the stack. When recursion would go thousands of levels deep, prefer a \`while\`/\`for\` loop instead.`,
    },
    {
      type: 'callout',
      tone: 'gotcha',
      md: `Always make sure the recursive call moves *toward* the base case (here, \`n - 1\` shrinks \`n\`). A recursive case that doesn't reduce the input never terminates.`,
    },
    {
      type: 'exercise',
      ex: {
        id: 'recursion-ex1',
        difficulty: 'easy',
        prompt: `Write \`int sumTo(int n)\` that returns \`1 + 2 + ... + n\` **recursively** (no loops). The base case is \`sumTo(0) == 0\`. Print \`sumTo(5)\`.

Expected output:

\`\`\`
15
\`\`\``,
        starter: `int sumTo(int n) {
    // base case: if n <= 0 return 0
    // recursive case: n + sumTo(n - 1)
}

int main() {
    print(sumTo(5));
    return 0;
}`,
        check: {
          kind: 'output',
          expected: '15',
        },
        hints: [
          'Base case: `if (n <= 0) { return 0; }`.',
          'Recursive case: `return n + sumTo(n - 1);`.',
        ],
        solution: `int sumTo(int n) {
    if (n <= 0) {
        return 0;
    }
    return n + sumTo(n - 1);
}

int main() {
    print(sumTo(5));
    return 0;
}`,
      },
    },
    {
      type: 'exercise',
      ex: {
        id: 'recursion-ex2',
        difficulty: 'medium',
        prompt: `Write \`int power(int base, int exp)\` that computes \`base\` raised to \`exp\` **recursively**, where \`power(base, 0) == 1\`. Print \`power(2, 10)\`.

Expected output:

\`\`\`
1024
\`\`\``,
        starter: `int power(int base, int exp) {
    // base case: exp == 0 returns 1
    // recursive case: base * power(base, exp - 1)
}

int main() {
    print(power(2, 10));
    return 0;
}`,
        check: {
          kind: 'output',
          expected: '1024',
        },
        hints: [
          'Base case: `if (exp == 0) { return 1; }`.',
          'Recursive case: `return base * power(base, exp - 1);`.',
        ],
        solution: `int power(int base, int exp) {
    if (exp == 0) {
        return 1;
    }
    return base * power(base, exp - 1);
}

int main() {
    print(power(2, 10));
    return 0;
}`,
      },
    },
    {
      type: 'exercise',
      ex: {
        id: 'recursion-ex3',
        difficulty: 'medium',
        prompt: `**Predict the output.** Read the program and type exactly what it prints.`,
        code: `int countdown(int n) {
    if (n < 0) {
        return 0;
    }
    print(n);
    return countdown(n - 1);
}

int main() {
    countdown(3);
    return 0;
}`,
        check: {
          kind: 'predict',
          expected: '3\n2\n1\n0',
        },
        hints: [
          'Each call prints `n` before recursing on `n - 1`.',
          'The recursion stops once `n` drops below `0`, printing nothing for `-1`.',
        ],
      },
    },
  ],
} satisfies Lesson
