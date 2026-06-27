#!/usr/bin/env bash
# Build the Glang web server. Run from anywhere; resolves paths relative to the
# repo so std/... imports load (glangc's loader defaults to ./stdlib).
set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo="$(cd "$here/../.." && pwd)"
toolchain="$repo/Toolchain"

# Ensure glangc exists.
if [[ ! -x "$toolchain/glangc" ]]; then
  echo "building glangc..."
  "$toolchain/build.sh"
fi

cd "$toolchain"
./glangc "$here/main.lang" "$here/web-server.c"
gcc -O2 -w "$here/web-server.c" runtime/glang_runtime.c -o "$here/web-server"
echo "built: $here/web-server"
