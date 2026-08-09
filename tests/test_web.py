"""Smoke tests for the scribe web UI routes."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from anyscribe.web.app import create_app


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

    def test_get_config_exposes_quality_tiers(self, client):
        # The tier -> provider map the UI captions each quality choice with.
        tiers = client.get("/api/config").json()["_quality_tiers"]
        assert tiers["balanced"] == "deepgram"
        assert set(tiers) == {"accuracy", "balanced", "cost", "free"}

    def test_put_config_returns_same_payload_shape_as_get(self, client, tmp_path, monkeypatch):
        monkeypatch.setattr("anyscribe.config.settings.CONFIG_FILE", tmp_path / "config.yaml")
        r = client.put("/api/config", json={"keep_media": True})
        assert r.status_code == 200
        assert set(r.json()) == set(client.get("/api/config").json())

    def test_put_config_rejects_invalid_model_pin(self, client, tmp_path, monkeypatch):
        # Invalid entries are refused outright — nothing is persisted.
        monkeypatch.setattr("anyscribe.config.settings.CONFIG_FILE", tmp_path / "config.yaml")
        r = client.put("/api/config", json={"provider_models": {"deepgram": "nova-9"}})
        assert r.status_code == 422
        assert r.json()["success"] is False
        assert not (tmp_path / "config.yaml").exists()

    def test_put_config_provider_sets_quality_custom(self, client, tmp_path, monkeypatch):
        monkeypatch.setattr("anyscribe.config.settings.CONFIG_FILE", tmp_path / "config.yaml")
        r = client.put("/api/config", json={"provider": "groq"})
        assert r.status_code == 200
        assert r.json()["provider"] == "groq"
        assert r.json()["quality"] == "custom"

    def test_put_config_canonicalizes_the_sarvam_spelling(self, client, tmp_path, monkeypatch):
        monkeypatch.setattr("anyscribe.config.settings.CONFIG_FILE", tmp_path / "config.yaml")
        r = client.put("/api/config", json={"provider": "sarvam"})
        assert r.status_code == 200
        assert r.json()["provider"] == "sargam"

    def test_provider_test_route_accepts_the_sarvam_spelling(self, client, monkeypatch):
        monkeypatch.delenv("SARGAM_API_KEY", raising=False)
        # Reaching the "key not set" answer proves the name resolved; an
        # unresolved name would have answered "Unknown provider" instead.
        data = client.post("/api/providers/sarvam/test").json()
        assert data["message"] == "API key not set (SARGAM_API_KEY)"

    def test_provider_languages_route_accepts_the_sarvam_spelling(self, client):
        # Its sibling /test route normalizes; an empty list here would render
        # the wizard's language dropdown blank for the aliased name.
        alias = client.get("/api/providers/sarvam/languages").json()
        assert alias == client.get("/api/providers/sargam/languages").json()
        assert alias["languages"], alias

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
            assert "key_in_env_file" in p

    def test_get_providers_merges_user_added_models(self, client, tmp_path, monkeypatch):
        monkeypatch.setattr("anyscribe.config.settings.CONFIG_FILE", tmp_path / "config.yaml")
        client.put("/api/config", json={"extra_models": {"openrouter": ["acme/whisper-xl"]}})
        openrouter = next(
            p for p in client.get("/api/providers").json() if p["name"] == "openrouter"
        )
        assert openrouter["models"][-1] == "acme/whisper-xl"
        assert openrouter["models"][0] == "openai/gpt-audio-mini"  # catalog default still first

    def test_get_keys_status(self, client):
        r = client.get("/api/keys/status")
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, dict)

    def test_delete_key_unknown_provider(self, client):
        # Route is wired and rejects a provider with no API key. Uses a name
        # with no env var, so it never touches the real .env.
        r = client.delete("/api/keys/local")
        assert r.status_code == 200
        assert r.json()["success"] is False

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
        assert "items" in data
        assert "total" in data
        assert isinstance(data["items"], list)

    def test_list_transcripts_with_platform_filter(self, client):
        r = client.get("/api/transcripts?platform=youtube")
        assert r.status_code == 200
        data = r.json()
        assert "items" in data
        assert isinstance(data["items"], list)

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

    def test_upload_preserves_safe_original_filename(self, client, tmp_path, monkeypatch):
        from anyscribe.web.routes import transcribe

        monkeypatch.setattr(transcribe, "TMP_DIR", tmp_path)
        r = client.post(
            "/api/upload",
            files={"file": ("My Recording.mp3", b"fake audio", "audio/mpeg")},
        )

        assert r.status_code == 200
        path = Path(r.json()["path"])
        assert path.name == "My Recording.mp3"
        assert path.parent.parent == tmp_path / "uploads"
        assert path.read_bytes() == b"fake audio"

    def test_upload_sanitizes_path_like_filename(self, client, tmp_path, monkeypatch):
        from anyscribe.web.routes import transcribe

        monkeypatch.setattr(transcribe, "TMP_DIR", tmp_path)
        r = client.post(
            "/api/upload",
            files={"file": ("../.secret.mp3", b"fake audio", "audio/mpeg")},
        )

        assert r.status_code == 200
        path = Path(r.json()["path"])
        assert path.name == "secret.mp3"
        assert path.parent.parent == tmp_path / "uploads"
        assert path.read_bytes() == b"fake audio"

    def test_get_unknown_job(self, client):
        r = client.get("/api/jobs/nonexistent")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "not_found"

    def test_cancel_unknown_job(self, client):
        r = client.post("/api/jobs/nonexistent/cancel")
        assert r.status_code == 404

    def test_cancel_finished_job_is_noop(self, client):
        from anyscribe.web.jobs import Job, JobStatus, job_manager

        job = Job(id="finished1", url="https://example.com/x", status=JobStatus.COMPLETED)
        job_manager._jobs[job.id] = job
        r = client.post(f"/api/jobs/{job.id}/cancel")
        assert r.status_code == 200
        # Status unchanged and no cancellation requested on an already-finished job.
        assert r.json()["status"] == "completed"
        assert job.cancel_requested is False


# ── System ────────────────────────────────────────────


class TestSystem:
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


def test_config_payload_carries_resolved_plan(client):
    r = client.get("/api/config")
    assert r.status_code == 200
    resolved = r.json()["_resolved"]
    assert "provider" in resolved and "model" in resolved and "via" in resolved


def test_config_payload_resolved_error_for_bogus_provider(client, monkeypatch):
    # A hand-edited config with an unknown provider must yield {error}, not 500.
    from anyscribe.config.settings import Settings

    monkeypatch.setattr(
        "anyscribe.web.routes.config.load_config",
        lambda: Settings(provider="whisper", quality="custom"),
    )
    r = client.get("/api/config")
    assert r.status_code == 200
    assert "Unknown provider" in r.json()["_resolved"]["error"]


def test_put_config_instagram_unknown_key_rolls_back(client):
    client.put("/api/config", json={"instagram": {"browser": "chrome"}})
    r = client.put("/api/config", json={"instagram": {"bogus": "x", "browser": "safari"}})
    assert r.status_code == 422
    r = client.get("/api/config")
    assert r.json()["instagram"] == {"browser": "chrome"}


def test_put_config_instagram_browser(client):
    r = client.put("/api/config", json={"instagram": {"browser": "firefox"}})
    assert r.status_code == 200
    assert r.json()["instagram"]["browser"] == "firefox"
    r = client.put("/api/config", json={"instagram": {"browser": ""}})
    assert r.status_code == 200
    assert r.json()["instagram"]["browser"] == ""
