# Glang Roadmap — Web Platform

## North-star goals

1. **An HTTP web server written in Glang** — production-shaped: HTTP/1.1, keep-alive,
   handles untrusted input safely.
2. **A backend framework like FastAPI** — typed routing, request/response, middleware,
   dependency injection, JSON (de)serialization + validation from typed models.
3. **A fullstack web technology** — same-language client and server. Client side ships via
   a **new Glang→JS compiler backend**, with types/validation shared across both ends.

### Decisions locked

- **Concurrency: hybrid — a pool of event loops.** Each OS thread runs its own
  epoll/kqueue loop; connections are distributed across threads. Scales across cores *and*
  connection count. Implies: non-blocking sockets + a poller + threads + a work-distribution
  queue in the runtime, and **async handlers** in the language.
- **Fullstack client: compile Glang→JS.** A second emitter beside the C one; a JS port of
  the runtime; shared model/validation types between server and browser.
- **Memory: unmanaged by default; `managed` is a per-type opt-in that is automatic
  everywhere.** `class Foo {}` keeps today's manual `new`/`delete`/`alloc`/`free` (the
  default — existing code and stdlib unchanged, **zero overhead**). `managed class Bar {}`
  marks the *type* as GC-managed: **every** `Bar` reference, at every use site, is
  automatically tracked — you never `delete` it. The managed heap is **refcounted + a
  tracing cycle-collector**, designed as one system. Raw `alloc` blocks and raw pointers
  stay unmanaged primitives. This is the new linchpin — see **Phase 0.0**.

### Two workstreams this creates beyond stdlib

- **`async`/`await` language feature** — required for async handlers under the hybrid model.
  Per CLAUDE.md, a language feature must land in **both** implementations (Python
  interpreter + Glang compiler) across the whole pipeline. **Highest-risk, critical-path
  item.** Implementation options to evaluate in the design phase:
  - stackful coroutines in the runtime (`ucontext`/custom asm), exposed as a library — least
    compiler change;
  - `async`/`await` as a real language feature (compiler lowers each async fn to a
    state machine) — most ergonomic, most work;
  - callback/continuation-passing — no language change, poor ergonomics (fallback only).
- **Glang→JS backend** — a third target after `{Interpreter | C emitter}`: a `jsemit.lang`,
  a JS runtime mirroring `glang_runtime.c` semantics, and a mapping for the manual-memory
  model onto JS's GC (`alloc`→array, `free`→no-op; define pointer/`Span` semantics).

---

## Conventions (unchanged)

- **Data / container types** are top-level generic **classes**; **free-function modules**
  are wrapped in a **`namespace`**. Imports use `std/<name>.lang`.
- **Pure** = writable in `.lang` on existing primitives, no runtime change, works in both
  backends free. **Runtime** = new C builtins in `runtime/glang_runtime.c` **and** matching
  Python-interpreter builtins, added together with paired differential tests.
- **Python stays the test oracle.** Front-load Pure modules; pay the double-implementation
  tax only for genuinely Runtime-backed primitives.

### Repo-specific constraints driving the foundation

- **No bounds checking today** — `memory.lang` fakes it via `data[-1]`. Untrusted network
  input makes real bounds checks mandatory.
- **Strings are NUL-terminated `char*`** — binary-unsafe. All wire/binary I/O must use the
  new **`Bytes`** type, never `string`.
- **No automatic cleanup; manual `free`/`delete`** — a long-running server leaks unless we
  add region/arena lifetimes and leak detection.
- **Hybrid threads add data races** — shared state needs atomics + locks; per-request memory
  should stay thread-local (arenas) to avoid cross-thread frees.

---

# Phase 0.0 — Memory model: `managed` types (THE LINCHPIN — START HERE)

A language-level change, so it lands in **both** implementations across the whole pipeline
(lexer → parser → analyser → interpreter **and** emit.lang), per CLAUDE.md's "adding a
language feature" checklist. Design-first; this gates everything below.

## Status — what is implemented now

The **managed type surface** is implemented and passing across all four run paths
(Python interpreter, pytest, native `glangc`, self-hosted `glangi`):

- `managed class` keyword and the `T@` handle type, parsed/analysed/interpreted/emitted.
- `new` on a managed class yields a `T@`; `delete` on a handle is a type error.
- `@` requires a managed class; `@` and `*` are distinct and do not implicitly mix;
  handle↔handle subclass widening and `null` assignment/compare are allowed.
- Handles use dot member access (reference-like); fields/methods/aliasing/inheritance work.
- Runtime: a **tracked allocate-and-sweep-at-exit collector** (`glang_managed_alloc` +
  `atexit` sweep) — managed objects are reclaimed automatically, never leak, never UAF.
  Interpreters never free (host GC), so output is identical and differential tests pass.
- Example: `examples/managed_memory.lang` (+ golden); tests: `bootstrap/tests/test_managed.py`.

**Still future (this phase):** refcount write barriers, the tracing cycle-collector, the
shadow stack, atomic refcounts, `Root<T>` + managed-scope blocks, and per-class field maps.
The allocator seam (`glang_managed_alloc`) is where refcounting/cycle collection will attach.

**Core idea:** managed-ness is a property of the **type**, declared once. The analyser
records a `managed` flag per class; the emitter then emits GC machinery **only** for
references whose static type is managed. Unmanaged code emits exactly as today — no barriers,
no roots, no overhead. This is what makes a managed type "automatically managed wherever it
is called."

## Semantics to define

- **`managed class` = GC-tracked; `class` = manual (default).** New `managed` keyword.
  Managed objects need no `delete` (it's a compile error or no-op — decide). `class` keeps
  `new`/`delete` + destructor-on-delete, unchanged.
- **Automatic propagation.** Any value/field/param/return whose type is a managed class is
  tracked automatically — callers do nothing special. The type drives it, not the call site.
- **Managed handles get distinct syntax (decided).** Raw pointer stays `T*`; a managed
  handle is **`T@`** (AngelScript-style refcounted handle; `^` is the fallback sigil,
  subject to lexer availability). `*` and `@` are distinct types and do not implicitly mix —
  this is what lets the type checker enforce "managed wherever it's called." `new Bar()` on a
  `managed class` yields a `Bar@`; no `delete`. Affects the type system + every `show*`.
- **Allocation surface.** `new` on a managed class → `T@`. `alloc`/`free` and raw `T*` stay
  **unmanaged primitives** — the collector never tracks raw blocks.
- **Mixed-graph rules (decided).**
  - managed → unmanaged field (`@` holds `*`): raw, not traced; the programmer owns that
    lifetime.
  - managed → managed field (`@` holds `@`): traced normally.
  - **unmanaged → managed is forbidden directly** — a plain `class` may not declare a `T@`
    field. It must hold a **`Root<T>`** middle man instead (see below).
- **`Root<T>` — the unmanaged↔managed middle man (decided).** An *unmanaged* value type that
  pins its referent as a **GC root** on construction and unpins deterministically on scope
  exit (destructor / `using`). Unmanaged code never dereferences the handle directly; it
  **opens a managed scope** through the root, and only inside that scope is the `T@` live and
  root-tracked:
  ```
  class Server { Root<Cache> cache; }              // unmanaged: no bare @ field
  using (managed c = server.cache.enter()) {       // c : Cache@, valid only here
      c.put("k", v);
  }                                                // root machinery unwinds at scope exit
  ```
  Root set for the collector = shadow stack (in managed code) **+** registered `Root<T>`
  handles at unmanaged boundaries. No unmanaged field can hold an untracked managed pointer.
- **`managed` scope blocks (open detail).** Pin down the `managed { ... }` / `enter()` form:
  whether `managed` is a block keyword, what `enter()` returns, and how nested scopes
  compose. Smaller than the above; settle during the spike.
- **Finalizers vs `using`.** Destructors on managed objects become **finalizers** (run at
  collection — non-deterministic). `using` (§8.6) stays the deterministic-disposal escape
  hatch for resources (files, sockets). Document the timing difference.
- **Threads.** Managed refs shared across the pool need **atomic** refcounts; the cycle
  collector runs at **safepoints**. Per-thread allocation, share via the atomic path.

## The collector (refcount + tracing cycles, one design — managed types only)

| Piece | Where | Notes |
|---|---|---|
| Refcount write barriers | `emit.lang` | emitted only for managed-typed refs: retain/release on assign, param pass, return, scope exit |
| Per-class field maps | `emit.lang` + runtime | which fields of a managed class are managed → lets the tracer walk objects precisely |
| Root tracking | `emit.lang` + runtime | **shadow stack** (push managed locals to a thread-local root list) — portable, no platform stack maps; overhead only in code touching managed types |
| Cycle collector | runtime (C) | trial-deletion or mark-sweep backup over the managed heap; collects what refcounting can't |
| Atomic refcounts | runtime (C) | for cross-thread shared managed objects |
| Interpreter side | `bootstrap/` | already GC-like (never frees); model finalizer ordering for managed types; **tests must not observe finalizer timing** |
| JS backend | `jsemit.lang` (Phase 5) | managed → native JS objects (JS GC handles it); unmanaged → emulation |

## Migration (minimal — default is unchanged)

- **No forced audit:** existing stdlib stays `class` (unmanaged) and compiles identically.
- Opt specific types into `managed` only where the ergonomics pay off (e.g. request/response
  graphs, the router tree, framework objects with shared/cyclic ownership).
- Decide what `delete` on a managed object means (compile error vs no-op).

---

# Phase 0 — Runtime memory safety + foundation

The rest of the groundwork. Mostly **Runtime** (C + Python interpreter). Builds on the
Phase 0.0 model.

## Memory safety primitives

| Module | Namespace / Type | Kind | Exposes | Notes |
|---|---|---|---|---|
| `std/bytes.lang` | `Bytes` (class) | Runtime | bounds-checked binary buffer; read/write `int`/`float` LE/BE, slice, append, length | Replaces `string` for all wire I/O; checks **throw** instead of UB |
| `std/slice.lang` | `Slice<T>` (class) | Runtime | bounds-checked view over a block | Safe successor to `Span<T>` |
| `std/arena.lang` | `Arena` (class) | Runtime | bump allocate, `reset`, `destroy` (free-all-at-once) | **Per-request lifetime** → no per-request leaks; thread-local; complements managed GC for unmanaged blocks |
| `std/rc.lang` | `Rc<T>` / `Arc<T>` (class) | Runtime (Arc atomic) | explicit shared ownership for `unmanaged` types | The managed default already refcounts; this is the manual-side analog |
| `std/atomic.lang` | `Atomic*` (class) | Runtime | atomic int/ptr load/store/CAS/fetch-add | Backs `Arc`, managed atomic refcounts, counters, work queue |
| (runtime mode) | debug allocator | Runtime | track allocations, report leaks + double-free at exit | Env-gated (e.g. `GLANG_DEBUG_ALLOC=1`); ASan-lite, for `unmanaged` |

## Concurrency + I/O primitives (hybrid model)

| Module | Namespace / Type | Kind | Exposes | Notes |
|---|---|---|---|---|
| `std/thread.lang` | `Thread` (class) + `namespace thread` | Runtime | spawn, join, thread-local storage | pthreads |
| `std/sync.lang` | `Mutex`/`RwLock`/`CondVar` (class) | Runtime | lock/unlock/wait/signal | Guards shared state |
| `std/channel.lang` | `Channel<T>` (class) | Runtime/Pure | MPSC queue, send/recv | Distributes connections to loops |
| `std/poll.lang` | `Poller` (class) | Runtime | register fd, wait for readiness, timers | epoll (Linux) / kqueue (macOS) abstraction |
| `std/net.lang` | `TcpListener`/`TcpSocket`/`UdpSocket` + `namespace net` | Runtime | socket/bind/listen/accept/connect/send/recv/close, **non-blocking mode**, DNS | Built on `bytes` |
| `std/time.lang` | `namespace time` | Runtime | `nowNanos` (monotonic), `wallClock`, `sleepMs`, timers | Timeouts |

## Async language feature (critical path — design first)

- `async`/`await` (or coroutine library) per the options above. Design spike before
  committing: prototype the simplest viable (stackful coroutines) and measure ergonomics
  vs a compiler state-machine transform. Must work in interpreter + compiler.

---

# Phase 1 — Async runtime (the event loop)

| Module | Namespace / Type | Kind | Exposes | Depends on |
|---|---|---|---|---|
| `std/async.lang` | `Task<T>` / `Future<T>` + `namespace async` | Runtime/Pure | spawn, await, join, select/race, timeouts | poll, time, channel, async feature |
| `std/runtime.lang` | `EventLoop` (class) + `namespace rt` | Pure (on poll) | run loop, schedule, async TCP read/write/accept | poll, async |
| (server core) | pool-of-loops scheduler | Pure | N threads each running an `EventLoop`; accept-distribution | thread, channel, runtime |

---

# Phase 2 — Text / data foundation (Pure; build in parallel with Phase 0–1)

| Module | Namespace / Type | Kind | Exposes | Depends on |
|---|---|---|---|---|
| `std/result.lang` | `Result<T,E>` + `namespace result` | Pure | ok/err, map, unwrapOr | option |
| `std/fmt.lang` | `namespace fmt` | Pure | `format`, padding, hex/bin, width/precision | strings, stringbuilder |
| `std/convert.lang` | `namespace convert` | Pure | safe `tryParse*` → Option/Result | result |
| `std/sort.lang` | `namespace sort` | Pure | generic sort/stableSort/binarySearch | list |
| `std/json.lang` | `Json` (union) + `namespace json` | Pure | parse → Result, stringify | result, map, list, fmt |
| `std/encoding.lang` | `namespace encoding` | Pure | base64, hex, URL percent-encode/decode | bytes |
| `std/hash.lang` | `namespace hash` | Pure | FNV-1a, CRC32 | bytes |
| `std/url.lang` | `Url` (class) + `namespace url` | Pure | parse/build URL, query string | strings, encoding |
| `std/path.lang` | `namespace path` | Pure | join/split/normalize/ext/basename | strings |

---

# Phase 3 — HTTP + web server (Goal 1)

| Module | Namespace / Type | Kind | Exposes | Depends on |
|---|---|---|---|---|
| `std/http.lang` | `Request`/`Response`/`Headers` + `namespace http` | Pure | HTTP/1.1 parse + serialize, chunked, keep-alive, status codes | bytes, net, fmt, url |
| `std/mime.lang` | `namespace mime` | Pure | content-type lookup by extension | path |
| `std/server.lang` | `HttpServer` (class) | Pure | bind + serve over the pool-of-loops runtime; raw handler `async fn(Request)->Response` | http, runtime, async |

Milestone: `HttpServer` serving "hello world" and static files concurrently across cores.

---

# Phase 4 — Backend framework, FastAPI-style (Goal 2)

| Module | Namespace / Type | Kind | Exposes | Depends on |
|---|---|---|---|---|
| `std/web/router.lang` | `Router` (class) + `namespace web` | Pure | path params (`/users/{id}`), method dispatch, groups | http |
| `std/web/context.lang` | `Ctx`/`Request`/`Response` wrappers | Pure | typed accessors, cookies, query, body | http, json |
| `std/web/middleware.lang` | `namespace web` | Pure | composable middleware chain (logging, CORS, auth) | router |
| `std/web/inject.lang` | `namespace web` | Pure | dependency injection (handler params resolved from providers) | router |
| `std/web/model.lang` | `namespace web` | Pure | typed body → class via `json`, **validation**, error → 422 | json, result |
| `std/web/openapi.lang` | `namespace web` | Pure | generate OpenAPI/JSON-schema from typed handlers | model, router |
| `std/web/app.lang` | `App` (class) | Pure | the FastAPI-like entrypoint tying it together | all of the above + server |

Open question for design phase: how handlers declare typed inputs/outputs without
reflection (Glang has no runtime reflection) — likely codegen or explicit schema registration.

Milestone: define a typed model + route, POST JSON, get validation + auto JSON response +
generated OpenAPI.

---

# Phase 5 — Fullstack: Glang→JS (Goal 3)

| Workstream | Kind | Exposes | Notes |
|---|---|---|---|
| `compiler/jsemit.lang` | Compiler backend | Glang AST → JavaScript | Third target after C emitter; reuses loader/analyser/mono |
| JS runtime | Runtime (JS) | port of `glang_runtime.c` semantics | string/print/exception/collections in JS |
| memory model mapping | Design | `alloc`→array, `free`→no-op, pointer/`Span` semantics on GC | Decide early |
| `std/dom.lang` | Pure (JS target) | DOM + `fetch` bindings | Browser-only module |
| `std/web/shared.lang` | Pure | models/validation usable on **both** server and client | The fullstack payoff: define once, validate both ends |
| client framework | Pure (JS target) | components / SSR hydration story | Scope after emitter works |

Milestone: one Glang model type validated on the server (C) and in the browser (JS) from
the same source.

---

# Later / deferred

`std/process.lang`, `std/fs.lang` (dir ops), `std/os.lang` (env) — Runtime, useful but not
critical-path. `std/random.lang` (pure PRNG + runtime seed). `std/log.lang`, `std/test.lang`
(Pure). `std/regex.lang`, `std/toml.lang`, `std/yaml.lang`, `std/xml.lang`,
`std/crypto.lang` (Runtime: TLS/SHA — note: real HTTPS needs TLS, a significant Runtime
dependency to schedule before public deployment). `namespace gui` — out of scope.

---

# Build order (dependency-sane)

0. **Phase 0.0 memory model** (gates everything): design spike (settle `managed`-scope block
   form) → `managed` keyword + `@` handle type + analyser flag → type rules (`*`/`@` don't
   mix; no bare `@` in unmanaged classes) → `Root<T>` middle man + managed-scope `enter()` →
   refcount write barriers + shadow-stack roots in `emit.lang` (managed/`@` refs only) →
   field maps → cycle collector → atomic refcounts → interpreter parity. No stdlib migration.
1. **Phase 0 memory safety**: `bytes` → `slice` → `arena` → `atomic`/`rc` → debug allocator.
2. **Async design spike** (pick coroutine vs state-machine) — gate before Phase 1.
3. **Phase 0 I/O**: `thread`/`sync`/`channel` → `poll` → `net` → `time`.
4. **Phase 1**: `async` → `runtime` (event loop) → pool-of-loops scheduler.
5. **Phase 2** (parallel, no runtime cost): `result`/`fmt`/`sort`/`json`/`encoding`/`url`.
6. **Phase 3**: `http` → `mime` → `server`. (Goal 1 milestone)
7. **Phase 4**: `router` → `context`/`middleware`/`inject` → `model`/`openapi` → `app`.
   (Goal 2 milestone)
8. **Phase 5**: `jsemit` + JS runtime → `shared` models → `dom` → client framework.
   (Goal 3 milestone)
9. **TLS** before any public deployment.
