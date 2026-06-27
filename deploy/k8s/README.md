# Kubernetes (k3s) deployment

Deploys the three services (run, lsp, frontend) to a Kubernetes cluster with
Traefik ingress. Cluster- and account-specific details stay **out of git**: the
committed `base/` uses placeholders; real values live in a gitignored local
overlay and `.local.env`.

```
deploy/k8s/
├── base/                       # committed manifests (placeholders only)
│   ├── namespace / run / lsp / frontend / ingress / networkpolicy
│   ├── networkpolicy-strict-ingress.yaml   # optional, applied manually
│   └── kustomization.yaml
├── overlay-local.example/      # committed template for the local overlay
├── overlay-local/              # GITIGNORED — your real registry + hostname
├── .local.env                  # GITIGNORED — REGISTRY / TAG for build-push.sh
├── build-push.sh               # cross-build (amd64) + push images
└── .gitignore
```

## 1. Build & push images (amd64)

The cluster node is amd64; a local arm64 build won't run there, so images are
cross-built for `linux/amd64`. The service C and the frontend bundle are produced
natively on the host first, so only `gcc` runs under emulation (fast).

```bash
# one-time: allow pushing to GHCR
gh auth refresh -h github.com -s write:packages
gh auth token | docker login ghcr.io -u <your-gh-user> --password-stdin

# set your registry in the gitignored env file
printf 'REGISTRY=ghcr.io/<your-gh-user>\nTAG=v1\n' > deploy/k8s/.local.env

bash deploy/k8s/build-push.sh
```

## 2. Configure the local overlay

```bash
cp -r deploy/k8s/overlay-local.example deploy/k8s/overlay-local
# edit deploy/k8s/overlay-local/kustomization.yaml:
#   - images: -> ghcr.io/<your-gh-user>/glang-* : <TAG>
#   - Ingress host -> your hostname
```

Point that hostname's DNS A record at the cluster node, then (TLS optional — add
a `tls:` block + cert-manager/Traefik ACME once it resolves).

## 3. Pull secret (only if the GHCR packages are private)

Either make the three packages public on GitHub, or create a pull secret (the
Deployments already reference `imagePullSecrets: [ghcr]`):

```bash
kubectl create namespace glang
kubectl create secret docker-registry ghcr -n glang \
  --docker-server=ghcr.io --docker-username=<your-gh-user> \
  --docker-password="$(gh auth token)"
```

## 4. Deploy

```bash
kubectl apply -k deploy/k8s/overlay-local
kubectl get pods -n glang -w
```

## 5. Verify

```bash
HOST=<your-host>
curl -s -o /dev/null -w '%{http_code}\n' http://$HOST/                      # 200 (SPA)
curl -s -XPOST http://$HOST/api/run -H 'Content-Type: application/json' \
  --data-binary '{"source":"int main(){ print(6*7); return 0; }"}'          # {"ok":true,...["42"]}
# LSP WebSocket: open the app in a browser and edit code — squiggles/hover are live.
```

## Hardening

The two GLang services run non-root, read-only rootfs (run gets a memory-backed
`emptyDir` `/tmp`), all caps dropped, seccomp RuntimeDefault, resource-capped,
and **egress-locked to DNS only** (NetworkPolicy) so untrusted code can't reach
the network. Stricter ingress (only frontend → run/lsp) is in
`base/networkpolicy-strict-ingress.yaml`; apply it after confirming pods stay
Ready (kubelet probes can be denied by ingress rules on some CNIs).

## Notes

- The kubeconfig and any cluster/host/registry specifics are never committed —
  keep them in `~/.kube/config`, `.local.env`, and `overlay-local/`.
- Memory caveat carries over from compose: the interpreter leaks per step, so the
  run service uses `--max-steps 1000000` under a 512Mi limit. A subprocess-per-
  request executor is the durable fix.
