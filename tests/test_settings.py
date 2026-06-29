"""Tests for Settings (de)serialization."""

from __future__ import annotations

from anyscribecli.config.settings import Settings


def test_from_dict_tolerates_unknown_keys():
    # A config written by a different version may carry keys this version
    # doesn't know (top-level and inside instagram). It must load, not crash.
    data = {
        "provider": "deepgram",
        "quality": "cost",
        "future_top_level_key": "ignored",
        "instagram": {"username": "me", "browser": "chrome"},
    }
    s = Settings.from_dict(data)
    assert s.provider == "deepgram"
    assert s.quality == "cost"
    assert s.instagram.username == "me"


def test_quality_defaults_to_balanced():
    assert Settings().quality == "balanced"
