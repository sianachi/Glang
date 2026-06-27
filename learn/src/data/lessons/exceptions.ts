import type { Lesson } from '../../types.ts'

export default {
  id: 'exceptions',
  title: 'Exceptions',
  blurb: 'Throw, try, and catch: object-based error handling with a class hierarchy.',
  blocks: [
    {
      type: 'prose',
      md: `Glang has **object-based exception handling**. The built-in \`Exception\` class is always available — you never import or redeclare it. It carries a single \`string message\`:

\`\`\`
class Exception {
    string message;
    Exception(string msg) { ... }   // built-in — do not redeclare
}
\`\`\`

You signal an error by **throwing** a pointer to an \`Exception\` (or a subclass), and you recover from it with **\`try\` / \`catch\`**.`,
    },
    {
      type: 'callout',
      tone: 'note',
      md: `Exceptions involve classes, \`new\`, and pointers — features the in-browser interpreter cannot run. The programs below are shown as **read-only samples with their exact output**. Trace them by hand and predict the output in the exercises.`,
    },
    {
      type: 'prose',
      md: `## Defining your own exception types

Subclass \`Exception\` to give errors meaningful names. The constructor forwards the message to the base class with \`: super(msg)\`. Subclasses can themselves be subclassed, forming a hierarchy:`,
    },
    {
      type: 'static',
      caption: 'hierarchy.lang',
      code: `class IOException extends Exception {
    IOException(string msg) : super(msg) { }
}

class NetworkException extends IOException {
    NetworkException(string msg) : super(msg) { }
}`,
      output: '',
    },
    {
      type: 'prose',
      md: `Here \`NetworkException\` *is an* \`IOException\`, which *is an* \`Exception\`. That hierarchy is what \`catch\` clauses match against.

## Throwing

\`throw\` takes a **pointer to an \`Exception\` subclass** (you allocate it with \`new\`) and is a **diverging statement** — control never falls through past a \`throw\`, just like \`return\`:

\`\`\`
throw new IOException("file not found");
\`\`\`

## Catching

A \`try\` block is followed by one or more typed \`catch\` clauses. They are matched **top-to-bottom by class hierarchy, and the first match wins**. A handler for a base type also catches all of its subclasses:`,
    },
    {
      type: 'static',
      caption: 'catch_order.lang',
      code: `class IOException extends Exception {
    IOException(string msg) : super(msg) { }
}

class NetworkException extends IOException {
    NetworkException(string msg) : super(msg) { }
}

void fetch(bool fail) {
    if (fail) {
        throw new NetworkException("connection refused");
    }
    print("fetched ok");
}

int main() {
    try {
        fetch(false);
        fetch(true);              // throws — rest of the try is skipped
        print("unreachable");
    } catch (IOException* e) {
        print("caught IOException:");
        print(e->message);
    } catch (Exception* e) {
        print("caught Exception:");
        print(e->message);
    }
    return 0;
}`,
      output: `fetched ok
caught IOException:
connection refused`,
    },
    {
      type: 'prose',
      md: `Even though a \`NetworkException\` was thrown, the **first matching handler** is \`catch (IOException* e)\` — because \`NetworkException\` is a subclass of \`IOException\`. The \`Exception\` handler below it never runs.

- \`catch (IOException* e)\` catches \`IOException\` **and every subclass** (like \`NetworkException\`).
- \`catch (Exception* e)\` is the **catch-all** — it matches anything.
- The exception pointer (\`e\`) gives you the message via \`e->message\`.`,
    },
    {
      type: 'callout',
      tone: 'gotcha',
      md: `Order matters. If you put \`catch (Exception* e)\` **first**, it swallows everything and the more specific handlers below it become dead code. List specific types first, the catch-all last.`,
    },
    {
      type: 'prose',
      md: `## Propagation

A thrown exception isn't confined to the function that threw it. It **propagates up through function calls and out of loops** until some enclosing \`try\` intercepts it. Nothing else — not a function return, not the end of a loop — stops it.`,
    },
    {
      type: 'static',
      caption: 'propagate.lang',
      code: `class TooBig extends Exception {
    TooBig(string msg) : super(msg) { }
}

int check(int n) {
    if (n > 10) {
        throw new TooBig("value too big");
    }
    return n * 2;
}

int main() {
    try {
        print(check(3));      // 6
        print(check(20));     // throws — jumps to catch
        print(check(5));      // never reached
    } catch (TooBig* e) {
        print(e->message);
    }
    return 0;
}`,
      output: `6
value too big`,
    },
    {
      type: 'prose',
      md: `## Unhandled exceptions

If an exception is never caught, the program **prints \`Unhandled ClassName: message\` to stderr and exits with code 1**:`,
    },
    {
      type: 'static',
      caption: 'unhandled.lang',
      code: `class NetworkException extends Exception {
    NetworkException(string msg) : super(msg) { }
}

int main() {
    throw new NetworkException("connection refused");
    return 0;   // never reached
}`,
      output: `Unhandled NetworkException: connection refused`,
    },
    {
      type: 'callout',
      tone: 'note',
      md: `That \`Unhandled ...\` line goes to **stderr**, not stdout, and the process exit code is **1** rather than \`0\`.`,
    },
    {
      type: 'prose',
      md: `## Re-throwing from a catch

A \`throw\` inside a \`catch\` block **re-raises** — either the same exception or a new one. This lets you log at a low level and let a higher level decide what to do:`,
    },
    {
      type: 'static',
      caption: 'rethrow.lang',
      code: `class ParseException extends Exception {
    ParseException(string msg) : super(msg) { }
}

int parse(string s) {
    if (s == "") {
        throw new ParseException("empty input");
    }
    return 1;
}

int main() {
    try {
        try {
            parse("");
        } catch (ParseException* e) {
            print("logging:");
            print(e->message);
            throw new ParseException("re-raised: " + e->message);
        }
    } catch (Exception* e) {
        print("outer caught:");
        print(e->message);
    }
    return 0;
}`,
      output: `logging:
empty input
outer caught:
re-raised: empty input`,
    },
    {
      type: 'callout',
      tone: 'warn',
      md: `There is **no \`finally\`** in v1 — clean-up code can't be attached to a \`try\`. Free resources explicitly at the end of the relevant scope, or inside each handler.`,
    },
    {
      type: 'callout',
      tone: 'tip',
      md: `**Always-returns and try/catch.** When a function must return on every path, a \`try\`/\`catch\` counts as "always returns" **only if the try body and *every* catch handler always return**. A handler that falls off its end leaves a path with no return — and the analyser rejects it.`,
    },
    {
      type: 'exercise',
      ex: {
        id: 'exceptions-ex1',
        difficulty: 'easy',
        prompt: `**Predict the output.** A \`BException\` is thrown. Remember: handlers match top-to-bottom, first match wins, and a base-type handler catches its subclasses.`,
        code: `class AException extends Exception {
    AException(string msg) : super(msg) { }
}
class BException extends AException {
    BException(string msg) : super(msg) { }
}

int main() {
    try {
        throw new BException("boom");
    } catch (AException* e) {
        print("A handler");
        print(e->message);
    } catch (BException* e) {
        print("B handler");
    }
    return 0;
}`,
        check: {
          kind: 'predict',
          expected: 'A handler\nboom',
        },
        hints: [
          '`BException` is a subclass of `AException`, so the `AException` handler matches it first.',
          'Because the first match wins, the `BException` handler below is never reached.',
        ],
      },
    },
    {
      type: 'exercise',
      ex: {
        id: 'exceptions-ex2',
        difficulty: 'easy',
        prompt: `**Predict the output.** Trace how the exception propagates out of \`check\` and skips the rest of the \`try\`.`,
        code: `class Bad extends Exception {
    Bad(string msg) : super(msg) { }
}

int check(int n) {
    if (n < 0) {
        throw new Bad("negative");
    }
    return n + 1;
}

int main() {
    try {
        print(check(4));
        print(check(-2));
        print(check(9));
    } catch (Bad* e) {
        print(e->message);
    }
    return 0;
}`,
        check: {
          kind: 'predict',
          expected: '5\nnegative',
        },
        hints: [
          '`check(4)` returns `4 + 1`.',
          '`check(-2)` throws, so neither the second `print` nor `check(9)` runs — control jumps straight to the `catch`.',
        ],
      },
    },
    {
      type: 'exercise',
      ex: {
        id: 'exceptions-ex3',
        difficulty: 'medium',
        prompt: `**Predict the output**, including what the exit behaviour would be. The \`Exception\` catch-all matches any thrown subclass.`,
        code: `class FileMissing extends Exception {
    FileMissing(string msg) : super(msg) { }
}

int main() {
    try {
        throw new FileMissing("config.txt");
    } catch (Exception* e) {
        print("handled by catch-all");
        print(e->message);
    }
    return 0;
}`,
        check: {
          kind: 'predict',
          expected: 'handled by catch-all\nconfig.txt',
        },
        hints: [
          '`catch (Exception* e)` is the catch-all, so it matches `FileMissing`.',
          'Because it is caught, the program returns `0` normally — there is no `Unhandled ...` line.',
        ],
      },
    },
  ],
} satisfies Lesson
