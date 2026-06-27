#!/usr/bin/env bash
set -euo pipefail

# build-server.sh — compile the Glang language server into a standalone binary
# and place it at vscode-glang/server/glang-lsp, where extension.js looks for it.
#
# The server is compiled from toolchain/lsp/server.lang via the self-hosted
# glangc and linked with the C runtime. The resulting binary embeds the whole
# compiler front-end and needs no source files at runtime.

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TOOLCHAIN="$HERE/../toolchain"

if [[ ! -d "$TOOLCHAIN" ]]; then
  echo "error: toolchain not found at $TOOLCHAIN" >&2
  exit 1
fi

cd "$TOOLCHAIN"

if [[ ! -x ./glangc ]]; then
  echo "Building glangc from seed ..."
  ./build.sh
fi

mkdir -p "$HERE/server"

echo "Compiling lsp/server.lang -> C ..."
./glangc lsp/server.lang lsp/server.c

echo "Linking glang-lsp ..."
cc -O1 -w lsp/server.c runtime/glang_runtime.c -o "$HERE/server/glang-lsp"

echo "Built $HERE/server/glang-lsp"
