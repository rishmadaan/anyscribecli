"""Tests for Settings (de)serialization."""

from __future__ import annotations

from unittest.mock import patch

from anyscribecli.config.settings import (
    Settings,
    delete_env,
    env_file_keys,
    save_env,
)


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


def test_delete_env_handles_export_prefixed_keys(tmp_path):
    # A hand-edited .env may use valid dotenv `export KEY=...` syntax. Deletion
    # must still match the key, or the removal silently no-ops and python-dotenv
    # reloads it. (Codex review finding, 2026-07-14.)
    env_file = tmp_path / ".env"
    env_file.write_text("export OPENAI_API_KEY=sk-a\nDEEPGRAM_API_KEY=dg-b\n")
    with patch("anyscribecli.config.settings.ENV_FILE", env_file):
        delete_env(["OPENAI_API_KEY"])
        remaining = env_file.read_text()
    assert "OPENAI_API_KEY" not in remaining
    assert "DEEPGRAM_API_KEY=dg-b" in remaining


def test_env_file_keys_normalizes_export_and_skips_noise(tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text("export OPENAI_API_KEY=sk-a\nDEEPGRAM_API_KEY=dg-b\n# note\n\n")
    with patch("anyscribecli.config.settings.ENV_FILE", env_file):
        assert env_file_keys() == {"OPENAI_API_KEY", "DEEPGRAM_API_KEY"}


def test_env_file_keys_empty_when_absent(tmp_path):
    with patch("anyscribecli.config.settings.ENV_FILE", tmp_path / ".env"):
        assert env_file_keys() == set()
