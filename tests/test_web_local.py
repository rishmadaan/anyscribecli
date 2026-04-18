"""FastAPI TestClient coverage for the local + models routes.

Real install/download calls are mocked.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from anyscribecli.web.app import create_app


@pytest.fixture
def client():
    return TestClient(create_app())


# ── /api/local/status ─────────────────────────────────


def test_local_status_is_safe_before_setup(client):
    r = client.get("/api/local/status")
    assert r.status_code == 200
    body = r.json()
    for key in (
        "set_up",
        "faster_whisper_installed",
        "default_model",
        "models",
        "recommended_model",
        "choices",
    ):
        assert key in body
    # recommended_model is always one of the valid choices.
    assert body["recommended_model"] in body["choices"]


# ── /api/local/setup ──────────────────────────────────


def test_local_setup_rejects_invalid_model(client):
    r = client.post("/api/local/setup", json={"model": "huge"})
    assert r.status_code == 400
    assert "unknown model" in r.json()["detail"]


def test_local_setup_starts_background_and_is_non_blocking(client):
    # run_setup would normally block; intercept the background entry point so
    # the test returns instantly.
    with patch("anyscribecli.web.routes.local._background_setup", return_value=None):
        r = client.post("/api/local/setup", json={"model": "base"})
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "started"
    assert body["model"] == "base"


def test_concurrent_setup_returns_409(client):
    # First call marks state.running = True; _background_setup is stubbed so
    # it never resets it. A second call must 409.
    with patch("anyscribecli.web.routes.local._background_setup", return_value=None):
        first = client.post("/api/local/setup", json={"model": "base"})
        assert first.status_code == 200
        second = client.post("/api/local/setup", json={"model": "tiny"})
    assert second.status_code == 409


# ── /api/local/teardown ───────────────────────────────


def test_local_teardown_calls_run_teardown(client):
    fake = {
        "status": "removed",
        "models_deleted": [],
        "bytes_freed": 0,
        "uninstall": {"status": "already_absent"},
        "provider_reset": False,
    }
    with patch("anyscribecli.web.routes.local.run_teardown", return_value=fake):
        r = client.post("/api/local/teardown")
    assert r.status_code == 200
    assert r.json()["status"] == "removed"


# ── /api/models/local ─────────────────────────────────


def test_list_local_models_always_returns_five(client):
    r = client.get("/api/models/local")
    assert r.status_code == 200
    body = r.json()
    assert len(body["models"]) == 5


def test_pull_unknown_size_returns_400(client):
    r = client.post("/api/models/local/huge/pull")
    assert r.status_code == 400


def test_pull_without_faster_whisper_returns_409(client):
    with patch(
        "anyscribecli.web.routes.models.faster_whisper_importable",
        return_value=False,
    ):
        r = client.post("/api/models/local/base/pull")
    assert r.status_code == 409


def test_delete_unknown_size_returns_400(client):
    r = client.delete("/api/models/local/huge")
    assert r.status_code == 400


# ── /api/providers (set_up field + has_key honesty) ───


def test_providers_list_includes_set_up_field_for_all(client):
    r = client.get("/api/providers")
    assert r.status_code == 200
    for entry in r.json():
        assert "set_up" in entry
        assert "has_key" in entry


def test_local_provider_honest_about_readiness(client):
    # Without faster-whisper / cached models, has_key must NOT lie.
    with patch("anyscribecli.web.routes.config.local_ready", return_value=False):
        r = client.get("/api/providers")
    local = next(p for p in r.json() if p["name"] == "local")
    assert local["has_key"] is False
    assert local["set_up"] is False


# ── /api/providers/local/test ─────────────────────────


def test_local_test_returns_structured_checks(client):
    r = client.post("/api/providers/local/test")
    assert r.status_code == 200
    body = r.json()
    assert "checks" in body
    assert set(body["checks"].keys()) == {"faster_whisper", "ffmpeg", "model_cached"}
    for sub in body["checks"].values():
        assert "ok" in sub and "message" in sub
