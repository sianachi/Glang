import type { Lesson } from '../../types.ts'

export default {
  id: 'operator-overloading',
  title: 'Operator Overloading',
  blurb: 'Give your own classes the ergonomics of built-in types: `+`, `==`, `<`, indexing, and more.',
  blocks: [
    {
      type: 'prose',
      md: `Glang lets a class define what built-in operators mean for its values, so \`a + b\`, \`a == b\`, or \`v[0]\` read naturally on your own types. You declare an overload as a method whose name is \`operator\` followed by the symbol.

> Classes are not runnable in the in-browser interpreter, so the programs here are read-only \`static\` samples with their output shown beneath them.`,
    },
    {
      type: 'prose',
      md: `### Declaring overloads

An overload looks like an ordinary method: a return type, the keyword pair \`operator\` + symbol, and the right-hand operand as a parameter. The **left** operand is \`this\`. Here is a 2-D integer vector that overloads \`+\`, \`-\`, \`==\`, \`<\`, and indexing \`[]\`.`,
    },
    {
      type: 'static',
      caption: 'vec2.lang',
      code: `class Vec2 {
    int x;
    int y;

    Vec2(int x, int y) {
        this.x = x;
        this.y = y;
    }

    Vec2 operator+(Vec2 other) {
        return Vec2(this.x + other.x, this.y + other.y);
    }

    Vec2 operator-(Vec2 other) {
        return Vec2(this.x - other.x, this.y - other.y);
    }

    bool operator==(Vec2 other) {
        return this.x == other.x && this.y == other.y;
    }

    bool operator<(Vec2 other) {
        return this.magnitude_squared() < other.magnitude_squared();
    }

    int operator[](int index) {
        if (index == 0) {
            return this.x;
        }
        return this.y;
    }

    int magnitude_squared() {
        return this.x * this.x + this.y * this.y;
    }
}

int main() {
    Vec2 a = Vec2(3, 4);
    Vec2 b = Vec2(1, 2);

    Vec2 sum = a + b;       // operator+  -> Vec2(4, 6)
    Vec2 diff = a - b;      // operator-  -> Vec2(2, 2)
    a += b;                 // compound assignment runs operator+; a becomes Vec2(4, 6)

    print("sum:");
    print(sum[0]);          // operator[](0) -> x
    print(sum[1]);          // operator[](1) -> y

    print("difference:");
    print(diff[0]);
    print(diff[1]);

    print("a after += b equals sum:");
    print(a == sum);        // operator==

    print("a differs from diff:");
    print(a != diff);       // != is derived from operator== automatically

    print("diff is shorter than sum:");
    print(diff < sum);      // operator<

    return 0;
}`,
      output: `sum:
4
6
difference:
2
2
a after += b equals sum:
true
a differs from diff:
true
diff is shorter than sum:
true`,
    },
    {
      type: 'prose',
      md: `### What just happened

- \`a + b\` calls \`a\`'s \`operator+\` with \`b\` as \`other\`, returning a fresh \`Vec2(4, 6)\`.
- \`a += b\` is **compound assignment built on the binary operator**: it computes \`a + b\` and stores it back in \`a\`, so \`a\` ends up equal to \`sum\`.
- \`sum[0]\` and \`sum[1]\` dispatch to \`operator[]\`, which returns \`x\` for index \`0\` and \`y\` otherwise.
- \`diff < sum\` compares squared magnitudes: \`diff\` is \`2*2 + 2*2 = 8\`, \`sum\` is \`4*4 + 6*6 = 52\`, so \`8 < 52\` is \`true\`.`,
    },
    {
      type: 'callout',
      tone: 'tip',
      md: `Define **\`operator==\`** and you get **\`!=\`** for free — the compiler derives the negation automatically. You do not (and cannot) write a separate \`operator!=\`.`,
    },
    {
      type: 'callout',
      tone: 'note',
      md: `Overloads obey the language's normal rules: \`this\` is the left operand, the parameter is the right operand, and the return type is whatever the operator should yield (a new \`Vec2\` for \`+\`, a \`bool\` for \`==\` and \`<\`, an \`int\` for \`[]\`). The same overloads work even when the class lives in a \`namespace\` — once the type name is in scope, \`a + b\` just works with no qualification.`,
    },
    {
      type: 'exercise',
      ex: {
        id: 'operator-overloading-ex1',
        difficulty: 'medium',
        prompt: `**Predict the output.** This \`Complex\` number overloads \`+\` and \`==\`. Type exactly what the program prints.`,
        code: `class Complex {
    int re;
    int im;

    Complex(int re, int im) {
        this.re = re;
        this.im = im;
    }

    Complex operator+(Complex other) {
        return Complex(this.re + other.re, this.im + other.im);
    }

    bool operator==(Complex other) {
        return this.re == other.re && this.im == other.im;
    }
}

int main() {
    Complex a = Complex(1, 2);
    Complex b = Complex(3, 4);
    Complex c = a + b;
    print(c.re);
    print(c.im);
    print(c == Complex(4, 6));
    print(a == b);
    return 0;
}`,
        check: {
          kind: 'predict',
          expected: `4
6
true
false`,
        },
        hints: [
          '`a + b` adds component-wise: re = 1 + 3, im = 2 + 4.',
          '`operator==` compares both components; `c` matches `Complex(4, 6)` but `a` does not match `b`.',
        ],
      },
    },
    {
      type: 'exercise',
      ex: {
        id: 'operator-overloading-ex2',
        difficulty: 'medium',
        prompt: `**Predict the output.** Recall that \`!=\` is derived from \`operator==\`, and \`+=\` is built on \`operator+\`. Type exactly what this prints.`,
        code: `class Vec2 {
    int x;
    int y;

    Vec2(int x, int y) {
        this.x = x;
        this.y = y;
    }

    Vec2 operator+(Vec2 other) {
        return Vec2(this.x + other.x, this.y + other.y);
    }

    bool operator==(Vec2 other) {
        return this.x == other.x && this.y == other.y;
    }

    int operator[](int index) {
        if (index == 0) {
            return this.x;
        }
        return this.y;
    }
}

int main() {
    Vec2 p = Vec2(2, 3);
    Vec2 q = Vec2(2, 3);
    p += Vec2(1, 1);        // p becomes Vec2(3, 4)
    print(p[0]);
    print(p[1]);
    print(p == q);
    print(p != q);
    return 0;
}`,
        check: {
          kind: 'predict',
          expected: `3
4
false
true`,
        },
        hints: [
          '`p += Vec2(1, 1)` runs `operator+`, so `p` becomes `Vec2(3, 4)`.',
          '`p[0]`/`p[1]` are the updated components; `p == q` is now false, so `p != q` is true.',
        ],
      },
    },
  ],
} satisfies Lesson
