import type { Lesson } from '../../types.ts'

export default {
  id: 'collections',
  title: 'Generic Collections',
  blurb: 'The standard library containers: List, Stack, Queue, Map, Option, and Set.',
  blocks: [
    {
      type: 'prose',
      md: `Glang's standard library ships a family of **generic containers** built on the generics you just met. Each lives in its own module under \`std/\` and is brought in with an \`import\`:

\`\`\`
import "std/list.lang";
\`\`\`

The collection classes are **global** (no namespace prefix), so once imported you use \`List<int>\`, \`Map<string, int>\`, and friends directly.`,
    },
    {
      type: 'callout',
      tone: 'note',
      md: `These containers use generics, classes, and \`alloc\` — outside the in-browser interpreter's subset. The programs below are **read-only samples with their exact output**. Trace them and predict the output in the exercises.`,
    },
    {
      type: 'callout',
      tone: 'tip',
      md: `Every collection is **growable and generic**, backed by a contiguous \`alloc(T, cap)\` block that **doubles in capacity when it fills**. You never set a size up front — just \`add\`/\`push\`/\`enqueue\` and it grows as needed.`,
    },
    {
      type: 'prose',
      md: `## \`List<T>\` — a growable array

The workhorse. Key methods: \`add\`, \`get\`, \`set\`, \`contains\`, \`removeAt\`, \`length\`, \`isEmpty\`, \`clear\`, and \`span\` (a non-owning view). Indices are zero-based. Here's the canonical example from the spec:`,
    },
    {
      type: 'static',
      caption: 'list.lang',
      code: `import "std/list.lang";

int main() {
    List<int> xs = List<int>();
    xs.add(10);
    xs.add(20);
    xs.add(30);
    print(xs.length());     // 3
    print(xs.get(1));       // 20
    print(xs.contains(20)); // true
    xs.removeAt(0);         // drops 10
    print(xs.get(0));       // 20
    print(xs.length());     // 2
    return 0;
}`,
      output: `3
20
true
20
2`,
    },
    {
      type: 'prose',
      md: `## \`Stack<T>\` — last-in, first-out

A LIFO stack: \`push\`, \`pop\` (removes and returns the top), \`peek\` (returns the top without removing), \`length\`, \`isEmpty\`.

## \`Queue<T>\` — first-in, first-out

A FIFO queue backed by a **ring buffer**: \`enqueue\`, \`dequeue\` (removes and returns the front), \`peek\` (front without removing), \`length\`, \`isEmpty\`.`,
    },
    {
      type: 'static',
      caption: 'stack_queue.lang',
      code: `import "std/stack.lang";
import "std/queue.lang";

int main() {
    Stack<int> s = Stack<int>();
    s.push(1);
    s.push(2);
    s.push(3);
    print(s.pop());      // 3  (last in, first out)
    print(s.peek());     // 2  (now on top)
    print(s.length());   // 2

    Queue<string> q = Queue<string>();
    q.enqueue("a");
    q.enqueue("b");
    print(q.dequeue());  // a  (first in, first out)
    print(q.peek());     // b
    return 0;
}`,
      output: `3
2
2
a
b`,
    },
    {
      type: 'prose',
      md: `## \`Map<K, V>\` — an association map

A key/value store: \`set\` (insert or update), \`getOr\` (value for a key, or a fallback if absent), \`has\`, \`remove\`, \`length\`. It uses a **linear search**, so it works for any key type that supports \`==\` (a hashed map awaits a generic hashing mechanism).

## \`Option<T>\` — a present-or-absent value

A typed "maybe": \`setSome\` / \`setNone\` to fill it, \`isSome\` / \`isNone\` to test it, \`get\` to read the value, and \`getOr\` for a fallback when empty.`,
    },
    {
      type: 'static',
      caption: 'map_option.lang',
      code: `import "std/map.lang";
import "std/option.lang";

int main() {
    Map<string, int> ages = Map<string, int>();
    ages.set("ada", 36);
    ages.set("alan", 41);
    print(ages.has("ada"));          // true
    print(ages.getOr("ada", -1));    // 36
    print(ages.getOr("grace", -1));  // -1  (absent -> fallback)
    print(ages.length());            // 2

    Option<int> found = Option<int>();
    found.setSome(99);
    print(found.isSome());           // true
    print(found.getOr(0));           // 99
    found.setNone();
    print(found.isNone());           // true
    print(found.getOr(0));           // 0   (empty -> fallback)
    return 0;
}`,
      output: `true
36
-1
2
true
99
true
0`,
    },
    {
      type: 'prose',
      md: `## \`Set<T>\` — a collection of unique values

A set ignores duplicate inserts. Methods include \`add\`, \`contains\`, \`remove\`, \`size\`, \`isEmpty\`, and \`clear\`. Membership is checked with \`==\`, so it works for any comparable element type.`,
    },
    {
      type: 'static',
      caption: 'set.lang',
      code: `import "std/set.lang";

int main() {
    Set<int> seen = Set<int>();
    seen.add(1);
    seen.add(2);
    seen.add(2);             // duplicate — ignored
    seen.add(3);
    print(seen.size());      // 3
    print(seen.contains(2)); // true
    seen.remove(2);
    print(seen.contains(2)); // false
    return 0;
}`,
      output: `3
true
false`,
    },
    {
      type: 'callout',
      tone: 'gotcha',
      md: `\`Set\` uses \`size()\`, while \`List\`, \`Stack\`, \`Queue\`, and \`Map\` report their element count with \`length()\`. Watch the method name when you switch containers.`,
    },
    {
      type: 'exercise',
      ex: {
        id: 'collections-ex1',
        difficulty: 'easy',
        prompt: `**Predict the output.** The loop adds four values, then we inspect the list.`,
        code: `import "std/list.lang";

int main() {
    List<int> xs = List<int>();
    for (int i = 1; i <= 4; ++i) {
        xs.add(i * 10);
    }
    print(xs.length());
    print(xs.get(0));
    print(xs.get(3));
    print(xs.contains(25));
    return 0;
}`,
        check: {
          kind: 'predict',
          expected: '4\n10\n40\nfalse',
        },
        hints: [
          'The loop adds `10, 20, 30, 40` — four elements.',
          '`contains(25)` is `false`; the list holds multiples of ten only.',
        ],
      },
    },
    {
      type: 'exercise',
      ex: {
        id: 'collections-ex2',
        difficulty: 'easy',
        prompt: `**Predict the output.** Remember a \`Stack\` is last-in, first-out, and \`pop\` removes the top while \`peek\` does not.`,
        code: `import "std/stack.lang";

int main() {
    Stack<int> s = Stack<int>();
    s.push(5);
    s.push(6);
    s.push(7);
    print(s.pop());
    print(s.pop());
    print(s.length());
    print(s.peek());
    return 0;
}`,
        check: {
          kind: 'predict',
          expected: '7\n6\n1\n5',
        },
        hints: [
          'Two `pop`s remove `7` then `6`, leaving only `5`.',
          '`peek` returns the remaining top without removing it.',
        ],
      },
    },
    {
      type: 'exercise',
      ex: {
        id: 'collections-ex3',
        difficulty: 'medium',
        prompt: `**Predict the output.** Note that \`set\` on an existing key *updates* rather than inserts.`,
        code: `import "std/map.lang";

int main() {
    Map<string, int> m = Map<string, int>();
    m.set("x", 1);
    m.set("y", 2);
    m.set("x", 9);   // key "x" already present — updates it
    print(m.length());
    print(m.getOr("x", -1));
    print(m.getOr("z", -1));
    return 0;
}`,
        check: {
          kind: 'predict',
          expected: '2\n9\n-1',
        },
        hints: [
          'Re-setting `"x"` updates its value; it does not add a new entry, so `length()` stays `2`.',
          '`getOr("z", -1)` returns the fallback because `"z"` was never set.',
        ],
      },
    },
  ],
} satisfies Lesson
