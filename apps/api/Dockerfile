# Multi-stage: build deps in one layer, run from a slim final image.
# python:3.12-slim per the plan's D1.3 — python:3.12 alone is ~1GB with a
# large CVE surface; distroless was considered but rejected for Phase 1
# because we still want a shell to `exec` into while learning.

# Build context is the REPO ROOT (see docker-compose.yml), not apps/api/,
# specifically so this Dockerfile can also reach schemas/ below — hence
# every COPY here is prefixed with apps/api/.

FROM python:3.12-slim AS builder

RUN pip install --no-cache-dir uv==0.12.18

WORKDIR /app
COPY apps/api/pyproject.toml apps/api/uv.lock ./
COPY apps/api/src/ src/

RUN uv sync --frozen --no-dev

FROM python:3.12-slim

# Non-root user — many clusters' Pod Security Standards refuse to schedule
# a container running as root, and it's good practice regardless.
RUN useradd --uid 1000 --create-home appuser

WORKDIR /app
COPY --from=builder /app/.venv /app/.venv
COPY apps/api/src/ src/

# The TRF schema lives at the repo root (schemas/) in local dev, but the
# container has a different directory layout — config.py's path-walk
# default only holds locally. Copy the schema in and point TAD_SCHEMA_DIR
# at it explicitly rather than relying on any relative-path assumption.
COPY schemas/ /schemas/

ENV PATH="/app/.venv/bin:$PATH"
ENV TAD_SCHEMA_DIR=/schemas
USER 1000

EXPOSE 8000

CMD ["uvicorn", "tad_api.main:app", "--host", "0.0.0.0", "--port", "8000"]
