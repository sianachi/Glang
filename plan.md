# Glang Development Plan

## Already Shipped

enums, `const`, access modifiers, self-referential class types, string operations,
import system with `std/` prefix, file I/O built-ins, function pointers, operator
overloading, closures, generics via monomorphization, sized `alloc(T, n)` plus pointer
indexing, standard library (`std/math`, `char`, `string`, `io`, `List`, `Stack`,
`Queue`, `Map`, `Option`), `byte` and `byte[]`, `Span<T>`, `MemoryOwner<T>`, CLI
builtins (`getArgCount`, `getArg`, `printErr`, `exit`, `dieWith`), namespaces
(`namespace ns { ... }` + `ns::member`, used by the stdlib function modules
`math`, `chars`, `strings`, `io` and throughout `examples/`).

---

## Distribution

The Nuitka compiled-executable distribution (previously `scripts/build_nuitka.sh`
producing `dist/glang.dist/glang`) has been removed. Glang runs from the Python
source tree:

```bash
python3 main.py run examples/calc.lang
```

Two artifacts of that era intentionally remain, since they are harmless for
source runs and would be needed again by any future packaging effort:

- The CLI imports the loader from `glang_loader.loader`; the old `loader.loader`
  import path is a compatibility wrapper. (A top-level package named `loader`
  collided with Nuitka startup.)
- `Loader` resolves `std/...` imports via `GLANG_STDLIB` override first, then
  `stdlib/` beside the executable, then the source-tree `stdlib/`.

No Glang-to-C compiler is planned. Native code generation, self-hosting, and
ahead-of-time packaging are parked unless the project later needs them.

---

## Verification

```bash
python3 -m pytest tests/ -v
python3 examples/run_examples.py
```

---

## Future Work

Language/runtime work stays in the Python implementation first:

| Feature | Notes |
|---|---|
| Generic bounds | `<T extends Comparable>`; type params are unconstrained today |
| Generic type inference | Generic function calls still need explicit `f<int>(x)` |
| `using` declarations | Namespace members must be fully qualified outside their namespace |
| Error handling | Return-value style for now; `Result<T,E>` remains optional |
| Garbage collection | Still a possible standard-library/runtime experiment |
| `main` args | Current CLI exposes `getArgCount`/`getArg`; typed `main(argc, argv)` can come later |
| Variadic functions | Useful for printf-style stdlib functions |
