# syntax=docker/dockerfile:1.7
# Multi-stage Dockerfile for repo-analyzer
# Stage 1: builder
FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency manifests first for better layer caching
COPY pyproject.toml requirements.txt ./

# Install dependencies into a target directory
RUN pip install --user --no-cache-dir -r requirements.txt

# Stage 2: runtime
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH=/root/.local/bin:$PATH

# Runtime system dependencies (git is required by the VCS adapter)
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /root/.local /root/.local

# Copy application source
COPY src/ /app/src/
COPY pyproject.toml README.md ./

# Install the application itself (no deps, already installed)
RUN pip install --no-deps -e .

# Non-root user for safety
RUN useradd --create-home --shell /bin/bash analyzer
USER analyzer
WORKDIR /home/analyzer

ENTRYPOINT ["repo-analyzer"]
CMD ["--help"]
