import type { Lesson } from '../../types.ts'

export default {
  id: 'object-modifiers',
  title: 'Object Modifiers',
  blurb: 'Add methods to an existing type from outside its definition — like C# extension methods.',
  blocks: [
    {
      type: 'prose',
      md: `An **object modifier** adds methods to an existing type *from outside* its definition — much like extension methods in C# or extensions in Swift. The type being extended never has to be touched: you can decorate a class you do not own, or even a primitive like \`string\`.

A modifier block contains **only method declarations** — no fields, no constructor, no \`static\` members. Inside each method, \`this\` refers to the receiver value.`,
    },
    {
      type: 'prose',
      md: `### Declaring a modifier

The syntax is \`modifier for TypeName { ... }\`. Every method you add can use \`this\` to reach the receiver, exactly as if it had been written inside the class.`,
    },
    {
      type: 'static',
      caption: 'point_ext.lang',
      code: `class Point {
    int x;
    int y;
    Point(int x, int y) { this.x = x; this.y = y; }
}

modifier for Point {
    int manhattan() {
        return this.x + this.y;
    }
}

int main() {
    Point* p = new Point(3, 4);
    print(p.manhattan());
    return 0;
}`,
      output: '7',
    },
    {
      type: 'callout',
      tone: 'note',
      md: `\`manhattan\` lives outside \`Point\`, yet it is called like any other method (\`p.manhattan()\`) and has full access to \`this.x\` / \`this.y\`. The class definition was not modified at all.`,
    },
    {
      type: 'prose',
      md: `### Primitive targets

Modifiers may target primitive types such as \`string\`. When the receiver is a primitive, \`this\` has that primitive type **directly** — it is not a pointer. So inside a \`modifier for string\`, \`this\` is the string itself, and you can pass it straight to builtins like \`len\`.`,
    },
    {
      type: 'static',
      caption: 'string_ext.lang',
      code: `modifier for string {
    int size() { return len(this); }
    bool startsWith(char c) { return len(this) > 0 && this[0] == c; }
}

int main() {
    print("hello".size());
    bool ok = "glang".startsWith('g');
    print(ok);
    return 0;
}`,
      output: '5\ntrue',
    },
    {
      type: 'prose',
      md: `### Generic modifiers

For a generic type, the modifier is parameterised with the same type variables: \`modifier<T> for List<T> { ... }\`. The type variable \`T\` is bound at instantiation time — the compiler **monomorphizes** the modifier, generating a concrete method for every distinct \`List<X>\` the program actually uses, following the same rules as generic classes and functions.`,
    },
    {
      type: 'static',
      caption: 'list_ext.lang',
      code: `import "std/list.lang";

modifier<T> for List<T> {
    bool isEmpty() {
        return this.length() == 0;
    }
}

int main() {
    List<int> xs = List<int>();
    print(xs.isEmpty());
    xs.add(42);
    print(xs.isEmpty());
    return 0;
}`,
      output: 'true\nfalse',
    },
    {
      type: 'callout',
      tone: 'tip',
      md: `\`modifier<T> for List<T>\` adds one logical \`isEmpty\` that works for \`List<int>\`, \`List<string>\`, and any other instantiation — the compiler stamps out a specialized copy per concrete element type behind the scenes.`,
    },
    {
      type: 'prose',
      md: `### Scope and visibility

Modifiers follow a few precise rules:

- A modifier is visible **from its declaration to the end of its file**, and to any file that **imports** it.
- Modifier methods are looked up **after** the class's own instance methods, so the class always wins. A modifier **cannot shadow** a method the class already defines.
- Registering the **same method name for the same type** from two modifiers in the same visible scope is a **compile error**.`,
    },
    {
      type: 'callout',
      tone: 'gotcha',
      md: `Because the class's own methods are consulted first, you cannot use a modifier to "override" existing behaviour — if \`List<T>\` already had \`length()\`, a modifier \`length()\` would simply never be reached. Modifiers *extend*; they do not *replace*.`,
    },
    {
      type: 'exercise',
      ex: {
        id: 'object-modifiers-ex1',
        difficulty: 'easy',
        prompt: `**Predict the output.** \`this\` is the string itself inside a \`modifier for string\`. Type exactly what this prints.`,
        code: `modifier for string {
    int size() { return len(this); }
    string shout() { return this + "!"; }
}

int main() {
    print("glang".size());
    print("hi".shout());
    return 0;
}`,
        check: {
          kind: 'predict',
          expected: '5\nhi!',
        },
        hints: [
          'For a primitive target, `this` is the value directly — here, the string.',
          '`len("glang")` is `5`; `shout` appends `"!"`.',
        ],
      },
    },
    {
      type: 'exercise',
      ex: {
        id: 'object-modifiers-ex2',
        difficulty: 'medium',
        prompt: `**Predict the output.** A modifier adds two methods to \`Rect\`, each using \`this\`. Type exactly what this prints.`,
        code: `class Rect {
    int w;
    int h;
    Rect(int w, int h) { this.w = w; this.h = h; }
}

modifier for Rect {
    int area() { return this.w * this.h; }
    int perimeter() { return 2 * (this.w + this.h); }
}

int main() {
    Rect* r = new Rect(3, 5);
    print(r.area());
    print(r.perimeter());
    return 0;
}`,
        check: {
          kind: 'predict',
          expected: '15\n16',
        },
        hints: [
          'A modifier on a class receives `this` as a pointer to the object; `this.w` reads its field.',
          '`area` is `3 * 5`; `perimeter` is `2 * (3 + 5)`.',
        ],
      },
    },
  ],
} satisfies Lesson
