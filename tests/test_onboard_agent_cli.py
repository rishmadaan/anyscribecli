"""Typer runner tests for ``scribe onboard --yes`` (agent-facing mode)."""

from __future__ import annotations

import json
from unittest.mock import patch

import typer
from typer.testing import CliRunner

from anyscribecli.cli.onboard import onboard

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
    monkeypatch.setattr("anyscribecli.cli.onboard.CONFIG_FILE", fake_config)
    result = runner.invoke(
        _make_app(),
        ["--yes", "--provider", "openai", "--json"],
    )
    assert result.exit_code == 2
    err = json.loads(result.stderr.strip().splitlines()[-1])
    assert err["error"] == "already configured"


def test_yes_happy_path_delegates_to_headless(tmp_path, monkeypatch):
    fake_config = tmp_path / "config.yaml"
    monkeypatch.setattr("anyscribecli.cli.onboard.CONFIG_FILE", fake_config)
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
        "anyscribecli.core.onboard_headless.run_headless_onboard",
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
    monkeypatch.setattr("anyscribecli.cli.onboard.CONFIG_FILE", fake_config)
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
        "anyscribecli.core.onboard_headless.run_headless_onboard",
        return_value=partial,
    ):
        result = runner.invoke(
            _make_app(),
            ["--yes", "--provider", "local", "--local-model", "tiny", "--json"],
        )
    assert result.exit_code == 1
