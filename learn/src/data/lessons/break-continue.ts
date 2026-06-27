import type { Lesson } from '../../types.ts'

export default {
  id: 'break-continue',
  title: 'Break & Continue',
  blurb: 'Exit a loop early or skip to the next iteration.',
  blocks: [
    {
      type: 'prose',
      md: `Two keywords give you finer control inside any loop:

- **\`break;\`** immediately exits the nearest enclosing loop. Execution jumps to the first statement after the loop.
- **\`continue;\`** skips the rest of the current iteration and jumps to the next one (in a \`for\` loop, the post section still runs).

Both work in \`while\` and \`for\` loops.`,
    },
    {
      type: 'prose',
      md: `### Break: stop as soon as you're done

A common use is searching: walk through values and \`break\` the moment you find what you want, so you don't waste the rest of the loop.`,
    },
    {
      type: 'run',
      caption: 'find.lang',
      code: `int main() {
    for (int i = 1; i <= 100; ++i) {
        if (i * i > 50) {
            print(i);
            break;
        }
    }
    return 0;
}`,
    },
    {
      type: 'prose',
      md: `The loop header allows \`i\` up to \`100\`, but as soon as \`i * i\` passes \`50\` (at \`i = 8\`), we print and \`break\` — so only \`8\` is printed and the loop ends early.`,
    },
    {
      type: 'prose',
      md: `### Continue: skip the ones you don't want

\`continue\` keeps the loop going but abandons the current pass. Here we print only the odd numbers by skipping the evens.`,
    },
    {
      type: 'run',
      caption: 'odds.lang',
      code: `int main() {
    for (int i = 1; i <= 7; ++i) {
        if (i % 2 == 0) {
            continue;
        }
        print(i);
    }
    return 0;
}`,
    },
    {
      type: 'prose',
      md: `When \`i\` is even, \`continue\` jumps straight to the next iteration, so the \`print(i)\` below it never runs for those values. The output is the odd numbers \`1 3 5 7\`.`,
    },
    {
      type: 'callout',
      tone: 'note',
      md: `Both \`break\` and \`continue\` affect only the **nearest** enclosing loop. In nested loops, a \`break\` in the inner loop leaves the inner loop but the outer loop keeps running.`,
    },
    {
      type: 'exercise',
      ex: {
        id: 'break-continue-ex1',
        difficulty: 'easy',
        prompt: `Loop \`i\` from \`1\` upward and print each value, but use \`break\` to stop right after printing \`3\`. Expected output:

\`\`\`
1
2
3
\`\`\``,
        starter: `int main() {
    for (int i = 1; i <= 10; ++i) {
        print(i);
        // break once i reaches 3

    }
    return 0;
}`,
        check: {
          kind: 'output',
          expected: '1\n2\n3',
        },
        hints: [
          'Print first, then check whether `i == 3`.',
          'Inside that `if`, use `break;` to leave the loop.',
        ],
        solution: `int main() {
    for (int i = 1; i <= 10; ++i) {
        print(i);
        if (i == 3) {
            break;
        }
    }
    return 0;
}`,
      },
    },
    {
      type: 'exercise',
      ex: {
        id: 'break-continue-ex2',
        difficulty: 'medium',
        prompt: `**Predict the output.** \`continue\` skips multiples of 3. Trace the loop and type exactly what it prints.`,
        code: `int main() {
    for (int i = 1; i <= 8; ++i) {
        if (i % 3 == 0) {
            continue;
        }
        print(i);
    }
    return 0;
}`,
        check: {
          kind: 'predict',
          expected: '1\n2\n4\n5\n7\n8',
        },
        hints: [
          'Whenever `i` is a multiple of 3 (`3`, `6`), the `print` is skipped.',
          'Every other value of `i` from 1 to 8 is printed.',
        ],
      },
    },
  ],
} satisfies Lesson
