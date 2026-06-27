import type { Lesson } from '../../types.ts'

// Lesson: Span & MemoryOwner (README §18, §8.6)
export default {
  id: 'span-memoryowner',
  title: 'Span & MemoryOwner',
  blurb: 'Own a contiguous heap block with MemoryOwner<T>, then view it through a non-owning, bounds-checked Span<T>.',
  blocks: [
    {
      type: 'prose',
      md: `The standard library gives you two cooperating types for contiguous memory:

- **\`MemoryOwner<T>\`** *owns* a heap block. It allocates \`alloc(T, n)\` up front and frees it when released. Methods: \`get\`, \`set\`, \`span\`, \`length\`, \`dispose\`.
- **\`Span<T>\`** is a *non-owning, bounds-checked* view over a block — conceptually a \`pointer + offset + length\`. Methods: \`get\`, \`set\`, \`slice\`, \`length\`, \`isEmpty\`.

The owner holds the storage; the span borrows it. This is the same split as C++'s \`std::vector\` vs \`std::span\`, or Rust's \`Vec\` vs \`&[T]\`.`,
    },
    {
      type: 'prose',
      md: `### The owner allocates and frees

Construct a \`MemoryOwner<int>(n)\` to grab a block of \`n\` elements, write into it with \`set(i, v)\`, read with \`get(i)\`, and ask its size with \`length()\`. When you are done, \`dispose()\` frees the block.`,
    },
    {
      type: 'static',
      caption: 'owner.lang',
      code: `import "std/memory.lang";

int main() {
    MemoryOwner<int> o = MemoryOwner<int>(8);
    for (int i = 0; i < 8; ++i) {
        o.set(i, i * 10);   // 0, 10, 20, ... 70
    }
    print(o.length());      // 8
    print(o.get(5));        // 50

    o.dispose();            // free the block
    return 0;
}`,
      output: '8\n50',
    },
    {
      type: 'prose',
      md: `### A span is a view — and \`slice\` is zero-copy

Call \`o.span()\` to get a \`Span<T>\` over the *whole* block. Then \`slice(start, end)\` carves out a sub-view of the half-open range \`[start, end)\`. Crucially, slicing **copies nothing**: the sub-span aliases the very same backing storage. Writing through the view is visible to the owner, and vice versa.`,
    },
    {
      type: 'static',
      caption: 'span_alias.lang',
      code: `import "std/memory.lang";

int main() {
    MemoryOwner<int> o = MemoryOwner<int>(8);
    for (int i = 0; i < 8; ++i) { o.set(i, i * 10); }

    Span<int> mid = o.span().slice(2, 6);  // view of o[2..6): 20, 30, 40, 50
    print(mid.length());                   // 4
    print(mid.get(0));                     // 20

    mid.set(0, 999);                       // aliases the backing block
    print(o.get(2));                       // 999  — the owner sees it

    o.dispose();
    return 0;
}`,
      output: '4\n20\n999',
    },
    {
      type: 'callout',
      tone: 'note',
      md: `\`slice(start, end)\` is **half-open**: it includes \`start\` and excludes \`end\`, so its length is \`end - start\`. \`slice(2, 6)\` over \`[0,10,20,30,40,50,60,70]\` yields the four elements at indices 2, 3, 4, 5 — i.e. \`20, 30, 40, 50\`. Both the span's own accessors (\`get\`/\`set\`) and the owner's are bounds-checked.`,
    },
    {
      type: 'callout',
      tone: 'warn',
      md: `**A span is valid only while its backing owner is live.** Because the span holds no ownership, using it after the owner has been disposed (or deleted) is a use-after-free. Keep the owner alive for at least as long as any span — or sub-span — that views it.`,
    },
    {
      type: 'prose',
      md: `### Free exactly once

The owner's block must be freed **exactly once** — not zero times (a leak), not twice (a double free). You have three styles, and you pick *one*:

1. **Value handle + \`dispose()\`** — \`MemoryOwner<int> o = MemoryOwner<int>(n); ... o.dispose();\`
2. **Heap handle + \`delete\`** — \`MemoryOwner<int>* h = new MemoryOwner<int>(n); ... delete h;\` (this runs \`~MemoryOwner\`, which frees the block).
3. **A \`using\` block** — automatic \`dispose()\` at scope exit (next section).

Do **not** combine them: disposing *and* deleting the same handle is a double free.`,
    },
    {
      type: 'static',
      caption: 'heap_owner.lang',
      code: `import "std/memory.lang";

int main() {
    // Heap style: new + delete; the destructor frees the block.
    MemoryOwner<byte>* buf = new MemoryOwner<byte>(3);
    buf->set(0, 0xFF);
    buf->set(1, (byte) 256);  // wraps to 0
    buf->set(2, 200);
    print(buf->get(0));       // 255
    print(buf->get(1));       // 0
    print(buf->length());     // 3
    delete buf;               // ~MemoryOwner() frees the block
    return 0;
}`,
      output: '255\n0\n3',
    },
    {
      type: 'prose',
      md: `### Automatic release with \`using\`

A \`using\` block (section 8.6) ties the lifetime to scope: when control leaves the block — by falling off the end, \`return\`, \`break\`, or \`continue\` — the owner is released automatically. For a class **value** like \`MemoryOwner<T>\`, that means its zero-argument \`dispose()\` runs at scope exit. So **don't call \`dispose()\` yourself inside the block** — that would double-free.`,
    },
    {
      type: 'static',
      caption: 'using_owner.lang',
      code: `import "std/memory.lang";

int main() {
    int total = 0;
    using (MemoryOwner<int> o = MemoryOwner<int>(5)) {
        for (int i = 0; i < 5; ++i) { o.set(i, i + 1); }   // 1..5
        for (int i = 0; i < o.length(); ++i) { total += o.get(i); }
    }                          // o.dispose() runs here, automatically
    print(total);              // 15  (1+2+3+4+5)
    return 0;
}`,
      output: '15',
    },
    {
      type: 'callout',
      tone: 'tip',
      md: `Inside a \`using\` header, the resource variable is implicitly \`const\` (you can't reassign \`o\`) and scoped to the block. Prefer \`using\` whenever the owner's lifetime matches a block — it makes the "free exactly once" rule impossible to get wrong, even on an early \`return\` or \`break\`.`,
    },
    {
      type: 'exercise',
      ex: {
        id: 'span-memoryowner-ex1',
        difficulty: 'easy',
        prompt: `**Predict the output.** A slice aliases the owner's storage. Trace the writes and predict what prints.`,
        code: `import "std/memory.lang";

int main() {
    MemoryOwner<int> o = MemoryOwner<int>(6);
    for (int i = 0; i < 6; ++i) { o.set(i, i); }  // 0,1,2,3,4,5

    Span<int> s = o.span().slice(1, 4);  // view of o[1..4): 1, 2, 3
    print(s.length());
    print(s.get(2));
    s.set(0, 50);                        // writes o[1]
    print(o.get(1));

    o.dispose();
    return 0;
}`,
        check: {
          kind: 'predict',
          expected: '3\n3\n50',
        },
        hints: [
          '`slice(1, 4)` is half-open: indices 1, 2, 3 of the owner, so length is `4 - 1 = 3`.',
          '`s.get(2)` is the span\'s third element, which is the owner\'s index 3 → value `3`.',
          '`s.set(0, 50)` writes the span\'s index 0, which aliases the owner\'s index 1.',
        ],
      },
    },
    {
      type: 'exercise',
      ex: {
        id: 'span-memoryowner-ex2',
        difficulty: 'medium',
        prompt: `**Predict the output.** This owner lives in a \`using\` block, so it is disposed automatically. Sub-slices alias the same block. What does it print?`,
        code: `import "std/memory.lang";

int main() {
    int first = 0;
    int last = 0;
    using (MemoryOwner<int> o = MemoryOwner<int>(4)) {
        for (int i = 0; i < 4; ++i) { o.set(i, (i + 1) * 100); }  // 100,200,300,400

        Span<int> whole = o.span();
        Span<int> tail = whole.slice(2, 4);  // 300, 400
        tail.set(1, 999);                    // writes o[3]

        first = whole.get(0);
        last = o.get(3);
    }                                        // dispose() runs automatically
    print(first);
    print(last);
    return 0;
}`,
        check: {
          kind: 'predict',
          expected: '100\n999',
        },
        hints: [
          '`tail = whole.slice(2, 4)` views owner indices 2 and 3 (values 300, 400).',
          '`tail.set(1, 999)` writes the tail\'s index 1, which is the owner\'s index 3 → becomes `999`.',
          'Do not call `dispose()` inside a `using` block — the block does it for you when control leaves.',
        ],
      },
    },
  ],
} satisfies Lesson
