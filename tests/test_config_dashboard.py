"""Tests for the bare `scribe config` defaults dashboard and its JSON shape."""

from __future__ import annotations

import json

import pytest
from typer.testing import CliRunner

from anyscribecli.cli.config_cmd import config_app, providers_app
from anyscribecli.config.settings import Settings, save_config
from anyscribecli.providers import PROVIDER_KEY_ENV, list_providers

runner = CliRunner()


@pytest.fixture(autouse=True)
def isolated_config(tmp_path, monkeypatch):
    """Point config.yaml/.env at tmp_path and start with no API keys set."""
    monkeypatch.setattr("anyscribecli.config.settings.CONFIG_FILE", tmp_path / "config.yaml")
    monkeypatch.setattr("anyscribecli.config.settings.ENV_FILE", tmp_path / ".env")
    for env in PROVIDER_KEY_ENV.values():
        if env:
            monkeypatch.delenv(env, raising=False)
    return tmp_path


def _json(result):
    return json.loads(result.stdout)


# ── dashboard ─────────────────────────────────────────


def test_bare_config_renders_dashboard_on_default_config():
    result = runner.invoke(config_app, [])
    assert result.exit_code == 0
    assert "Next run:" in result.output
    for name in list_providers():
        assert name in result.output
    assert "scribe config set provider" in result.output


def test_dashboard_renders_on_populated_config(monkeypatch):
    monkeypatch.setenv("DEEPGRAM_API_KEY", "dg-test")
    save_config(
        Settings(
            provider="openrouter",
            quality="custom",
            provider_models={"openai": "whisper-1"},
            extra_models={"openrouter": ["acme/asr-1"]},
        )
    )
    result = runner.invoke(config_app, [])
    assert result.exit_code == 0
    assert "→ openrouter" in result.output
    assert "pinned" in result.output
    assert "1 custom" in result.output
    assert "balanced" in result.output  # tier label on deepgram's row


def test_dashboard_shows_keyless_tier_warning():
    save_config(Settings(quality="accuracy", provider="openai"))
    result = runner.invoke(config_app, [])
    assert "WARNING" in result.output
    assert "ELEVENLABS_API_KEY" in result.output


def test_dashboard_flags_missing_keys(monkeypatch):
    monkeypatch.setenv("DEEPGRAM_API_KEY", "dg-test")
    result = runner.invoke(config_app, [])
    assert "Missing keys:    elevenlabs, groq, openai, openrouter, sargam" in result.output
    assert "_api_key" in result.output  # wraps at 80 cols, so match the tail only


# ── dashboard --json ──────────────────────────────────


def test_dashboard_json_shape(monkeypatch):
    monkeypatch.setenv("DEEPGRAM_API_KEY", "dg-test")
    save_config(
        Settings(
            provider="openrouter",
            quality="custom",
            provider_models={"deepgram": "nova-2"},
            extra_models={"openrouter": ["acme/asr-1"]},
        )
    )
    data = _json(runner.invoke(config_app, ["--json"]))

    assert data["provider"] == "openrouter"  # full settings dict is still there
    assert data["resolved"] == {
        "provider": "openrouter",
        "model": "openai/gpt-audio-mini",
        "via": "config",
        "notes": [],
    }
    by_name = {p["name"]: p for p in data["providers"]}
    assert set(by_name) == set(list_providers())
    assert by_name["deepgram"] == {
        "name": "deepgram",
        "default_model": "nova-2",
        "models": ["nova-3", "nova-2"],
        "has_key": True,
        "tier": "balanced",
        "pinned": True,
        "custom_models": [],
    }
    assert by_name["openrouter"]["custom_models"] == ["acme/asr-1"]
    assert "acme/asr-1" in by_name["openrouter"]["models"]
    assert by_name["local"] == {
        "name": "local",
        "default_model": None,
        "models": [],
        "has_key": True,
        "tier": "free",
        "pinned": False,
        "custom_models": [],
    }
    assert by_name["groq"]["has_key"] is False


def test_dashboard_json_carries_resolve_notes():
    save_config(Settings(quality="cost", provider="openai"))
    data = _json(runner.invoke(config_app, ["--json"]))
    assert data["resolved"]["provider"] == "openai"
    assert any("GROQ_API_KEY" in n for n in data["resolved"]["notes"])


# ── subcommands still reachable ───────────────────────


def test_help_still_lists_subcommands():
    result = runner.invoke(config_app, ["--help"])
    assert result.exit_code == 0
    for sub in ("show", "set", "path", "list-keys"):
        assert sub in result.output


def test_show_subcommand_unaffected():
    result = runner.invoke(config_app, ["show", "--json"])
    assert result.exit_code == 0
    assert "resolved" not in _json(result)


# ── list-keys ─────────────────────────────────────────


def test_list_keys_includes_model_rows_when_unset():
    rows = {r["key"]: r["value"] for r in _json(runner.invoke(config_app, ["list-keys", "--json"]))}
    assert rows["provider_models.openai"] == "(default)"
    assert rows["extra_models.openrouter"] == "(none)"
    assert "provider_models.local" not in rows  # no pickable models
    assert rows["provider"] == "openai"


def test_list_keys_shows_current_pins_and_extras():
    save_config(
        Settings(
            provider_models={"openai": "whisper-1"},
            extra_models={"openrouter": ["acme/asr-1", "acme/asr-2"]},
        )
    )
    rows = {r["key"]: r["value"] for r in _json(runner.invoke(config_app, ["list-keys", "--json"]))}
    assert rows["provider_models.openai"] == "whisper-1"
    assert rows["extra_models.openrouter"] == "acme/asr-1, acme/asr-2"


# ── providers list ────────────────────────────────────


def test_providers_list_json_merges_custom_models():
    save_config(Settings(extra_models={"openrouter": ["acme/asr-1"]}))
    by_name = {p["name"]: p for p in _json(runner.invoke(providers_app, ["list", "--json"]))}
    assert "acme/asr-1" in by_name["openrouter"]["models"]
    assert by_name["openrouter"]["custom_models"] == ["acme/asr-1"]
    assert by_name["openai"]["model"] == "gpt-transcribe"


def test_providers_list_table_marks_custom_models():
    save_config(Settings(extra_models={"openrouter": ["acme/asr-1"]}))
    result = runner.invoke(providers_app, ["list"])
    assert result.exit_code == 0
    assert "custom" in result.output


def test_dashboard_survives_unknown_provider_in_config(monkeypatch, tmp_path, capsys):
    # Hand-edited config with a bogus provider: the dashboard is where users
    # diagnose that, so it must error cleanly, not traceback (finding D1).
    import json as _json

    import yaml as _yaml
    from typer.testing import CliRunner

    import anyscribecli.config.settings as settings_mod
    from anyscribecli.cli.main import app

    cfg = tmp_path / "config.yaml"
    cfg.write_text(_yaml.dump({"provider": "whisper", "quality": "custom"}))
    monkeypatch.setattr(settings_mod, "CONFIG_FILE", cfg)

    runner = CliRunner()
    result = runner.invoke(app, ["config"])
    assert result.exit_code == 1
    assert "Unknown provider" in result.output

    result = runner.invoke(app, ["config", "--json"])
    assert result.exit_code == 1
    payload = _json.loads(result.stdout)
    assert "Unknown provider" in payload["error"]
