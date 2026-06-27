#!/usr/bin/env bash
set -euo pipefail

# prebuild.sh — generate the portable C for the GLang services on the HOST, so
# the Docker image only needs to run gcc (lightweight) rather than glangc (which
# holds the whole compiler+interpreter in memory and can OOM a small build VM).
# The emitted C is platform-neutral (it compiles on macOS and Linux alike).
#
# Run this before `docker compose build`:
#   bash deploy/prebuild.sh && docker compose up --build

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
TOOLCHAIN="$ROOT/toolchain"
GEN="$HERE/gen"

cd "$TOOLCHAIN"
if [[ ! -x ./glangc ]]; then
  echo "Building glangc from seed ..."
  ./build.sh
fi

mkdir -p "$GEN"
echo "Generating run_server.c ..."
./glangc services/run_server.lang "$GEN/run_server.c"
echo "Generating lsp_ws_server.c ..."
./glangc services/lsp_ws_server.lang "$GEN/lsp_ws_server.c"

cp runtime/glang_runtime.c runtime/glang_runtime.h "$GEN/"
echo "Prebuilt C is in $GEN"
