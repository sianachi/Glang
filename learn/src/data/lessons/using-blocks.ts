import type { Lesson } from '../../types.ts'

export default {
  id: 'using-blocks',
  title: 'using Resource Blocks',
  blurb: 'Deterministic, automatic cleanup at scope exit with the using statement.',
  blocks: [
    {
      type: 'prose',
      md: `Pairing every \`new\` with a \`delete\`, or every \`alloc\` with a \`free\`, on **every** path out of a function is tedious and error-prone — an early \`return\` in the middle is all it takes to leak. The C#-style **\`using\`** statement removes that burden: it releases the resource declared in its header when control leaves the block, **however it leaves**.

> \`using\`, \`new\`/\`delete\`, and \`alloc\`/\`free\` cannot run in the in-browser sandbox, so every program here is a read-only sample with its output shown. Trace the cleanup ordering by hand.`,
    },
    {
      type: 'prose',
      md: `## The shape

\`\`\`
using (T x = expr) {
    // use x
}   // x is released right here
\`\`\`

The release fires on **every** exit: falling off the end of the block, \`return\`, \`break\`, and \`continue\` all run the cleanup first.`,
    },
    {
      type: 'static',
      caption: 'using_basic.lang',
      code: `class File {
    string path;
    File(string p) { this.path = p; print("open " + p); }
    ~File() { print("close " + this.path); }
    void write(string s) { print(this.path + ": " + s); }
}

int main() {
    using (File* f = new File("log.txt")) {
        f->write("hello");
    }                          // ~File() runs here automatically
    print("after block");
    return 0;
}`,
      output: `open log.txt
log.txt: hello
close log.txt
after block`,
    },
    {
      type: 'prose',
      md: `## Cleanup runs even on early exit

The whole point is that you cannot forget the release on an early path. Here a \`return\` from inside the block still closes the file first.`,
    },
    {
      type: 'static',
      caption: 'using_return.lang',
      code: `class File {
    string path;
    File(string p) { this.path = p; print("open " + p); }
    ~File() { print("close " + this.path); }
}

int run(bool bad) {
    using (File* f = new File("log.txt")) {
        if (bad) {
            return 1;          // ~File() runs before the return propagates
        }
        return 0;              // ~File() runs here too
    }
}

int main() {
    print(run(true));
    return 0;
}`,
      output: `open log.txt
close log.txt
1`,
    },
    {
      type: 'prose',
      md: `## The release action depends on the declared type

\`using\` picks the right cleanup from the header type:

| Header type | Scope-exit action |
|---|---|
| \`T*\` where \`T\` is a class | \`delete\` semantics — destructor chain, then free |
| any other pointer | \`free\` |
| class **value** (not a pointer) | its zero-argument \`dispose()\` method |

A class **value** handle requires a \`dispose()\` method — it is a **compile error** to use one without it. And you must **not** call \`dispose()\` yourself inside the block; \`using\` owns that call.`,
    },
    {
      type: 'static',
      caption: 'using_kinds.lang',
      code: `class MemoryOwner {
    int n;
    MemoryOwner(int size) { this.n = size; print("own " + toString(size)); }
    void dispose() { print("dispose " + toString(this.n)); }
}

int main() {
    using (MemoryOwner o = MemoryOwner(8)) {   // class value -> dispose()
        print("using owner");
    }                                          // o.dispose() runs here

    using (int* p = alloc(int, 64)) {          // non-class pointer -> free
        p[0] = 1;
        print(p[0]);
    }                                          // free(p) runs here
    return 0;
}`,
      output: `own 8
using owner
dispose 8
1`,
    },
    {
      type: 'callout',
      tone: 'note',
      md: `For a \`T*\` where \`T\` is a class, \`using\` does full \`delete\` semantics — the destructor chain (derived-first, up to the base) then the free. For any other pointer (\`int*\`, \`byte*\`, …) it does a plain \`free\`. For a class value it calls \`dispose()\`. There is no cleanup for primitives — see below.`,
    },
    {
      type: 'prose',
      md: `## Rules and edge cases

- The resource variable is implicitly **\`const\`** — you cannot reassign it, and it is scoped to the block.
- A pointer resource that is **\`null\`**, or one you **already released** inside the body (an early \`delete\`/\`free\`), is **skipped** — no double free.
- **\`exit(...)\`** terminates the program immediately and **skips all disposals**, matching its skip-everything semantics.
- **Primitives** and **dispose-less class values** are rejected at **compile time** with: \`'using' requires a pointer or a class value with dispose()\`.`,
    },
    {
      type: 'static',
      caption: 'using_null.lang',
      code: `class Node {
    Node() { print("new node"); }
    ~Node() { print("~node"); }
}

int main() {
    using (Node* n = new Node()) {
        delete n;          // released early inside the body
    }                      // skipped — no double free
    print("done");
    return 0;
}`,
      output: `new node
~node
done`,
    },
    {
      type: 'callout',
      tone: 'gotcha',
      md: `\`using (int x = 5) { ... }\` does **not** compile — a primitive has nothing to release. Likewise a class value whose type has no \`dispose()\` is rejected at compile time. \`using\` is for *resources*: class pointers, other pointers, or disposable class values only.`,
    },
    {
      type: 'exercise',
      ex: {
        id: 'using-blocks-ex1',
        difficulty: 'medium',
        prompt: `**Predict the output.** The body releases the pointer early, so the \`using\` cleanup must not run it again.`,
        code: `class Conn {
    Conn() { print("connect"); }
    ~Conn() { print("disconnect"); }
}

int main() {
    using (Conn* c = new Conn()) {
        print("working");
        delete c;          // released here
    }                      // skipped: already released
    print("finished");
    return 0;
}`,
        check: {
          kind: 'predict',
          expected: 'connect\nworking\ndisconnect\nfinished',
        },
        hints: [
          'The destructor runs exactly once — at the explicit `delete` inside the body.',
          'The block exit is skipped because the pointer was already released (no double free).',
        ],
      },
    },
    {
      type: 'exercise',
      ex: {
        id: 'using-blocks-ex2',
        difficulty: 'hard',
        prompt: `**Predict the output.** A class **value** handle uses \`dispose()\`, and the block exits early with \`break\` inside a loop.`,
        code: `class Buf {
    int id;
    Buf(int i) { this.id = i; print("alloc " + toString(i)); }
    void dispose() { print("dispose " + toString(this.id)); }
}

int main() {
    for (int i = 0; i < 3; ++i) {
        using (Buf b = Buf(i)) {
            print("use " + toString(i));
            if (i == 1) {
                break;     // dispose() runs before the break
            }
        }                  // dispose() runs here on normal exit
    }
    print("loop done");
    return 0;
}`,
        check: {
          kind: 'predict',
          expected: 'alloc 0\nuse 0\ndispose 0\nalloc 1\nuse 1\ndispose 1\nloop done',
        },
        hints: [
          'Each loop iteration constructs a fresh `Buf`, and `dispose()` runs at every block exit.',
          'When `i == 1`, `break` exits the block (running `dispose 1`) and ends the loop — there is no `i == 2` iteration.',
        ],
      },
    },
  ],
} satisfies Lesson
