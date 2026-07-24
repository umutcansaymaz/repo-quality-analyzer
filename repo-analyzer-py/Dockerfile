# syntax=docker/dockerfile:1.7
# Multi-stage Dockerfile for repo-analyzer.
# Stage 1: builder — installs dependencies into a virtual env.
FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    UV_SYSTEM_PYTHON=1

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency manifests first for better layer caching.
COPY pyproject.toml requirements.txt ./

# Create a virtual env and install dependencies into it.
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Stage 2: runtime — minimal image with only runtime deps.
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

# Runtime system dependencies:
#   git — required by the VCS adapter for cloning.
#   libpango — required by WeasyPrint for PDF rendering.
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --shell /bin/bash analyzer

# Copy the virtual env from the builder.
COPY --from=builder /opt/venv /opt/venv

# Copy the application source.
WORKDIR /app
COPY src/ /app/src/
COPY pyproject.toml README.md ./

# Install the application itself (no deps — already in the venv).
RUN pip install --no-deps -e .

# Switch to non-root user.
USER analyzer
WORKDIR /home/analyzer

# Healthcheck: verify the CLI is operational.
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD repo-analyzer doctor || exit 1

ENTRYPOINT ["repo-analyzer"]
CMD ["--help"]
