"""local needs no API key — a local-only setup must not look 'unconfigured'."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from anyscribe.web.app import create_app


@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)


def test_keys_status_includes_local_when_ready(client, monkeypatch):
    monkeypatch.setattr("anyscribe.web.routes.config.faster_whisper_importable", lambda: True)
    data = client.get("/api/keys/status").json()
    assert data["local"] is True


def test_keys_status_local_false_when_not_installed(client, monkeypatch):
    monkeypatch.setattr("anyscribe.web.routes.config.faster_whisper_importable", lambda: False)
    data = client.get("/api/keys/status").json()
    assert data["local"] is False
