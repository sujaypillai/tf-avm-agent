# syntax=docker/dockerfile:1.7
# -----------------------------------------------------------------------------
# tf-avm-agent MCP server image
#
# Multi-stage:
#   1. "builder" installs deps into a throwaway virtualenv so we get clean
#      layer caching and don't ship pip/build tooling.
#   2. "runtime" copies the venv + source into a slim base, runs as non-root.
#
# Build:   docker build -t tf-avm-mcp:dev .
# Run:     docker run --rm -p 8000:8000 \
#            -e AZURE_OPENAI_ENDPOINT=... -e AZURE_OPENAI_API_KEY=... \
#            tf-avm-mcp:dev
# Probe:   curl -fsS http://localhost:8000/health
# -----------------------------------------------------------------------------

ARG PYTHON_VERSION=3.12

# ---------------------------------------------------------------------------- #
# Stage 1: build wheel + install into an isolated venv
# ---------------------------------------------------------------------------- #
FROM python:${PYTHON_VERSION}-slim AS builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1

# build-essential is only needed if a transitive dep has no wheel for slim;
# keeping it out of the runtime image is the whole point of multi-stage.
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

# Copy dependency manifests first so the install layer caches until
# pyproject.toml actually changes.
COPY pyproject.toml README.md ./
COPY src/ ./src/
COPY server/ ./server/

# Create a venv at a fixed path and install the package + server extras.
# `[server]` must be defined in pyproject.toml (see rollout notes).
RUN python -m venv /opt/venv \
    && /opt/venv/bin/pip install --upgrade pip \
    && /opt/venv/bin/pip install ".[api,agent]"

# ---------------------------------------------------------------------------- #
# Stage 2: slim runtime
# ---------------------------------------------------------------------------- #
FROM python:${PYTHON_VERSION}-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    PORT=8000

# curl: used by HEALTHCHECK and ad-hoc debugging.
# tini:  PID 1 that reaps zombies and forwards signals properly (uvicorn
#        reloads, SIGTERM on revision swap, etc.).
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl tini ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --system --gid 10001 app \
    && useradd  --system --uid 10001 --gid app --home-dir /app --shell /usr/sbin/nologin app

# Bring over the already-populated venv + source tree.
COPY --from=builder /opt/venv /opt/venv
COPY --from=builder /build    /app

WORKDIR /app
USER app

EXPOSE 8000

# ACA's default probes are GET on the target port. /mcp is POST-only, so this
# MUST hit /health or the container restart-loops.
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -fsS "http://127.0.0.1:${PORT}/health" || exit 1

ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["python", "-m", "server.main"]