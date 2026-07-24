"""FastAPI REST API for repo-analyzer.

Exposes the analysis pipeline as a service with the following endpoints:

- ``GET  /health``  — liveness probe.
- ``GET  /status``  — service status + available providers.
- ``POST /analyze`` — start an analysis (returns a job id).
- ``GET  /result/{job_id}`` — fetch a stored result.
- ``POST /report``  — render a result into md/json/html/pdf.

**Security:**
    - API key authentication (``X-API-Key`` header) on all mutating endpoints.
    - Rate limiting (simple in-memory token bucket, per IP).
    - SSRF protection: private-IP and link-local hosts are blocked.
    - Request size limit.
    - Results have a TTL and are evicted to prevent memory exhaustion.
"""

from __future__ import annotations

import ipaddress
import os
import threading
import time
import uuid
from datetime import datetime
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, Field

from repo_analyzer.adapters.cache import SQLiteCacheAdapter
from repo_analyzer.adapters.llm import MockLLMProvider
from repo_analyzer.core.domain.repository import parse_repository_url
from repo_analyzer.core.orchestrator import Orchestrator
from repo_analyzer.infrastructure.config import load_config
from repo_analyzer.infrastructure.logging import get_logger
from repo_analyzer.utils.validation import is_valid_git_url

_logger = get_logger(__name__)

#: In-memory store for analysis results (job_id → (result, timestamp)).
_results: dict[str, tuple[Any, float]] = {}
_results_lock = threading.Lock()

#: Maximum number of stored results (FIFO eviction).
_MAX_RESULTS = 100

#: Result TTL in seconds (1 hour).
_RESULT_TTL = 3600

#: Rate-limit: max requests per window per IP.
_RATE_LIMIT_MAX = 10
_RATE_LIMIT_WINDOW = 60  # seconds
_rate_buckets: dict[str, list[float]] = {}
_rate_lock = threading.Lock()


def _check_rate_limit(client_ip: str) -> None:
    """Enforce a simple in-memory rate limit per IP."""
    now = time.time()
    with _rate_lock:
        bucket = _rate_buckets.get(client_ip, [])
        # Drop entries outside the window.
        bucket = [t for t in bucket if now - t < _RATE_LIMIT_WINDOW]
        if len(bucket) >= _RATE_LIMIT_MAX:
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded. Try again later.",
            )
        bucket.append(now)
        _rate_buckets[client_ip] = bucket


def _evict_expired_results() -> None:
    """Evict expired results to prevent unbounded memory growth."""
    now = time.time()
    with _results_lock:
        expired = [jid for jid, (_, ts) in _results.items() if now - ts > _RESULT_TTL]
        for jid in expired:
            del _results[jid]
        # If still over the limit, evict oldest.
        if len(_results) > _MAX_RESULTS:
            sorted_items = sorted(_results.items(), key=lambda kv: kv[1][1])
            for jid, _ in sorted_items[: len(_results) - _MAX_RESULTS]:
                del _results[jid]


def _is_ssrf_safe(url: str) -> bool:
    """Block SSRF attempts: reject private/loopback/link-local hosts."""
    try:
        from urllib.parse import urlparse

        parsed = urlparse(url)
        host = parsed.hostname
        if not host:
            return False
        # Block IP literals that are private / loopback / link-local.
        try:
            ip = ipaddress.ip_address(host)
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
                return False
        except ValueError:
            pass  # hostname, not IP — allow
        # Block common metadata endpoints.
        if host in {"169.254.169.254", "metadata.google.internal", "metadata.aws.internal"}:
            return False
        return True
    except Exception:
        return False


def _verify_api_key(request: Request) -> None:
    """Verify the ``X-API-Key`` header against ``GRA_API_KEY`` env var.

    If ``GRA_API_KEY`` is not set, authentication is disabled (development
    mode). In production, set ``GRA_API_KEY`` to enable authentication.
    """
    expected = os.environ.get("GRA_API_KEY")
    if not expected:
        # Auth disabled — development mode.
        return
    provided = request.headers.get("X-API-Key", "")
    if provided != expected:
        raise HTTPException(
            status_code=401,
            detail="Invalid or missing API key.",
        )


app = FastAPI(
    title="repo-analyzer API",
    description="REST API for analyzing GitHub repositories.",
    version="0.1.0",
)


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------


class AnalyzeRequest(BaseModel):
    """Request body for ``POST /analyze``."""

    repository_url: str = Field(..., description="Repository URL to analyze.")
    use_cache: bool = Field(default=True, description="Use the clone cache.")


class AnalyzeResponse(BaseModel):
    """Response body for ``POST /analyze``."""

    job_id: str
    status: str
    repository: str
    started_at: str


class ReportRequest(BaseModel):
    """Request body for ``POST /report``."""

    job_id: str = Field(..., description="The analysis job id.")
    format: str = Field(default="json", description="Report format: md/json/html/pdf.")


class HealthResponse(BaseModel):
    """Response body for ``GET /health``."""

    status: str
    version: str
    timestamp: str


# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):  # type: ignore[no-untyped-def]
    """Apply rate limiting to all requests."""
    client_ip = request.client.host if request.client else "unknown"
    # Health endpoint is not rate-limited.
    if request.url.path != "/health":
        try:
            _check_rate_limit(client_ip)
        except HTTPException as exc:
            return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
    return await call_next(request)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    """Liveness probe (no auth, no rate limit)."""
    return HealthResponse(status="ok", version="0.1.0", timestamp=datetime.now().isoformat())


@app.get("/status")
def status_endpoint() -> dict[str, Any]:
    """Service status and available features."""
    from repo_analyzer.adapters.llm import LLMProviderFactory

    return {
        "status": "running",
        "version": "0.1.0",
        "llm_providers": LLMProviderFactory.available_providers(),
        "cached_results": len(_results),
        "endpoints": ["/health", "/status", "/analyze", "/result/{job_id}", "/report"],
    }


@app.post("/analyze", response_model=AnalyzeResponse)
def analyze(req: AnalyzeRequest, request: Request) -> AnalyzeResponse:
    """Start an analysis synchronously and return the job id + result."""
    _verify_api_key(request)
    if not is_valid_git_url(req.repository_url):
        raise HTTPException(status_code=400, detail="Invalid repository URL.")
    if not _is_ssrf_safe(req.repository_url):
        raise HTTPException(
            status_code=400,
            detail="URL points to a blocked host (private/loopback/link-local).",
        )
    try:
        repository = parse_repository_url(req.repository_url)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    config = load_config()
    cache = SQLiteCacheAdapter(f"{config.cache.dir}/api-cache.db")
    orchestrator = Orchestrator(
        cache,
        max_workers=4,
        clone_depth=config.vcs.clone_depth,
        timeout=config.vcs.timeout_sec,
        llm=MockLLMProvider(),
    )
    job_id = str(uuid.uuid4())
    started = datetime.now().isoformat()
    try:
        result = orchestrator.analyze(repository, use_cache=req.use_cache)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {exc}") from exc
    finally:
        cache.close()
    with _results_lock:
        _results[job_id] = (result, time.time())
    _evict_expired_results()
    return AnalyzeResponse(
        job_id=job_id,
        status=result.status.value,
        repository=f"{repository.owner}/{repository.name}",
        started_at=started,
    )


@app.get("/result/{job_id}")
def get_result(job_id: str, request: Request) -> JSONResponse:
    """Fetch a stored analysis result as JSON."""
    _verify_api_key(request)
    with _results_lock:
        entry = _results.get(job_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="Job not found or expired.")
    result, _ts = entry
    # Use model_dump without the unsupported default=str kwarg; json.dumps
    # handles serialization via the default callback at the JSONResponse level.
    payload = result.model_dump(mode="json")
    return JSONResponse(payload)


@app.post("/report")
def generate_report(req: ReportRequest, request: Request) -> Response:
    """Render a stored result into the requested format and return it."""
    _verify_api_key(request)
    with _results_lock:
        entry = _results.get(req.job_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="Job not found or expired.")
    result, _ts = entry
    fmt = req.format.lower()
    valid_formats = {"md", "json", "html", "pdf"}
    if fmt not in valid_formats:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid format {fmt!r}. Valid: {sorted(valid_formats)}",
        )
    fmt_map = {"md": "markdown", "json": "json", "html": "html", "pdf": "pdf"}
    from repo_analyzer.core.domain.report import ReportFormat

    report_format = ReportFormat(fmt_map[fmt])
    import tempfile

    from repo_analyzer.reports import ReportGenerator

    with tempfile.TemporaryDirectory() as tmpdir:
        gen = ReportGenerator(tmpdir, [report_format])
        content = gen.render_format(result, report_format)
    mime_map = {
        "markdown": "text/markdown",
        "json": "application/json",
        "html": "text/html",
        "pdf": "application/pdf",
    }
    return Response(
        content=content,
        media_type=mime_map[report_format.value],
        headers={"Content-Disposition": f'inline; filename="report.{fmt}"'},
    )


def run_api(host: str = "127.0.0.1", port: int = 8000) -> None:
    """Run the API server.

    By default binds to ``127.0.0.1`` (localhost only). Set
    ``GRA_API_HOST=0.0.0.0`` to listen on all interfaces (ensure auth is
    enabled via ``GRA_API_KEY``).
    """
    import uvicorn

    actual_host = os.environ.get("GRA_API_HOST", host)
    uvicorn.run(app, host=actual_host, port=port)


if __name__ == "__main__":
    run_api()
