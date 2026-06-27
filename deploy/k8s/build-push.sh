#!/usr/bin/env bash
set -euo pipefail

# build-push.sh — cross-build the three images for linux/amd64 and push them to a
# registry. Reads REGISTRY/TAG from deploy/k8s/.local.env (gitignored) so the
# registry never lands in git.
#
# Prereqs (one-time):
#   gh auth refresh -h github.com -s write:packages      # add packages scope
#   gh auth token | docker login ghcr.io -u <user> --password-stdin
#
# Then:  bash deploy/k8s/build-push.sh

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/../.." && pwd)"

# shellcheck disable=SC1091
source "$HERE/.local.env"
: "${REGISTRY:?set REGISTRY in deploy/k8s/.local.env}"
: "${TAG:=v1}"

cd "$ROOT"

# 1. Generate the services' portable C on the host (native glangc; the image only
#    runs gcc, so it cross-compiles cleanly under emulation).
if [[ ! -f deploy/gen/run_server.c || ! -f deploy/gen/lsp_ws_server.c ]]; then
  echo "==> Generating service C (deploy/prebuild.sh)"
  bash deploy/prebuild.sh
fi

# 2. Build the frontend bundle on the host (native; avoids npm under emulation).
if [[ ! -f learn/dist/index.html ]]; then
  echo "==> Building frontend bundle (npm run build)"
  ( cd learn && npm install --no-fund --no-audit --loglevel=error && npm run build )
fi

# 3. Ensure a buildx builder exists.
docker buildx inspect glang-builder >/dev/null 2>&1 || docker buildx create --name glang-builder --use >/dev/null
docker buildx use glang-builder

PLATFORM=linux/amd64
echo "==> Pushing to $REGISTRY (tag $TAG) for $PLATFORM"

docker buildx build --platform "$PLATFORM" --push \
  -f deploy/Dockerfile.services --target run \
  -t "$REGISTRY/glang-run:$TAG" .

docker buildx build --platform "$PLATFORM" --push \
  -f deploy/Dockerfile.services --target lsp \
  -t "$REGISTRY/glang-lsp:$TAG" .

docker buildx build --platform "$PLATFORM" --push \
  -f deploy/Dockerfile.frontend-static \
  -t "$REGISTRY/glang-frontend:$TAG" .

echo "==> Done. Images:"
echo "    $REGISTRY/glang-run:$TAG"
echo "    $REGISTRY/glang-lsp:$TAG"
echo "    $REGISTRY/glang-frontend:$TAG"
