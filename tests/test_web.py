"""Smoke tests for the scribe web UI routes."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from anyscribecli.web.app import create_app


@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)


# ── Health ────────────────────────────────────────────


class TestHealth:
    def test_health_returns_ok(self, client):
        r = client.get("/api/health")
        assert r.status_code == 200
        data = r.json()
        assert "version" in data
        assert "ok" in data
        assert "dependencies" in data


# ── Config ────────────────────────────────────────────


class TestConfig:
    def test_get_config(self, client):
        r = client.get("/api/config")
        assert r.status_code == 200
        data = r.json()
        assert "provider" in data
        assert "language" in data
        assert "_resolved_workspace" in data

    def test_get_providers(self, client):
        r = client.get("/api/providers")
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)
        assert len(data) > 0
        # Each provider has name, description, has_key
        for p in data:
            assert "name" in p
            assert "description" in p
            assert "has_key" in p

    def test_get_keys_status(self, client):
        r = client.get("/api/keys/status")
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, dict)

    def test_test_unknown_provider(self, client):
        r = client.post("/api/providers/nonexistent/test")
        assert r.status_code == 200
        data = r.json()
        assert data["success"] is False


# ── History ───────────────────────────────────────────


class TestHistory:
    def test_list_transcripts(self, client):
        r = client.get("/api/transcripts")
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)

    def test_list_transcripts_with_platform_filter(self, client):
        r = client.get("/api/transcripts?platform=youtube")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_get_nonexistent_transcript(self, client):
        r = client.get("/api/transcripts/does-not-exist-12345")
        assert r.status_code == 404

    def test_workspace_info(self, client):
        r = client.get("/api/workspace/info")
        assert r.status_code == 200
        data = r.json()
        assert "path" in data
        assert "file_count" in data
        assert "total_words" in data


# ── Transcribe ────────────────────────────────────────


class TestTranscribe:
    def test_submit_job(self, client):
        r = client.post("/api/transcribe", json={"url": "https://example.com/test"})
        assert r.status_code == 200
        data = r.json()
        assert "job_id" in data

    def test_get_unknown_job(self, client):
        r = client.get("/api/jobs/nonexistent")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "not_found"


# ── System ────────────────────────────────────────────


class TestSystem:
    def test_version(self, client):
        r = client.get("/api/version")
        assert r.status_code == 200
        data = r.json()
        assert "version" in data

    def test_shutdown(self, client):
        r = client.post("/api/shutdown")
        assert r.status_code == 200
        data = r.json()
        assert data["ok"] is True


# ── SPA Routing ───────────────────────────────────────


class TestSPARouting:
    def test_root_serves_index_html(self, client):
        r = client.get("/")
        assert r.status_code == 200
        assert "text/html" in r.headers.get("content-type", "")

    def test_history_path_serves_index_html(self, client):
        r = client.get("/history")
        assert r.status_code == 200
        assert "text/html" in r.headers.get("content-type", "")

    def test_settings_path_serves_index_html(self, client):
        r = client.get("/settings")
        assert r.status_code == 200
        assert "text/html" in r.headers.get("content-type", "")

    def test_static_assets_served(self, client):
        r = client.get("/favicon.svg")
        assert r.status_code == 200
