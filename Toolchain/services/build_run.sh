#!/usr/bin/env bash
set -euo pipefail

# build_run.sh — compile the GLang run service to a native binary.
# Produces toolchain/services/run_server. Run from anywhere.

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TOOLCHAIN="$(cd "$HERE/.." && pwd)"

cd "$TOOLCHAIN"
if [[ ! -x ./glangc ]]; then
  echo "Building glangc from seed ..."
  ./build.sh
fi

echo "Compiling services/run_server.lang -> C ..."
./glangc services/run_server.lang services/run_server.c

echo "Linking run_server ..."
cc -O2 -w services/run_server.c runtime/glang_runtime.c -o services/run_server

echo "Built $TOOLCHAIN/services/run_server"
echo "Run: ./services/run_server --port 8081 --stdlib stdlib --tmp /tmp --max-steps 5000000"
