# Glang web server + reverse proxy + file store

A comprehensive, single-threaded, **non-blocking** HTTP/1.1 server with an
integrated **streaming reverse proxy** and a binary-safe **file store** (upload /
download) — written entirely in Glang, compiled to C.

One thread runs one `poll()` loop and serves many concurrent connections. Every
socket is non-blocking, so a slow client never stalls the others.

## What it demonstrates

- **Event-loop concurrency** — `poll()`-based readiness multiplexing (`std/net.lang`'s `Poller`), per-connection inbound/outbound buffers, no threads.
- **Full HTTP/1.1 request parsing & response building** — request line, headers, `Content-Length` bodies, pipelined requests, keep-alive (`std/http.lang`).
- **Routing** — exact and prefix routes to handler functions (`std/router.lang`).
- **Static / file serving** — binary-safe download and upload of any file type, MIME by extension, path-traversal protection, optional SPA fallback (`std/static.lang`, served via `std/server.lang` mounts). Uploaded bytes round-trip intact (incl. `\0`/`0xFF`), unlike string-based file I/O.
- **CORS** — configurable allowed origin with automatic `OPTIONS` preflight handling, so a browser/SPA on another origin can upload and fetch.
- **Safe HTML** — output escaping so untrusted query input can't inject markup (`std/html.lang`); the home-page file list builds DOM via `textContent` (no `innerHTML` injection from file names).
- **Reverse proxy** — path-prefix mounts open a non-blocking upstream connection, rewrite hop-by-hop headers + `Host` + `Via`, and **stream** the response back through the same loop (`std/server.lang`).
- **Robustness** — `SIGPIPE` ignored (a hung-up peer returns an error instead of crashing the process), oversized request → `413`, failed upstream → `502`, path traversal → `403`.

## Routes

| Route                | Description                                    |
|----------------------|------------------------------------------------|
| `GET /`              | HTML home page with a file uploader            |
| `GET /health`        | liveness probe (`ok`)                          |
| `GET /echo`          | reflects `?msg=...`, HTML-escaped (XSS-safe)   |
| `GET /time`          | server wall-clock millis                       |
| `GET /files`         | JSON list of uploaded files                    |
| `PUT /files/<name>`  | upload a file (binary-safe)                    |
| `GET /files/<name>`  | download a file (binary-safe, MIME by ext)     |
| `ANY /api/*`         | reverse-proxied to the configured upstream     |

## Build

The server uses real sockets, so it goes through the native compiler. Run from
the `Toolchain/` directory so `std/...` imports resolve:

```bash
cd Toolchain
./glangc ../real-world-applications/web-server/main.lang ws.c
gcc -O2 ws.c runtime/glang_runtime.c -o web-server
```

(Or use the helper: `real-world-applications/web-server/build.sh`.)

## Run

Run from this directory so the default `./uploads` store stays inside the app
folder (the `uploads/` dir ships with the repo via a `.gitkeep`):

```bash
cd real-world-applications/web-server
./web-server [listenPort] [upstreamHost] [upstreamPort] [uploadsDir]
# defaults:  8080         127.0.0.1      9000           ./uploads
```

Example — file store + proxy `/api/*` to a backend on `:9000`:

```bash
mkdir -p uploads
./web-server 8080 127.0.0.1 9000 uploads &
curl http://127.0.0.1:8080/                          # home page + uploader
curl -T photo.png http://127.0.0.1:8080/files/photo.png   # upload (binary-safe)
curl http://127.0.0.1:8080/files                     # -> ["photo.png"]
curl http://127.0.0.1:8080/files/photo.png -o out.png # download, byte-identical
curl http://127.0.0.1:8080/echo?msg='<b>'            # -> &lt;b&gt;
curl http://127.0.0.1:8080/api/users/42              # -> proxied to 127.0.0.1:9000
```

Open `http://localhost:8080/` in a browser to upload via the form and see the
file list (built with `textContent`, so file names can't inject HTML).

## Architecture

```
            ┌──────────────────────── HttpServer (one poll loop) ─────────────────────┐
 client ───▶│ accept ─▶ Conn{inbuf,outbuf} ─▶ tryParseRequest ─┬─▶ Router ─▶ Response │
            │                                                   │                      │
            │                                                   └─▶ proxy mount ─▶ upstream Conn
            │                                                          (non-blocking connect,    │
            │                                                           stream response back)     │
            └──────────────────────────────────────────────────────────────────────────────────┘
```

Each connection is a state machine driven only by poll readiness. Local routes
produce a response synchronously; proxied requests pair the client connection
with an upstream connection and shuttle bytes between them — all on the one
thread.

## Limitations (deliberate scope)

- HTTP/1.1 only; no TLS (terminate TLS at a front proxy and run this plaintext).
- The reverse proxy buffers each request fully (bounded by `serverMaxRequestBytes`, 1 MiB) and forces `Connection: close` upstream; it does not pool upstream connections or tunnel WebSocket upgrades.
- Chunked **request** bodies are not decoded (responses stream fine regardless).
- File uploads are buffered in memory (bounded by the same 1 MiB request cap) and written synchronously; the uploads directory must already exist. CORS headers apply to locally-served responses (static, file store, routes); proxied responses pass the upstream's own headers through.
