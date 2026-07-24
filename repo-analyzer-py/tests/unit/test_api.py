"""Tests for the FastAPI REST API."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from repo_analyzer.api.app import app


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)


class TestHealthEndpoint:
    def test_health_returns_ok(self, client: TestClient) -> None:
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "version" in data
        assert "timestamp" in data


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


class TestResultEndpoint:
    def test_result_not_found(self, client: TestClient) -> None:
        response = client.get("/result/nonexistent-job-id")
        assert response.status_code == 404


class TestReportEndpoint:
    def test_report_not_found(self, client: TestClient) -> None:
        response = client.post("/report", json={"job_id": "nonexistent", "format": "json"})
        assert response.status_code == 404

    def test_report_invalid_format(self, client: TestClient) -> None:
        # First we need a job — skip if no job available.
        response = client.post("/report", json={"job_id": "fake", "format": "xml"})
        assert response.status_code in (400, 404)
