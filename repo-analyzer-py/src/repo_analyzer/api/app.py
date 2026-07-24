"""FastAPI REST API for repo-analyzer.

Exposes the analysis pipeline as a service with the following endpoints:

- ``GET  /health``  — liveness probe.
- ``GET  /status``  — service status + available providers.
- ``POST /analyze`` — start an analysis (returns a job id + result).
- ``GET  /result/{job_id}`` — fetch a stored result.
- ``POST /report``  — render a result into md/json/html/pdf.

The API runs as a separate entry point: ``python -m repo_analyzer.api``.
"""

from __future__ import annotations

import threading
import uuid
from datetime import datetime
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, Field

from repo_analyzer.adapters.cache import SQLiteCacheAdapter
from repo_analyzer.adapters.llm import MockLLMProvider
from repo_analyzer.core.domain.repository import parse_repository_url
from repo_analyzer.core.orchestrator import Orchestrator
from repo_analyzer.infrastructure.config import load_config
from repo_analyzer.infrastructure.logging import get_logger
from repo_analyzer.reports import ReportGenerator
from repo_analyzer.utils.validation import is_valid_git_url

_logger = get_logger(__name__)

#: In-memory store for analysis results (job_id → AnalysisResult).
_results: dict[str, Any] = {}
_results_lock = threading.Lock()

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
# Endpoints
# ---------------------------------------------------------------------------


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    """Liveness probe."""
    return HealthResponse(status="ok", version="0.1.0", timestamp=datetime.now().isoformat())


@app.get("/status")
def status() -> dict[str, Any]:
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
def analyze(req: AnalyzeRequest) -> AnalyzeResponse:
    """Start an analysis and return the job id + result.

    The analysis runs synchronously (blocking) and the full result is stored
    in memory under the returned ``job_id``.
    """
    if not is_valid_git_url(req.repository_url):
        raise HTTPException(status_code=400, detail="Invalid repository URL.")
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
        _results[job_id] = result
    return AnalyzeResponse(
        job_id=job_id,
        status=result.status.value,
        repository=f"{repository.owner}/{repository.name}",
        started_at=started,
    )


@app.get("/result/{job_id}")
def get_result(job_id: str) -> JSONResponse:
    """Fetch a stored analysis result as JSON."""
    with _results_lock:
        result = _results.get(job_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Job not found.")
    payload = result.model_dump(mode="json", default=str)
    return JSONResponse(payload)


@app.post("/report")
def generate_report(req: ReportRequest) -> Response:
    """Render a stored result into the requested format and return it."""
    with _results_lock:
        result = _results.get(req.job_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Job not found.")
    fmt = req.format.lower()
    valid_formats = {"md", "json", "html", "pdf"}
    if fmt not in valid_formats:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid format {fmt!r}. Valid: {sorted(valid_formats)}",
        )
    # Map short names to ReportFormat values.
    fmt_map = {"md": "markdown", "json": "json", "html": "html", "pdf": "pdf"}
    from repo_analyzer.core.domain.report import ReportFormat

    report_format = ReportFormat(fmt_map[fmt])

    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        gen = ReportGenerator(tmpdir, [report_format])
        content = gen.render_format(result, report_format)
    mime_map = {
        "markdown": "text/markdown",
        "json": "application/json",
        "html": "text/html",
        "pdf": "application/pdf",
    }
    return Response(content=content, media_type=mime_map[report_format.value])


def run_api(host: str = "0.0.0.0", port: int = 8000) -> None:
    """Run the API server (used by ``python -m repo_analyzer.api``)."""
    import uvicorn

    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    run_api()
