"""FastAPI TestClient coverage for the Web UI wizard backend."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from anyscribecli.web.app import create_app


@pytest.fixture
def client():
    return TestClient(create_app())


def test_status_returns_expected_shape(client):
    r = client.get("/api/onboarding/status")
    assert r.status_code == 200
    body = r.json()
    for key in (
        "completed",
        "has_workspace",
        "has_any_api_key",
        "local_ready",
        "provider_keys",
        "current_provider",
        "recommended_next_step",
    ):
        assert key in body
    # provider_keys must list every API provider.
    assert set(body["provider_keys"].keys()) == {
        "openai",
        "deepgram",
        "elevenlabs",
        "sargam",
        "openrouter",
    }


def test_save_rejects_unknown_provider(client):
    r = client.post("/api/onboarding/save", json={"provider": "nope"})
    assert r.status_code == 400
    assert "unknown provider" in r.json()["detail"]["error"]


def test_save_missing_api_key_returns_400(client, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    r = client.post("/api/onboarding/save", json={"provider": "openai"})
    assert r.status_code == 400
    assert r.json()["detail"]["env_var"] == "OPENAI_API_KEY"


def test_save_delegates_to_headless(client):
    fake_result = {
        "status": "onboarded",
        "provider": "openai",
        "workspace": "/tmp/vault",
        "local_enabled": False,
        "api_keys_set": ["OPENAI_API_KEY"],
        "skill_installed": False,
        "local_setup": None,
        "config_file": "/tmp/cfg.yaml",
    }
    with patch(
        "anyscribecli.web.routes.onboarding.run_headless_onboard",
        return_value=fake_result,
    ) as run:
        r = client.post(
            "/api/onboarding/save",
            json={"provider": "openai", "api_key": "sk-test"},
        )
    assert r.status_code == 200
    run.assert_called_once()
    assert r.json()["status"] == "onboarded"
