import type { Lesson } from '../../types.ts'

export default {
  id: 'enums',
  title: 'Enums',
  blurb: 'Named sets of integer constants that form their own distinct, type-checked type.',
  blocks: [
    {
      type: 'prose',
      md: `An **enum** is a named set of integer constants. Each variant carries a distinct \`int\` value, but the enum itself is its own type — not just a synonym for \`int\`.

\`\`\`c
enum Color  { RED, GREEN, BLUE }            // implicit: RED=0, GREEN=1, BLUE=2
enum Status { OK = 200, NOT_FOUND = 404 }   // explicit values
\`\`\`

Implicit values start at \`0\` and increase by \`1\`. You can pin a variant to an explicit value with \`= N\`; the **next** implicit variant then continues from \`explicit + 1\`.`,
    },
    {
      type: 'prose',
      md: `You reach a variant with dot notation — \`Color.RED\`, \`Status.NOT_FOUND\` — and you can compare enum values with \`==\` and \`!=\`.`,
    },
    {
      type: 'run',
      caption: 'color.lang',
      code: `enum Color { RED, GREEN, BLUE }

int main() {
    Color c = Color.GREEN;

    if (c == Color.GREEN) {
        print("it is green");
    }
    if (c != Color.RED) {
        print("but not red");
    }
    return 0;
}`,
    },
    {
      type: 'prose',
      md: `An enum is a **distinct type**. The type checker will not let an \`int\` and an enum mix without an explicit cast — this catches a whole class of "magic number" bugs.

\`\`\`c
Color c = Color.GREEN;   // ok
int   x = Color.RED;     // error: cannot assign 'Color' to 'int'
Color e = 0;             // error: cannot assign 'int' to 'Color'
\`\`\``,
    },
    {
      type: 'callout',
      tone: 'gotcha',
      md: `An enum is **not** an alias for \`int\`. \`int x = Color.RED;\` and \`Color c = 0;\` are both type errors — the compiler refuses to silently treat one as the other. When you really do want to cross between them, you must say so with a cast.`,
    },
    {
      type: 'prose',
      md: `When you genuinely need the underlying number, **cast to \`int\`** to read the ordinal, and **cast from \`int\`** to convert a runtime integer back into the enum type.

\`\`\`c
int code = (int) HttpStatus.NOT_FOUND;   // 404
HttpStatus s = (HttpStatus) 500;         // SERVER_ERROR
\`\`\`

The run below also shows the "continue after an explicit value" rule: \`CREATED\` has no explicit value, so it follows \`OK = 200\` as \`201\`.`,
    },
    {
      type: 'run',
      caption: 'status.lang',
      code: `enum HttpStatus { OK = 200, CREATED, NOT_FOUND = 404, SERVER_ERROR = 500 }

int main() {
    print((int) HttpStatus.NOT_FOUND);   // 404
    print((int) HttpStatus.CREATED);     // 201  (200 + 1)

    HttpStatus s = (HttpStatus) 500;     // int -> enum
    if (s == HttpStatus.SERVER_ERROR) {
        print("server error");
    }
    return 0;
}`,
    },
    {
      type: 'exercise',
      ex: {
        id: 'enums-ex1',
        difficulty: 'easy',
        prompt: `Declare an enum \`Direction\` with variants \`NORTH\`, \`EAST\`, \`SOUTH\`, \`WEST\` (implicit values). Set a variable to \`EAST\` and print its ordinal as an \`int\`. The program should print \`1\`.`,
        starter: `// declare enum Direction here

int main() {
    Direction d = /* EAST */;
    print(/* the ordinal of d as an int */);
    return 0;
}`,
        check: {
          kind: 'output',
          expected: '1',
        },
        hints: [
          'Implicit values start at 0, so NORTH=0, EAST=1, ...',
          'Read the ordinal with a cast: `(int) d`.',
        ],
        solution: `enum Direction { NORTH, EAST, SOUTH, WEST }

int main() {
    Direction d = Direction.EAST;
    print((int) d);
    return 0;
}`,
      },
    },
    {
      type: 'exercise',
      ex: {
        id: 'enums-ex2',
        difficulty: 'medium',
        prompt: `Given the \`Level\` enum, write a program that converts the integer \`2\` to a \`Level\`, then prints \`"high"\` if it equals \`Level.HIGH\` and \`"other"\` otherwise. It should print \`high\`.`,
        starter: `enum Level { LOW, MEDIUM, HIGH }

int main() {
    Level lv = /* convert the int 2 to a Level */;
    // print "high" or "other"

    return 0;
}`,
        check: {
          kind: 'output',
          expected: 'high',
        },
        hints: [
          'Cast an int to an enum with `(Level) 2`.',
          'HIGH is the third variant, ordinal 2, so the cast lands on `Level.HIGH`.',
          'Compare with `==`: `if (lv == Level.HIGH) { ... }`.',
        ],
        solution: `enum Level { LOW, MEDIUM, HIGH }

int main() {
    Level lv = (Level) 2;
    if (lv == Level.HIGH) {
        print("high");
    } else {
        print("other");
    }
    return 0;
}`,
      },
    },
    {
      type: 'exercise',
      ex: {
        id: 'enums-ex3',
        difficulty: 'medium',
        prompt: `**Predict the output.** Mind the explicit value and how the next variant continues from it.`,
        code: `enum Coin { PENNY = 1, NICKEL = 5, DIME, QUARTER = 25 }

int main() {
    print((int) Coin.PENNY);
    print((int) Coin.DIME);
    print((int) Coin.QUARTER);
    return 0;
}`,
        check: {
          kind: 'predict',
          expected: '1\n6\n25',
        },
        hints: [
          'DIME has no explicit value, so it is NICKEL + 1.',
          'NICKEL is 5, so DIME is 6.',
        ],
      },
    },
  ],
} satisfies Lesson
