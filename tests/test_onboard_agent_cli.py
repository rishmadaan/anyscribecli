"""Typer runner tests for ``scribe onboard --yes`` (agent-facing mode)."""

from __future__ import annotations

import json
from unittest.mock import patch

import typer
from typer.testing import CliRunner

from anyscribe.cli.onboard import onboard

runner = CliRunner()


def _make_app():
    """Tiny one-command Typer app just for testing the onboard function."""
    app = typer.Typer()
    app.command()(onboard)
    return app


def test_yes_without_provider_exits_2_with_json_error():
    result = runner.invoke(_make_app(), ["--yes", "--json"])
    assert result.exit_code == 2
    err = json.loads(result.stderr.strip().splitlines()[-1])
    assert err["error"] == "--provider is required with --yes"


def test_headless_only_flag_without_yes_is_rejected():
    # --provider used without --yes should bail — otherwise agents who forget
    # --yes silently fall into the interactive wizard and hang.
    result = runner.invoke(_make_app(), ["--provider", "openai"])
    assert result.exit_code == 2
    assert "--provider" in result.stderr


def test_yes_with_existing_config_refuses_without_force(tmp_path, monkeypatch):
    # Simulate an existing config file so the "already configured" gate fires.
    fake_config = tmp_path / "config.yaml"
    fake_config.write_text("provider: openai\n")
    monkeypatch.setattr("anyscribe.cli.onboard.CONFIG_FILE", fake_config)
    result = runner.invoke(
        _make_app(),
        ["--yes", "--provider", "openai", "--json"],
    )
    assert result.exit_code == 2
    err = json.loads(result.stderr.strip().splitlines()[-1])
    assert err["error"] == "already configured"


def test_yes_happy_path_delegates_to_headless(tmp_path, monkeypatch):
    fake_config = tmp_path / "config.yaml"
    monkeypatch.setattr("anyscribe.cli.onboard.CONFIG_FILE", fake_config)
    fake_result = {
        "status": "onboarded",
        "provider": "openai",
        "workspace": str(tmp_path / "vault"),
        "local_enabled": False,
        "api_keys_set": ["OPENAI_API_KEY"],
        "skill_installed": False,
        "local_setup": None,
        "config_file": str(fake_config),
    }
    with patch(
        "anyscribe.core.onboard_headless.run_headless_onboard",
        return_value=fake_result,
    ) as run:
        result = runner.invoke(
            _make_app(),
            [
                "--yes",
                "--provider",
                "openai",
                "--api-key",
                "sk-xyz",
                "--json",
            ],
        )
    assert result.exit_code == 0
    run.assert_called_once()
    # Output is multi-line pretty-printed JSON, so parse the whole thing.
    payload = json.loads(result.stdout)
    assert payload["status"] == "onboarded"
    assert payload["provider"] == "openai"


def test_yes_partial_result_exits_1(tmp_path, monkeypatch):
    fake_config = tmp_path / "config.yaml"
    monkeypatch.setattr("anyscribe.cli.onboard.CONFIG_FILE", fake_config)
    partial = {
        "status": "partial",
        "provider": "local",
        "workspace": str(tmp_path / "vault"),
        "local_enabled": False,
        "api_keys_set": [],
        "skill_installed": False,
        "local_setup": {"status": "failed", "phase": "install", "install": {"stderr": "boom"}},
        "config_file": str(fake_config),
    }
    with patch(
        "anyscribe.core.onboard_headless.run_headless_onboard",
        return_value=partial,
    ):
        result = runner.invoke(
            _make_app(),
            ["--yes", "--provider", "local", "--local-model", "tiny", "--json"],
        )
    assert result.exit_code == 1


def test_quality_and_model_flags_require_yes():
    for flag, value in (("--quality", "cost"), ("--model", "whisper-1")):
        result = runner.invoke(_make_app(), [flag, value])
        assert result.exit_code == 2
        assert flag in result.stderr


def test_quality_and_model_flags_reach_headless(tmp_path, monkeypatch):
    fake_config = tmp_path / "config.yaml"
    monkeypatch.setattr("anyscribe.cli.onboard.CONFIG_FILE", fake_config)
    with patch(
        "anyscribe.core.onboard_headless.run_headless_onboard",
        return_value={
            "status": "onboarded",
            "provider": "openai",
            "quality": "custom",
            "model": "whisper-1",
            "workspace": str(tmp_path),
            "local_enabled": False,
            "api_keys_set": [],
            "skill_installed": False,
            "local_setup": None,
            "config_file": str(fake_config),
        },
    ) as run:
        result = runner.invoke(
            _make_app(),
            [
                "--yes",
                "--provider",
                "openai",
                "--api-key",
                "sk-xyz",
                "--quality",
                "custom",
                "--model",
                "whisper-1",
            ],
        )
    assert result.exit_code == 0
    assert run.call_args.kwargs["quality"] == "custom"
    assert run.call_args.kwargs["model"] == "whisper-1"
    assert "quality: custom" in result.stdout and "whisper-1" in result.stdout


def test_invalid_model_is_reported_with_exit_2(tmp_path, monkeypatch):
    fake_config = tmp_path / "config.yaml"
    monkeypatch.setattr("anyscribe.cli.onboard.CONFIG_FILE", fake_config)
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setattr("anyscribe.config.settings.CONFIG_FILE", fake_config)
    result = runner.invoke(
        _make_app(),
        ["--yes", "--provider", "deepgram", "--api-key", "k", "--model", "nope", "--json"],
    )
    assert result.exit_code == 2
    err = json.loads(result.stderr.strip().splitlines()[-1])
    assert err["choices"] == ["nova-3", "nova-2"]


class TestModelPicker:
    """`_pick_model` — the TUI step. bselect is patched; only the write logic runs."""

    def _settings(self, provider="openai"):
        from anyscribe.config.settings import Settings

        return Settings(provider=provider)

    def test_no_picker_when_catalog_has_one_entry(self):
        from anyscribe.cli.onboard import _pick_model

        settings = self._settings("elevenlabs")
        with patch("anyscribe.cli.onboard.bselect") as sel:
            _pick_model("elevenlabs", settings)
        sel.assert_not_called()
        assert settings.provider_models == {}

    def test_no_picker_for_local(self):
        from anyscribe.cli.onboard import _pick_model

        settings = self._settings("local")
        with patch("anyscribe.cli.onboard.bselect") as sel:
            _pick_model("local", settings)
        sel.assert_not_called()

    def test_default_pick_writes_no_pin(self):
        from anyscribe.cli.onboard import _pick_model

        settings = self._settings()
        settings.provider_models["openai"] = "whisper-1"
        with patch("anyscribe.cli.onboard.bselect", side_effect=lambda opts, **kw: opts[0]):
            _pick_model("openai", settings)
        # Picking the catalog default clears the stale pin.
        assert settings.provider_models == {}

    def test_non_default_pick_writes_pin(self):
        from anyscribe.cli.onboard import _pick_model

        settings = self._settings()
        with patch("anyscribe.cli.onboard.bselect", side_effect=lambda opts, **kw: opts[1]):
            _pick_model("openai", settings)
        assert settings.provider_models["openai"] == "whisper-1"

    def test_cursor_starts_on_current_pin(self):
        from anyscribe.cli.onboard import _pick_model

        settings = self._settings()
        settings.provider_models["openai"] = "gpt-4o-transcribe"
        with patch("anyscribe.cli.onboard.bselect", return_value=None) as sel:
            _pick_model("openai", settings)
        assert sel.call_args.kwargs["cursor_index"] == 2

    def test_extra_openrouter_models_are_offered(self):
        from anyscribe.cli.onboard import _pick_model

        settings = self._settings("openrouter")
        settings.extra_models["openrouter"] = ["vendor/custom"]
        with patch("anyscribe.cli.onboard.bselect", side_effect=lambda opts, **kw: opts[-1]):
            _pick_model("openrouter", settings)
        assert settings.provider_models["openrouter"] == "vendor/custom"
