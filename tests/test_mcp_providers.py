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
