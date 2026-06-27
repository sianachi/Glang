# Glang Learn — an interactive GScript learning platform

A browser-based course for **Glang (GScript)**, built with **React 19**,
**TypeScript**, and **Tailwind CSS v4** (via Vite). It teaches the whole
language — from `print` and `main` through pointers, classes, generics,
modifiers, exceptions, namespaces, and the memory model — with **runnable code**
and **auto-checked exercises**.

## Quick start

```bash
cd learn
npm install
npm run dev      # http://localhost:5173
```

Other scripts: `npm run typecheck` (`tsc --noEmit`), `npm run build`
(typechecks, then bundles into `dist/`), `npm run preview`.

## What's inside

- **50 lessons** across 16 modules, ordered as a path (sidebar shows progress).
- **106 exercises** — two kinds:
  - *Coding* exercises run your code in the browser and compare its output to the
    expected result.
  - *Predict-the-output* exercises check your reading of a program.
- **A live Glang interpreter** (`src/lib/glang/`) — a small tree-walking
  evaluator split into `lexer`, `parser`, `ast`, `values`, and `evaluator`
  modules, for the core language (primitives, control flow, functions,
  recursion, out-parameters, enums, casts, the string builtins). Every `Run`
  button and every auto-checked exercise executes through it. It is **not** the
  real toolchain (that compiles to C under `../Toolchain`); features beyond the
  core (classes, generics, the std library, exceptions, namespaces) are taught
  with worked examples and predict exercises instead of live execution.
- **Syntax highlighting** for Glang (`src/lib/highlighter.ts`) in every code
  block and the editable playgrounds.
- **Progress tracking** saved to `localStorage` (per lesson + per exercise).

> A real language server / in-browser native compiler is intentionally out of
> scope for now (you mentioned you'll tackle that later). The interpreter here
> is a teaching aid, kept faithful to the spec for the subset it covers.

## Project layout

```
learn/
├── index.html
├── tsconfig*.json
├── src/
│   ├── App.tsx                 # layout, hash routing, progress wiring
│   ├── types.ts                # the content schema (Lesson/Block/Exercise…)
│   ├── components/             # Sidebar, LessonView, Playground, Exercise, …
│   │   ├── ui/                  # WindowChrome, OutputPanel, icons
│   │   ├── exercise/           # PredictInput, HintList, ResultBanner, …
│   │   ├── lesson/             # LessonNav, CompletionToggle
│   │   ├── sidebar/            # ProgressMeter, ModuleNav
│   │   └── layout/             # MobileHeader
│   ├── hooks/                  # useProgress, useHashRoute
│   ├── lib/
│   │   ├── glang/              # lexer · parser · ast · values · evaluator · index
│   │   ├── checkExercise.ts    # exercise grading logic
│   │   └── highlighter.ts      # Glang tokenizer → colored spans
│   └── data/
│       ├── curriculum.ts       # modules → lessons (the table of contents)
│       └── lessons/*.ts         # one file per lesson (content + exercises)
└── AUTHORING.md                # the lesson schema + how to add/edit lessons
```

## Adding or editing a lesson

Read `AUTHORING.md`. In short: each lesson is an ES module under
`src/data/lessons/` exporting `{ id, title, blurb, blocks: [...] }`, then it's
imported and placed into a module in `src/data/curriculum.js`. Block types are
`prose`, `run` (editable + executed), `static` (read-only sample with known
output), `callout`, and `exercise`.

The course content is validated by running every `run` block and every
`output`-checked exercise solution through the interpreter (all currently pass).
