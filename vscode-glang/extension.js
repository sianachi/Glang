// extension.js — VS Code client for the Glang Language Server.
//
// Launches the compiled `glang-lsp` binary and wires it to VS Code via the LSP.
// The binary embeds the whole compiler front-end, so only the path to the binary
// itself is required here. It does read imported modules (incl. the stdlib) from
// disk to resolve `import` statements, locating the stdlib by walking up from the
// edited file's own path — so no working directory or toolchain path needs to be
// configured.
//
// Transports:
//   stdio (default) — launch the binary with --stdio, talk over its pipes.
//   tcp             — spawn it with --tcp <port>, then connect a socket. Useful
//                     for sharing one server with other clients (e.g. the learn
//                     platform's WebSocket bridge).

const path = require("path");
const net = require("net");
const cp = require("child_process");
const { workspace, window } = require("vscode");
const { LanguageClient, TransportKind } = require("vscode-languageclient/node");

let client;

function resolveServerPath(context) {
  const configured = workspace.getConfiguration("glang.lsp").get("serverPath");
  if (configured && configured.length > 0) {
    return configured;
  }
  return context.asAbsolutePath(path.join("server", "glang-lsp"));
}

function activate(context) {
  const cfg = workspace.getConfiguration("glang.lsp");
  if (cfg.get("enable") === false) {
    return;
  }

  const serverPath = resolveServerPath(context);
  const transport = cfg.get("transport") || "stdio";

  let serverOptions;
  if (transport === "tcp") {
    const port = cfg.get("port") || 6789;
    serverOptions = () =>
      new Promise((resolve, reject) => {
        const child = cp.spawn(serverPath, ["--tcp", String(port)]);
        child.stderr.on("data", (d) =>
          console.error("[glang-lsp]", d.toString().trimEnd())
        );
        child.on("error", reject);
        // Give the server a moment to bind, then connect.
        const tryConnect = (attempt) => {
          const socket = net.connect(port, "127.0.0.1");
          socket.once("connect", () =>
            resolve({ reader: socket, writer: socket })
          );
          socket.once("error", (err) => {
            if (attempt < 20) {
              setTimeout(() => tryConnect(attempt + 1), 100);
            } else {
              reject(err);
            }
          });
        };
        tryConnect(0);
      });
  } else {
    const run = {
      command: serverPath,
      args: ["--stdio"],
      transport: TransportKind.stdio,
    };
    serverOptions = { run, debug: run };
  }

  const clientOptions = {
    documentSelector: [{ scheme: "file", language: "glang" }],
    synchronize: { configurationSection: "glang" },
  };

  client = new LanguageClient(
    "glang",
    "GLang Language Server",
    serverOptions,
    clientOptions
  );

  client.start().catch((err) => {
    window.showErrorMessage(
      "GLang language server failed to start: " +
        (err && err.message ? err.message : String(err)) +
        ". Build it with `npm run build-server` in the extension folder, or set glang.lsp.serverPath."
    );
  });
}

function deactivate() {
  if (client) {
    return client.stop();
  }
  return undefined;
}

module.exports = { activate, deactivate };
