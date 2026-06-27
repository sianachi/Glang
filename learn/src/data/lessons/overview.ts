import type { Lesson } from '../../types.ts'

export default {
  id: 'overview',
  title: 'What Is Glang?',
  blurb: 'A statically-typed, manually-managed, C-style language that compiles to C.',
  blocks: [
    {
      type: 'prose',
      md: `**Glang** (also written *GScript*) is a small systems language. It is:

- **Statically typed** — every variable, parameter, and return value has a type the analyser checks *before* the program runs.
- **Manually managed** — you decide when memory is allocated and freed. There is no garbage collector.
- **C-style** — the syntax is close to C and Java: braces for blocks, semicolons to end statements, \`int main()\` as the entry point.
- **Compiled to C** — the toolchain translates your \`.lang\` source into C, which a normal C compiler turns into a native binary.`,
    },
    {
      type: 'prose',
      md: `### Design goals

Glang is deliberately small. Its guiding goals are:

1. **Simple, unambiguous syntax** — close to C/Java, with no surprising parses.
2. **Explicit control over memory** — allocation and freeing are things you write, not things that happen behind your back.
3. **A small, auditable runtime** — the built-in runtime is tiny. The only built-in I/O is \`print\`; richer facilities (dynamic arrays, maps, string builders) live in a standard library *written in Glang itself*.
4. **A type system expressive enough to write that standard library** — the language is powerful enough to bootstrap its own batteries.`,
    },
    {
      type: 'callout',
      tone: 'note',
      md: `No GC and **no implicit allocations**. If memory is allocated on the heap, it is because your code asked for it. This makes Glang predictable, but it also means *you* are responsible for freeing what you allocate.`,
    },
    {
      type: 'prose',
      md: `### Two ways to run the same program

Glang has **two execution paths** that share one front-end (loader, analyser, type checker):

- A **tree-walking interpreter** (written in Python) that runs your program directly — great for quick iteration and for the lessons in this platform.
- A **self-hosting compiler** that emits **C**, which \`gcc\` then turns into a fast native binary.

Both paths see the exact same parsed-and-checked program, so a correct program behaves identically either way.`,
    },
    {
      type: 'callout',
      tone: 'tip',
      md: `"**Self-hosting**" means the compiler is written *in Glang*. The lexer, parser, analyser, and the AST-to-C emitter are all Glang source. Python is needed only once, to bootstrap the very first compiler; after that the language compiles itself.`,
    },
    {
      type: 'prose',
      md: `Here is the smallest complete Glang program. Press **Run** — it executes in the interpreter right here in your browser.`,
    },
    {
      type: 'run',
      caption: 'hello.lang',
      code: `int main() {
    print("Hello, Glang!");
    return 0;
}`,
    },
    {
      type: 'prose',
      md: `Already visible: execution begins at \`main\`, \`print\` writes one line of output, and \`return 0;\` reports success to the operating system. We will unpack each of these in the lessons that follow.`,
    },
    {
      type: 'exercise',
      ex: {
        id: 'overview-ex1',
        difficulty: 'intro',
        prompt: `**Predict the output.** Read this tiny program and type exactly what it prints.`,
        code: `int main() {
    print("Glang");
    print("compiles");
    print("to C");
    return 0;
}`,
        check: {
          kind: 'predict',
          expected: 'Glang\ncompiles\nto C',
        },
        hints: [
          'Each `print` writes its argument followed by a newline.',
          'Three `print` calls produce three lines, in order.',
        ],
      },
    },
  ],
} satisfies Lesson
