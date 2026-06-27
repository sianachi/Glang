import type { Lesson } from '../../types.ts'

export default {
  id: 'linq',
  title: 'LINQ-Style Collections',
  blurb: 'Import std/linq.lang to get filter / fold / map methods on List, Span, and string — built entirely from object modifiers.',
  blocks: [
    {
      type: 'prose',
      md: `The standard library uses **object modifiers** to bolt LINQ-style collection operations onto the core collection types — without editing a single line of \`List\`, \`Span\`, or \`string\`. Just add one import:

\`\`\`
import "std/linq.lang";
\`\`\`

That import registers a family of methods on \`List<T>\`, \`Span<T>\`, and \`string\`. This lesson assumes you have already met [object modifiers](#) — LINQ is the real-world payoff of that feature.`,
    },
    {
      type: 'prose',
      md: `### The methods added to \`List<T>\`

Importing \`std/linq.lang\` gives \`List<T>\` these seven methods:

- \`List<T> where(fn(T) -> bool)\` — filter into a **new list** of matching elements
- \`bool any(fn(T) -> bool)\` — true if any element matches
- \`bool all(fn(T) -> bool)\` — true if every element matches
- \`int countWhere(fn(T) -> bool)\` — count of matching elements
- \`T first(fn(T) -> bool)\` — first matching element (exits if none)
- \`void forEach(fn(T) -> void)\` — apply an action to every element
- \`T reduce(fn(T,T) -> T, T)\` — fold left with an initial value

\`Span<T>\` gets the same seven (its \`where\` returns a \`List<T>\`). On \`string\` the element type is \`char\` and \`where\` returns \`List<char>\`.`,
    },
    {
      type: 'static',
      caption: 'filter_fold.lang',
      code: `import "std/linq.lang";

int main() {
    List<int> scores = List<int>();
    scores.add(45);
    scores.add(82);
    scores.add(60);
    scores.add(91);

    int failures = scores.countWhere((int s) -> bool { return s < 60; });
    print(failures);

    bool anyExcellent = scores.any((int s) -> bool { return s >= 90; });
    print(anyExcellent);

    bool allPass = scores.all((int s) -> bool { return s >= 60; });
    print(allPass);

    return 0;
}`,
      output: '1\ntrue\nfalse',
    },
    {
      type: 'callout',
      tone: 'note',
      md: `Each method takes a **closure** — \`(int s) -> bool { ... }\` is an anonymous function literal. \`countWhere\` finds one score below 60 (\`45\`), \`any\` finds \`91 >= 90\` (true), and \`all\` fails on \`45\` (false).`,
    },
    {
      type: 'prose',
      md: `### Method chaining

\`where\` returns a fresh \`List<T>\`, so its result has all the same LINQ methods — which means you can **chain** calls. Below, \`where\` produces a list of even numbers, and \`reduce\` folds that list into a sum.`,
    },
    {
      type: 'static',
      caption: 'chaining.lang',
      code: `import "std/linq.lang";

int main() {
    List<int> nums = List<int>();
    for (int i = 1; i <= 10; ++i) { nums.add(i); }

    // method chaining works because where() returns a List<int>
    int sumOfEvens = nums
        .where((int x) -> bool { return x % 2 == 0; })
        .reduce((int acc, int x) -> int { return acc + x; }, 0);
    print(sumOfEvens);

    bool hasW = "hello world".any((char c) -> bool { return c == 'w'; });
    print(hasW);

    return 0;
}`,
      output: '30\ntrue',
    },
    {
      type: 'callout',
      tone: 'tip',
      md: `The evens are \`2 4 6 8 10\`, and \`reduce(..., 0)\` folds them left starting at \`0\`: \`0+2+4+6+8+10 = 30\`. The second call shows LINQ on a \`string\`: \`any\` iterates the characters, and \`'w'\` is present in \`"hello world"\`, so it returns \`true\`.`,
    },
    {
      type: 'prose',
      md: `### Cross-type operations stay free functions

A modifier method can only mention one element type — but mapping a \`List<T>\` to a \`List<U>\` needs **two** type parameters. Those operations can't be modifier methods, so the standard library exposes them as **free functions**:

\`\`\`
List<U> select<T, U>(List<T> source, fn(T) -> U mapper)
List<U> spanSelect<T, U>(Span<T> sp, fn(T) -> U mapper)
T strReduce<T>(string s, fn(T, char) -> T reducer, T initial)
\`\`\`

You call these as ordinary generic functions — \`select<int, int>(scores, mapper)\` — rather than with dot syntax.`,
    },
    {
      type: 'static',
      caption: 'select_free.lang',
      code: `import "std/linq.lang";

int main() {
    List<int> nums = List<int>();
    nums.add(1);
    nums.add(2);
    nums.add(3);

    // select<T, U> maps each element through a function
    List<int> doubled = select<int, int>(nums, (int x) -> int { return x * 2; });
    doubled.forEach((int x) -> void { print(x); });

    return 0;
}`,
      output: '2\n4\n6',
    },
    {
      type: 'callout',
      tone: 'gotcha',
      md: `\`first\` returns the first matching element but **exits the program** if nothing matches — there is no null to fall back on. Guard with \`any\` (or \`countWhere\`) first when a match is not guaranteed.`,
    },
    {
      type: 'exercise',
      ex: {
        id: 'linq-ex1',
        difficulty: 'easy',
        prompt: `**Predict the output.** \`reduce\` folds left from the initial value. Type exactly what this prints.`,
        code: `import "std/linq.lang";

int main() {
    List<int> xs = List<int>();
    xs.add(10);
    xs.add(20);
    xs.add(30);

    int total = xs.reduce((int acc, int x) -> int { return acc + x; }, 0);
    print(total);

    int count = xs.countWhere((int x) -> bool { return x >= 20; });
    print(count);

    return 0;
}`,
        check: {
          kind: 'predict',
          expected: '60\n2',
        },
        hints: [
          '`reduce` starts at `0` and adds each element: `0+10+20+30`.',
          '`countWhere` counts elements where `x >= 20`: that is `20` and `30`.',
        ],
      },
    },
    {
      type: 'exercise',
      ex: {
        id: 'linq-ex2',
        difficulty: 'medium',
        prompt: `**Predict the output.** \`where\` returns a new \`List<int>\`, so the chain is \`where(...).reduce(...)\`. Type exactly what this prints.`,
        code: `import "std/linq.lang";

int main() {
    List<int> nums = List<int>();
    for (int i = 1; i <= 6; ++i) { nums.add(i); }

    int sumOfOdds = nums
        .where((int x) -> bool { return x % 2 == 1; })
        .reduce((int acc, int x) -> int { return acc + x; }, 0);
    print(sumOfOdds);

    bool anyBig = nums.any((int x) -> bool { return x > 5; });
    print(anyBig);

    return 0;
}`,
        check: {
          kind: 'predict',
          expected: '9\ntrue',
        },
        hints: [
          'The odds in `1..6` are `1 3 5`; `reduce(..., 0)` sums them.',
          '`any(x > 5)` is true because `6` is present.',
        ],
      },
    },
  ],
} satisfies Lesson
