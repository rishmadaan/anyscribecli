"""MCP discovery payloads — the model lists agents pick from."""

from __future__ import annotations

import json

import pytest

pytest.importorskip("mcp", reason="mcp extra not installed (pip install 'anyscribe[mcp]')")

from anyscribe.config.settings import Settings
from anyscribe.mcp import server


def test_list_providers_merges_user_added_models(monkeypatch):
    settings = Settings(
        provider="openrouter",
        provider_models={"deepgram": "nova-2"},
        extra_models={"openrouter": ["acme/whisper-xl"]},
    )
    monkeypatch.setattr(server, "_load_settings", lambda: settings)

    by_name = {p["name"]: p for p in json.loads(server.list_providers())}

    assert by_name["openrouter"]["active"] is True
    assert "acme/whisper-xl" in by_name["openrouter"]["models"]
    # Pin wins over the catalog default for the "model" field.
    assert by_name["deepgram"]["model"] == "nova-2"
    assert by_name["openai"]["model"] == "gpt-transcribe"
    # local has no pickable models — its choice lives in settings.local_model.
    assert by_name["local"]["models"] == []


def test_test_provider_alias_reports_the_same_key_status_as_canonical(monkeypatch):
    """The alias must not skip the API-key check.

    `get_provider` normalizes internally, so a raw `sarvam` used for the
    PROVIDER_KEY_ENV lookup silently returned None — reporting a keyless
    provider as fully configured.
    """
    monkeypatch.setattr(server, "_load_settings", lambda: Settings(provider="openai"))
    monkeypatch.delenv("SARGAM_API_KEY", raising=False)

    alias = json.loads(server.test_provider("sarvam"))
    canonical = json.loads(server.test_provider("sargam"))

    assert alias == canonical
    assert alias["provider"] == "sargam"
    assert alias["api_key_env"] == "SARGAM_API_KEY"
    assert alias["api_key_set"] is False
