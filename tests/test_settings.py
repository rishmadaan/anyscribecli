"""Tests for Settings (de)serialization."""

from __future__ import annotations

from unittest.mock import patch

from anyscribecli.config.settings import Settings, delete_env, save_env


def test_from_dict_tolerates_unknown_keys():
    # A config written by a different version may carry keys this version
    # doesn't know (top-level and inside instagram). It must load, not crash.
    data = {
        "provider": "deepgram",
        "quality": "cost",
        "future_top_level_key": "ignored",
        "instagram": {"browser": "chrome", "username": "legacy-pre-0.8.3"},
    }
    s = Settings.from_dict(data)
    assert s.provider == "deepgram"
    assert s.quality == "cost"
    assert s.instagram.browser == "chrome"  # known key kept; unknown 'username' dropped


def test_quality_defaults_to_balanced():
    assert Settings().quality == "balanced"


def test_delete_env_removes_only_named_keys(tmp_path):
    env_file = tmp_path / ".env"
    with patch("anyscribecli.config.settings.ENV_FILE", env_file):
        save_env({"OPENAI_API_KEY": "sk-a", "DEEPGRAM_API_KEY": "dg-b"})
        delete_env(["OPENAI_API_KEY"])
        remaining = env_file.read_text()
    assert "OPENAI_API_KEY" not in remaining
    assert "DEEPGRAM_API_KEY=dg-b" in remaining


def test_delete_env_missing_file_is_noop(tmp_path):
    env_file = tmp_path / ".env"  # never created
    with patch("anyscribecli.config.settings.ENV_FILE", env_file):
        delete_env(["OPENAI_API_KEY"])  # must not raise
    assert not env_file.exists()
