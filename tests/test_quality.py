"""Tests for quality-tier → provider resolution."""

from __future__ import annotations

import pytest

from anyscribe.config.settings import Settings
from anyscribe.core.quality import apply_quality


@pytest.fixture(autouse=True)
def _clear_keys(monkeypatch):
    """Start each test with no provider keys set."""
    for env in (
        "OPENAI_API_KEY",
        "ELEVENLABS_API_KEY",
        "DEEPGRAM_API_KEY",
        "GROQ_API_KEY",
        "SARGAM_API_KEY",
        "OPENROUTER_API_KEY",
    ):
        monkeypatch.delenv(env, raising=False)


def test_accuracy_tier_routes_to_elevenlabs(monkeypatch):
    monkeypatch.setenv("ELEVENLABS_API_KEY", "x")
    s = Settings(provider="openai", quality="accuracy")
    apply_quality(s, explicit_provider=False)
    assert s.provider == "elevenlabs"


def test_balanced_tier_routes_to_deepgram(monkeypatch):
    monkeypatch.setenv("DEEPGRAM_API_KEY", "x")
    s = Settings(provider="openai", quality="balanced")
    apply_quality(s, explicit_provider=False)
    assert s.provider == "deepgram"


def test_cost_tier_routes_to_groq(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "x")
    s = Settings(provider="openai", quality="cost")
    apply_quality(s, explicit_provider=False)
    assert s.provider == "groq"


def test_free_tier_routes_to_local_without_a_key():
    s = Settings(provider="openai", quality="free")
    apply_quality(s, explicit_provider=False)
    assert s.provider == "local"


def test_explicit_provider_is_respected(monkeypatch):
    monkeypatch.setenv("ELEVENLABS_API_KEY", "x")
    s = Settings(provider="sargam", quality="accuracy")
    apply_quality(s, explicit_provider=True)
    assert s.provider == "sargam"


def test_missing_key_falls_back_to_configured_provider():
    # accuracy → elevenlabs, but no ELEVENLABS_API_KEY set
    s = Settings(provider="openai", quality="accuracy")
    apply_quality(s, explicit_provider=False)
    assert s.provider == "openai"


def test_unknown_quality_leaves_provider_unchanged():
    s = Settings(provider="openai", quality="")
    apply_quality(s, explicit_provider=False)
    assert s.provider == "openai"
