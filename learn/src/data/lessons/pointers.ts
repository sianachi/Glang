import type { Lesson } from '../../types.ts'

export default {
  id: 'pointers',
  title: 'Pointers',
  blurb: 'Pointer types, taking an address with &, dereferencing with *, and reading through ->.',
  blocks: [
    {
      type: 'prose',
      md: `A **pointer** is a value that holds the *address* of another value. Glang is manually managed and C-style, so pointers are everywhere: they let one function read or modify a variable that lives in another.

Any type can be made into a pointer type by adding \`*\`:
- \`int*\` — pointer to an \`int\`
- \`int**\` — pointer to a pointer to an \`int\`
- \`Dog*\` — pointer to a \`Dog\` instance
- \`void*\` — an untyped pointer that can hold *any* pointer

A \`void*\` is the universal pointer: converting to or from it is always **explicit** (you write the cast yourself).`,
    },
    {
      type: 'prose',
      md: `Two unary operators connect a value and its address:

- \`&x\` takes the **address of** \`x\`. If \`x\` is an \`int\`, then \`&x\` has type \`int*\`.
- \`*p\` **dereferences** \`p\` — it reads (or writes) the value \`p\` points at.

So \`&\` and \`*\` are inverses: \`*(&x)\` is just \`x\`.`,
    },
    {
      type: 'run',
      caption: 'address.lang',
      code: `int main() {
    int x = 10;
    int* p = &x;   // p points at x

    print(*p);     // read through the pointer -> 10

    *p = 99;       // write through the pointer
    print(x);      // x itself changed -> 99
    return 0;
}`,
    },
    {
      type: 'prose',
      md: `The most common use of pointers is the **out-parameter**: a function takes a pointer so it can hand a result back through it. Here \`swap\` exchanges two callers' variables by writing through the pointers it was given.`,
    },
    {
      type: 'run',
      caption: 'swap.lang',
      code: `void swap(int* a, int* b) {
    int t = *a;   // remember what a points at
    *a = *b;      // copy b's value into a's slot
    *b = t;       // copy the saved value into b's slot
}

int main() {
    int x = 3;
    int y = 7;
    swap(&x, &y);   // pass the addresses
    print(x);       // 7
    print(y);       // 3
    return 0;
}`,
    },
    {
      type: 'prose',
      md: `When a pointer points at an object, you reach a field with \`->\`. The expression \`p->field\` is exactly shorthand for \`(*p).field\`: dereference \`p\`, then read \`field\`.

A pointer can be compared against \`null\` to check whether it points at anything:

\`\`\`c
if (p == null) {
    // nothing to dereference
}
\`\`\``,
    },
    {
      type: 'callout',
      tone: 'gotcha',
      md: `**Dereferencing \`null\` is undefined behaviour** — there is no value at address \`null\`, so \`*p\` when \`p == null\` can crash or corrupt memory. Always null-check a pointer before dereferencing it if it might be absent.`,
    },
    {
      type: 'callout',
      tone: 'gotcha',
      md: `Member access binds tighter than the unary \`*\`. So \`*x.get(i)\` parses as \`*(x.get(i))\`, **not** \`(*x).get(i)\`. Likewise \`!f(x)\` is \`(!f)(x)\`. When mixing prefix operators with calls or member access, **parenthesise** to say exactly what you mean.`,
    },
    {
      type: 'callout',
      tone: 'note',
      md: `The in-browser runner supports pointers only for the cases above: \`&x\` / \`*p\` on local primitives and out-parameters like \`void f(int* p) { *p = 1; }\`. Object pointers (\`Dog*\`), \`void*\`, and \`->\` are part of the full compiler but are shown here as read-only samples.`,
    },
    {
      type: 'static',
      caption: 'object_ptr.lang',
      code: `class Dog {
    string name;
    Dog(string n) { this.name = n; }
}

void rename(Dog* d, string n) {
    d->name = n;          // same as (*d).name = n
}

int main() {
    Dog rex = new Dog("Rex");
    rename(&rex, "Fido");
    print(rex.name);
    return 0;
}`,
      output: 'Fido',
    },
    {
      type: 'exercise',
      ex: {
        id: 'pointers-ex1',
        difficulty: 'easy',
        prompt: `Finish the \`addTo\` function so it adds \`amount\` to the integer that \`p\` points at, writing the result back through the pointer. The program should print \`15\`.`,
        starter: `void addTo(int* p, int amount) {
    // write *p + amount back through p

}

int main() {
    int total = 10;
    addTo(&total, 5);
    print(total);
    return 0;
}`,
        check: {
          kind: 'output',
          expected: '15',
        },
        hints: [
          'Read the current value with `*p`, add `amount`, then assign back to `*p`.',
          '`*p = *p + amount;` updates the caller\'s variable in place.',
        ],
        solution: `void addTo(int* p, int amount) {
    *p = *p + amount;
}

int main() {
    int total = 10;
    addTo(&total, 5);
    print(total);
    return 0;
}`,
      },
    },
    {
      type: 'exercise',
      ex: {
        id: 'pointers-ex2',
        difficulty: 'medium',
        prompt: `**Predict the output.** Trace how \`&\` and \`*\` move data between \`main\` and \`setBoth\`.`,
        code: `void setBoth(int* a, int* b, int v) {
    *a = v;
    *b = v + 1;
}

int main() {
    int x = 0;
    int y = 0;
    setBoth(&x, &y, 5);
    print(x);
    print(y);
    print(x + y);
    return 0;
}`,
        check: {
          kind: 'predict',
          expected: '5\n6\n11',
        },
        hints: [
          '`*a = v` writes 5 into `x`; `*b = v + 1` writes 6 into `y`.',
          'After the call, `x` is 5 and `y` is 6, so `x + y` is 11.',
        ],
      },
    },
  ],
} satisfies Lesson
