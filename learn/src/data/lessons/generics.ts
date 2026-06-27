import type { Lesson } from '../../types.ts'

export default {
  id: 'generics',
  title: 'Generics',
  blurb: 'Write a class or function once, use it at many types — with monomorphization.',
  blocks: [
    {
      type: 'prose',
      md: `**Generics** let you write a class or function once and reuse it across many types, without giving up static type checking. You introduce **type parameters** in angle brackets — \`<T>\`, \`<K, V>\` — and use them wherever a concrete type would normally go.`,
    },
    {
      type: 'callout',
      tone: 'note',
      md: `Generics, classes, and \`new\` are outside the in-browser interpreter's subset, so the programs here are **read-only samples with their exact output**. Hand-trace them and predict the output in the exercises.`,
    },
    {
      type: 'prose',
      md: `## Generic classes

A type parameter after the class name — \`class Box<T>\` — can be used for fields, constructor parameters, and method return types throughout the class body:`,
    },
    {
      type: 'static',
      caption: 'box.lang',
      code: `class Box<T> {
    T value;

    Box(T v) {
        this.value = v;
    }

    T get() {
        return this.value;
    }
}

int main() {
    Box<int> a = Box<int>(42);
    Box<string> b = Box<string>("hi");
    print(a.get());     // 42
    print(b.get());     // hi
    return 0;
}`,
      output: `42
hi`,
    },
    {
      type: 'prose',
      md: `You name the concrete type at the use site: \`Box<int>\` and \`Box<string>\` are two distinct, fully type-checked types built from the same template.

## Monomorphization

Glang generics are **monomorphized**: the compiler generates a separate concrete version of the class or function **for each distinct type it is used with**. \`Box<int>\` and \`Box<string>\` become two real classes in the compiled output — there is no boxing, no runtime type tag, and no shared erased representation. You get the same machine code you'd have written by hand for each type.`,
    },
    {
      type: 'prose',
      md: `## Generic functions

Functions can take type parameters too. The parameter list goes right after the function name: \`T identity<T>(T x)\`.`,
    },
    {
      type: 'static',
      caption: 'identity.lang',
      code: `T identity<T>(T x) {
    return x;
}

int main() {
    print(identity<int>(7));
    print(identity<string>("glang"));
    return 0;
}`,
      output: `7
glang`,
    },
    {
      type: 'callout',
      tone: 'gotcha',
      md: `**Generic function calls need explicit type arguments today.** You must write \`identity<int>(7)\`, not \`identity(7)\` — type inference for generic *functions* is future work. (Generic *classes* are written with their type argument anyway, e.g. \`Box<int>(...)\`, so this only bites on free functions.)`,
    },
    {
      type: 'callout',
      tone: 'warn',
      md: `**Type parameters are unconstrained today** — there are no bounds like \`<T extends Comparable>\`. A generic body can only use operations valid for *every* possible \`T\`. If a particular instantiation uses an operation the chosen type doesn't support, the error surfaces when that concrete version is generated, not at the generic declaration.`,
    },
    {
      type: 'prose',
      md: `## Multiple type parameters

A generic can take more than one type parameter — separate them with commas, as in \`class Map<K, V>\` or a free function \`List<U> select<T, U>(...)\`. Each is bound independently at the use site.`,
    },
    {
      type: 'exercise',
      ex: {
        id: 'generics-ex1',
        difficulty: 'easy',
        prompt: `**Predict the output.** \`Pair<T>\` uses the same type parameter twice. Both elements here are \`int\`.`,
        code: `class Pair<T> {
    T first;
    T second;

    Pair(T a, T b) {
        this.first = a;
        this.second = b;
    }

    T sum() {
        return this.first + this.second;
    }
}

int main() {
    Pair<int> p = Pair<int>(3, 4);
    print(p.sum());
    print(p.first);
    return 0;
}`,
        check: {
          kind: 'predict',
          expected: '7\n3',
        },
        hints: [
          'With `T = int`, `sum()` returns `3 + 4`.',
          '`p.first` is the first constructor argument.',
        ],
      },
    },
    {
      type: 'exercise',
      ex: {
        id: 'generics-ex2',
        difficulty: 'medium',
        prompt: `**Predict the output.** Note the explicit type arguments on each call to the generic function \`pick\`.`,
        code: `T pick<T>(bool cond, T a, T b) {
    if (cond) {
        return a;
    }
    return b;
}

int main() {
    print(pick<int>(true, 10, 20));
    print(pick<string>(false, "yes", "no"));
    return 0;
}`,
        check: {
          kind: 'predict',
          expected: '10\nno',
        },
        hints: [
          '`pick<int>(true, 10, 20)` — the condition is `true`, so it returns `a`.',
          '`pick<string>(false, "yes", "no")` — the condition is `false`, so it returns `b`.',
        ],
      },
    },
  ],
} satisfies Lesson
