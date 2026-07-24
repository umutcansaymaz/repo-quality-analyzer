"""REST API package for repo-analyzer (FastAPI)."""

from __future__ import annotations

from repo_analyzer.api.app import app, run_api

__all__ = ["app", "run_api"]
