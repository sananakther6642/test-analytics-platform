# ADR 0004: Pin external image versions, not floating tags

## Status
Accepted

## Context
`docker-compose.yml` originally used `postgres:16-alpine` — a floating tag
that Docker Hub can (and does) repoint to a newly published image at any
time. Bringing up Postgres for the first time in this project failed with
`exec /usr/local/bin/docker-entrypoint.sh: exec format error`.

Diagnosing this took considerable effort and ruled out several wrong
hypotheses in order: CPU architecture mismatch (image was correctly arm64
on an arm64 host), a corrupted local volume (removing it and starting fresh
didn't help), and Docker Desktop's own VM/storage state being corrupted by
an earlier disk-full incident (confirmed unrelated — `hello-world` and
other images ran perfectly). The eventual root cause, found by inspecting
the raw bytes of the entrypoint script inside the running container: the
file was **zero bytes**. Not corrupted content — genuinely empty, at a path
where a real shell script should exist.

A full local cache eviction (`docker builder prune -af`,
`docker system prune -af`, removing the image, re-pulling from an empty
image store) reproduced the exact same empty file, ruling out local
corruption entirely. Testing sibling images narrowed it down conclusively:
`alpine:3.20`, `nginx:1.27-alpine`, `postgres:16` (Debian), and
`postgres:16.4-alpine` (a specific pinned patch version) all worked
correctly. Only the floating `postgres:16-alpine` tag, at this point in
time, resolved to an image with a broken entrypoint script.

## Decision
Pin every external (non-project) Docker image in `docker-compose.yml` and
any Kubernetes manifests/Helm values to an exact version, never a floating
tag like `16-alpine`, `latest`, or a bare major version.

`postgres:16-alpine` → `postgres:16.4-alpine`.

## Alternatives considered
- **Keep the floating tag and just retry/wait for upstream to fix it.**
  Works eventually, but means this project's reproducibility depends on
  whatever Docker Hub happens to serve at `:16-alpine` on any given day —
  exactly the failure mode version pinning exists to prevent, and this
  incident is direct, first-hand evidence of that risk materializing, not
  a hypothetical.
- **Pin only project-built images (api, web) and leave third-party images
  floating**, on the reasoning that project images are what actually change
  during development. Rejected by this incident specifically: the image
  that broke was the *external* one, not anything we built. The
  reproducibility argument applies at least as strongly to dependencies
  outside our control as to our own code — arguably more so, since we can't
  fix an upstream bug in someone else's published image, only avoid
  depending on the exact moment it's broken.

## Consequences
- Every external image reference going forward (Postgres now; ingress-nginx,
  cert-manager, kube-prometheus-stack, Argo CD in later phases) gets an
  exact version pin, with the version recorded in the same file as the
  pin, not just implied by "whatever was current when this was written."
- Upgrading an external image becomes a deliberate, reviewed action (bump
  the pin, test it) rather than something that happens silently on a
  rebuild — the same trade-off already accepted for `.tool-versions` and
  `uv.lock`, now extended to container images.
- This incident and its resolution are recorded here specifically so the
  reasoning ("we pin because of X, and X actually happened") survives as
  more than a stylistic preference — it's backed by a real, reproducible
  failure this project hit.
