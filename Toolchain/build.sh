#!/usr/bin/env bash
# Bootstrap the self-hosted Glang compiler from the committed glangc.c seed.
# Produces ./glangc — after this, no Python is needed to compile .lang files.
set -euo pipefail
cd "$(dirname "$0")"
gcc -O1 -w glangc.c runtime/glang_runtime.c -o glangc
echo "built ./glangc  —  use it as:  ./glangc <file.lang> <out.c>"
