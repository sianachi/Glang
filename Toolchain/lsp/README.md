# GLang Language Server

A Language Server Protocol (LSP) implementation for GLang, written in GLang
itself. It reuses the self-hosted compiler front-end (`../compiler/`) for
analysis and `../stdlib/json.lang` for the wire format.

## Features

| Capability | Notes |
|---|---|
| **Diagnostics** | Errors as you type (lex / parse / type errors). Positioned on the offending token; type errors without a compiler position are anchored on the identifier named in the message. |
| **Hover** | Signature for functions, and structure for classes / enums / unions, from the symbol table. |
| **Completion** | User symbols (functions, classes, enums, unions, interfaces) + keywords + builtins. |
| **Go-to-definition** | Jumps to the declaration of a function / class / enum / union / interface. |
| **Document symbols** | Outline of top-level declarations. |

Transports: **stdio** (default) and **TCP** (`--tcp <port>`).

## Build & run

```bash
cd toolchain
./glangc lsp/server.lang lsp/server.c
cc -O1 -w lsp/server.c runtime/glang_runtime.c -o glang-lsp

./glang-lsp --stdio        # for editors (VS Code, etc.)
./glang-lsp --tcp 6789     # listen on a TCP port
```

The compiled binary is self-contained — the whole front-end is compiled into it
and it does no file I/O at runtime, so it can be moved/copied anywhere.

## Layout

| File | Role |
|---|---|
| `server.lang` | `main`, transport selection, JSON-RPC dispatch, document store, lifecycle. |
| `jsonrpc.lang` | `Content-Length` framing over stdio / TCP (`Transport`). |
| `analysis.lang` | Runs the front-end over a document → diagnostics + tokens + `GlobalEnv`. |
| `features.lang` | hover / completion / definition / documentSymbol. |
| `diag_dump.lang`, `json_dump.lang` | Differential-test drivers (read stdin, print result). |

## Editor integration

- **VS Code**: see `../../vscode-glang/` — run `npm run build-server` (or the
  repo-root `install-vscode-ext.sh`) and the extension launches this binary over
  stdio.
- **Learn platform** (browser): a native binary can't run in the browser, so the
  React app surfaces lighter, parse-time diagnostics from its own in-browser
  interpreter (`learn/src/lib/glang/`). For real-compiler diagnostics, run
  `glang-lsp --tcp` behind a WebSocket bridge.

## Known limitations

- **One diagnostic per change.** The compiler is fail-fast, so analysis reports
  the first error only. Fix it and the next surfaces.
- **Positions come from tokens, not the AST** (AST nodes carry no source spans).
  Type-error squiggles are anchored on the identifier named in the message;
  go-to-definition and symbols are resolved by scanning the token stream, so
  definition is single-file and finds the first textual declaration.
- **No cross-file / workspace features.** Each open document is analyzed on its
  own (no import resolution at the server level).

## Implementation note (native exceptions)

The native runtime implements `try`/`catch` with `setjmp`/`longjmp`, which
leaves non-volatile locals indeterminate after a `longjmp`. Reading a `try`-local
(or a heap field through a local pointer) inside a `catch` is therefore reliable
under the interpreter but **not** under the compiled binary. The analyzer keeps
all surviving state in a heap result, the catch does only writes, and position
recovery runs after the `try`/`catch` — see `analyzeDoc` in `analysis.lang`.
