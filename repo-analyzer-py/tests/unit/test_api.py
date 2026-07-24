"""Tests for the FastAPI REST API.

Covers:
    - Health / status endpoints.
    - Analyze endpoint validation + SSRF protection.
    - Result endpoint (including the model_dump fix).
    - Report endpoint validation.
    - Rate limiting.
"""

from __future__ import annotations

import importlib

import pytest
from fastapi.testclient import TestClient

# Import the module directly (not the `app` symbol) so we can access
# module-level state like `_rate_lock` and `_results`.
_api_module = importlib.import_module("repo_analyzer.api.app")
app = _api_module.app


@pytest.fixture(autouse=True)
def reset_rate_limit() -> None:
    """Reset the rate-limit buckets before each test."""
    with _api_module._rate_lock:
        _api_module._rate_buckets.clear()


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture()
def stored_result() -> str:
    """Insert a fake result into the API's in-memory store and return its id."""
    import time

    from repo_analyzer.core.domain.analysis_result import AnalysisResult
    from repo_analyzer.core.domain.repository import parse_repository_url

    repo = parse_repository_url("https://github.com/test/repo")
    result = AnalysisResult(repository=repo)
    job_id = "test-job-id"
    with _api_module._results_lock:
        _api_module._results[job_id] = (result, time.time())
    return job_id


class TestHealthEndpoint:
    def test_health_returns_ok(self, client: TestClient) -> None:
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "version" in data
        assert "timestamp" in data

    def test_health_not_rate_limited(self, client: TestClient) -> None:
        """The /health endpoint should not be rate-limited."""
        for _ in range(20):
            response = client.get("/health")
            assert response.status_code == 200


class TestStatusEndpoint:
    def test_status_returns_info(self, client: TestClient) -> None:
        response = client.get("/status")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "running"
        assert "llm_providers" in data
        assert "mock" in data["llm_providers"]
        assert "endpoints" in data


class TestAnalyzeEndpoint:
    def test_analyze_invalid_url(self, client: TestClient) -> None:
        response = client.post("/analyze", json={"repository_url": "not-a-url"})
        assert response.status_code == 400

    def test_analyze_missing_url(self, client: TestClient) -> None:
        response = client.post("/analyze", json={})
        assert response.status_code == 422  # validation error

    def test_analyze_ssrf_blocked(self, client: TestClient) -> None:
        """SSRF protection: private/loopback IPs must be blocked."""
        response = client.post(
            "/analyze",
            json={"repository_url": "https://127.0.0.1:8080/secret"},
        )
        assert response.status_code == 400
        assert "blocked" in response.json()["detail"].lower()

    def test_analyze_metadata_ip_blocked(self, client: TestClient) -> None:
        """Cloud metadata endpoints must be blocked."""
        response = client.post(
            "/analyze",
            json={"repository_url": "https://169.254.169.254/latest/meta-data/"},
        )
        assert response.status_code == 400


class TestResultEndpoint:
    def test_result_not_found(self, client: TestClient) -> None:
        response = client.get("/result/nonexistent-job-id")
        assert response.status_code == 404

    def test_result_returns_valid_json(self, client: TestClient, stored_result: str) -> None:
        """The /result endpoint must return valid JSON (not 500).

        This is a regression test for the ``model_dump(default=str)`` bug
        that caused a 500 error on every /result call.
        """
        response = client.get(f"/result/{stored_result}")
        assert response.status_code == 200
        data = response.json()
        assert "repository" in data
        assert "status" in data


class TestReportEndpoint:
    def test_report_not_found(self, client: TestClient) -> None:
        response = client.post("/report", json={"job_id": "nonexistent", "format": "json"})
        assert response.status_code == 404

    def test_report_invalid_format(self, client: TestClient, stored_result: str) -> None:
        response = client.post("/report", json={"job_id": stored_result, "format": "xml"})
        assert response.status_code == 400

    def test_report_json(self, client: TestClient, stored_result: str) -> None:
        """The /report endpoint must produce a JSON report."""
        response = client.post("/report", json={"job_id": stored_result, "format": "json"})
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"

    def test_report_markdown(self, client: TestClient, stored_result: str) -> None:
        """The /report endpoint must produce a Markdown report."""
        response = client.post("/report", json={"job_id": stored_result, "format": "md"})
        assert response.status_code == 200
        assert "markdown" in response.headers["content-type"]


class TestRateLimiting:
    def test_rate_limit_enforced(self, client: TestClient) -> None:
        """After exceeding the rate limit, 429 must be returned."""
        # The rate limit is 10 requests per 60s per IP.
        # /health is excluded, so use /status.
        got_429 = False
        for _ in range(15):
            response = client.get("/status")
            if response.status_code == 429:
                got_429 = True
                break
        assert got_429, "Expected at least one 429 response"
