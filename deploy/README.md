# GLang Learn Platform — Deployment

A React frontend served by nginx, backed by two GLang services:

```
browser ──http──▶ nginx (frontend) ──/api/run──▶ run service  (GLang interpreter)
                       │
                       └──────/lsp (WebSocket)──▶ lsp service  (GLang LSP)
```

- **run service** (`toolchain/services/run_server.lang`) — `POST /api/run {source}`
  interprets the program in-process and returns `{ok, output[], stderr, exit,
  diagnostics?}`. Runs the **full language including `std/` imports**. Untrusted
  code is bounded by an interpreter step/recursion budget (`--max-steps`) and an
  app-layer guard that rejects raw filesystem builtins.
- **lsp service** (`toolchain/services/lsp_ws_server.lang`) — the GLang Language
  Server over WebSocket (RFC 6455). Live diagnostics, hover, completion,
  go-to-definition, document symbols. The browser editor is Monaco, wired to this
  service via a thin LSP-over-WebSocket client (`learn/src/lib/lsp/client.ts`).

## Run it

```bash
bash deploy/prebuild.sh        # generate the services' portable C on the host
docker compose up --build      # build + start run, lsp, frontend
open http://localhost:8080
```

`prebuild.sh` runs `glangc` on the host (it peaks ~1.8 GB compiling the whole
compiler+interpreter, which can OOM a small build VM); the emitted C is portable,
so the image only runs `gcc`.

## Local dev (without Docker)

```bash
# terminal 1 — run service
cd toolchain && bash services/build_run.sh && \
  ./services/run_server --port 8081 --stdlib stdlib --tmp /tmp --max-steps 1000000
# terminal 2 — lsp service
cd toolchain && ./glangc services/lsp_ws_server.lang services/lsp_ws_server.c && \
  cc -O1 -w services/lsp_ws_server.c runtime/glang_runtime.c -o services/lsp_ws_server && \
  ./services/lsp_ws_server --port 8082
# terminal 3 — frontend (vite proxies /api -> 8081, /lsp -> 8082)
cd learn && npm install && npm run dev
```

## Hardening (compose)

The two GLang containers run on an internal-only network (no internet egress),
as `nobody`, read-only rootfs (the run service gets a `tmpfs /tmp` for the
program it writes before interpreting), with dropped capabilities, no-new-privs,
and `mem_limit`/`cpus`/`pids_limit` caps. Only the frontend publishes a port.

## Known limitations / next steps

- **Memory under load.** The tree-walking interpreter allocates per step without
  freeing, so the step budget bounds CPU but not memory; a long-lived run process
  accumulates. `mem_limit` + a modest `--max-steps` contain it. The robust fix is
  a **subprocess-per-request executor** (each run reclaims its memory on exit) —
  the run service already isolates execution in `executeSource()` for this swap.
- **LSP concurrency.** The LSP service is a single-threaded poll loop; a
  heavyweight document briefly delays other sessions. Fine for small snippets.
- **Browser UX** (Monaco hover/completion/markers) is wired and builds, but a
  manual in-browser pass is worth doing.
