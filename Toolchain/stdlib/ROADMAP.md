# Glang Roadmap — Minimal HTML Web Server

## Goal

**A single Glang program that serves HTML over HTTP.** A small, FastAPI-shaped
backend that renders HTML server-side. Single-threaded, one request at a time —
correctness and simplicity first; throughput later, only if ever needed.

Deliberately minimal: the only new runtime capability required is TCP sockets.
Everything else is pure Glang built on what already ships.

## Conventions

- Data/container types are top-level generic **classes**; free-function modules are
  wrapped in a **`namespace`**. Imports use `std/<name>.lang`.
- **Pure** = writable in `.lang` on existing primitives (no runtime/emitter change;
  works in all four run paths for free). **Runtime** = new C builtin + matching
  Python-interpreter and `interp.lang` support, added together.
- Python stays the test oracle; the four run paths (Python interpreter, pytest,
  native `glangc`, self-hosted `glangi`) must agree.

---

## Already shipped (foundation)

These are committed, tested, and green across all four run paths:

- **Managed memory** — `managed class` + `T@` handle type; allocate-and-sweep-at-exit
  collector. (Note: exit-sweep only — see Memory below.)
- **`std/bytes.lang`** — `Bytes`: bounds-checked byte buffer + int packing. *(socket payloads)*
- **`std/arena.lang`** — `Arena<T>`: typed bump allocator. *(per-request memory — see Memory)*
- **`std/time.lang`** + `nowNanos`/`wallMillis`/`sleepMs` builtins. *(Date headers, logging)*
- `std/slice.lang` (`Slice<T>`), `std/rc.lang` (`Rc<T>`) — available, not required by the goal.
- `GLANG_DEBUG_ALLOC` debug allocator (leak/double-free) — dev tooling.
- Restored example golden-test harness (`Toolchain/examples/run_examples.py`).

---

## Build path to the server

| Step | Module | Kind | What |
|---|---|---|---|
| **1** | `std/net.lang` | **Runtime** | Blocking TCP: `TcpListener` (bind/listen/accept) and `TcpSocket` (recv/send/close) over `Bytes`. The only new runtime piece. Interpreters: throw "unsupported in interpreter"; tests are native-gated (loopback). |
| **2** | `std/http.lang` | Pure | Parse the request line + headers from bytes; build a `Response` (status, headers, body) and serialize it. HTTP/1.1, `Connection: close` (no keep-alive needed for v1). |
| **3** | `std/html.lang` | Pure | Server-side HTML: a tiny templating/escaping helper over `StringBuilder` (e.g. `html::escape`, `html::page(title, body)`). |
| **4** | `std/router.lang` | Pure | Map `(method, path)` → handler `fn(Request)->Response`; static path params optional. |
| **5** | `std/server.lang` | Pure | `HttpServer`: loop `accept → read → http::parse → route → render → http::write → close`. Single-threaded. |

Milestone: `HttpServer` that returns a rendered HTML page for `GET /`, verified
with a loopback request (native test) and an example program.

## Memory strategy (no GC collector needed)

The shipped managed collector frees only at process exit, so a long-running
server must not pile managed objects per request. Two simple, sufficient options —
**neither needs the tracing cycle collector**:

- Per-request data is `unmanaged` and lives in an **`Arena`** that is reset after
  each response (the whole request's memory freed at once).
- `managed` is reserved for process-lifetime objects (routes, config).

---

## Cut (not needed for an HTML server)

Removed from scope. Each can return later if a concrete need appears; none is on
the path to serving HTML.

- **Hybrid concurrency / thread pool / event loop** — server is single-threaded.
  → cuts `std/thread`, `std/sync`, `std/channel`, `std/atomic`, `Arc`.
- **Async / await + coroutines** — only existed for the event-loop model.
- **Poller (epoll/kqueue)** — only for event loops.
- **Glang→JS frontend backend** — server renders HTML; no client-side Glang.
- **Tracing cycle collector** — Arena-per-request makes it unnecessary.
- **FastAPI extras** — dependency injection, middleware, OpenAPI generation, JSON
  (de)serialization. Add only if a route actually needs them.
- **TLS/HTTPS** — terminate TLS at a proxy in front for now.

## Later (only if a real need shows up)

Throughput → add a thread pool (`thread` + one `sync` mutex). Massive connection
counts → the event-loop path (`poll` + `async`). JSON APIs → `std/json`. None are
prerequisites for the goal above.
