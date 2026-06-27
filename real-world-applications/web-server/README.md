# Glang web server + reverse proxy

A comprehensive, single-threaded, **non-blocking** HTTP/1.1 server with an
integrated **streaming reverse proxy** — written entirely in Glang, compiled to C.

One thread runs one `poll()` loop and serves many concurrent connections. Every
socket is non-blocking, so a slow client never stalls the others.

## What it demonstrates

- **Event-loop concurrency** — `poll()`-based readiness multiplexing (`std/net.lang`'s `Poller`), per-connection inbound/outbound buffers, no threads.
- **Full HTTP/1.1 request parsing & response building** — request line, headers, `Content-Length` bodies, pipelined requests, keep-alive (`std/http.lang`).
- **Routing** — exact and prefix routes to handler functions (`std/router.lang`).
- **Safe HTML** — output escaping so untrusted query input can't inject markup (`std/html.lang`).
- **Reverse proxy** — path-prefix mounts open a non-blocking upstream connection, rewrite hop-by-hop headers + `Host` + `Via`, and **stream** the response back through the same loop (`std/server.lang`).
- **Robustness** — `SIGPIPE` ignored (a hung-up peer returns an error instead of crashing the process), oversized request → `413`, failed upstream → `502`.

## Routes

| Route        | Description                                    |
|--------------|------------------------------------------------|
| `GET /`      | HTML home page                                 |
| `GET /health`| liveness probe (`ok`)                          |
| `GET /echo`  | reflects `?msg=...`, HTML-escaped (XSS-safe)   |
| `GET /time`  | server wall-clock millis                       |
| `ANY /api/*` | reverse-proxied to the configured upstream     |

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

```bash
./web-server [listenPort] [upstreamHost] [upstreamPort]
# defaults:  8080         127.0.0.1      9000
```

Example — proxy `/api/*` to a backend on `:9000`:

```bash
./web-server 8080 127.0.0.1 9000 &
curl http://127.0.0.1:8080/                 # home page
curl http://127.0.0.1:8080/echo?msg='<b>'   # -> &lt;b&gt;
curl http://127.0.0.1:8080/api/users/42     # -> proxied to 127.0.0.1:9000
```

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
