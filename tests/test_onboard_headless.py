"""Unit tests for the headless onboarding backend.

Local-setup side effects (pip install, HF download) are always mocked — these
tests stay fast and network-free.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from anyscribecli.core import onboard_headless


def test_validation_rejects_unknown_provider(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    with pytest.raises(onboard_headless.OnboardValidationError) as exc:
        onboard_headless.run_headless_onboard(provider="nope")
    assert "unknown provider" in exc.value.payload["error"]


def test_validation_requires_local_model_for_local_provider(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    with pytest.raises(onboard_headless.OnboardValidationError) as exc:
        onboard_headless.run_headless_onboard(provider="local")
    assert "local-model" in exc.value.payload["error"]
    assert exc.value.payload["recommended"] == "base"


def test_validation_requires_api_key_for_api_provider(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(onboard_headless.OnboardValidationError) as exc:
        onboard_headless.run_headless_onboard(provider="openai")
    assert exc.value.payload["env_var"] == "OPENAI_API_KEY"


def test_env_var_satisfies_api_key_requirement(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    with patch("anyscribecli.vault.scaffold.create_vault", return_value=tmp_path):
        with patch("anyscribecli.core.migrate.maybe_migrate_workspace", return_value=None):
            with patch("anyscribecli.core.onboard_headless.ensure_app_dirs"):
                result = onboard_headless.run_headless_onboard(
                    provider="openai", install_skill=False
                )
    assert result["status"] == "onboarded"
    assert result["provider"] == "openai"


def test_api_key_arg_is_written_to_env_and_process(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    saved = {}

    def fake_save_env(keys):
        saved.update(keys)

    with patch("anyscribecli.vault.scaffold.create_vault", return_value=tmp_path):
        with patch("anyscribecli.core.migrate.maybe_migrate_workspace", return_value=None):
            with patch("anyscribecli.core.onboard_headless.ensure_app_dirs"):
                with patch(
                    "anyscribecli.core.onboard_headless.save_env", side_effect=fake_save_env
                ):
                    result = onboard_headless.run_headless_onboard(
                        provider="openai", api_key="sk-abc", install_skill=False
                    )
    assert saved == {"OPENAI_API_KEY": "sk-abc"}
    # Also written to process env so downstream code sees it.
    import os

    assert os.environ["OPENAI_API_KEY"] == "sk-abc"
    assert result["api_keys_set"] == ["OPENAI_API_KEY"]


def test_local_provider_runs_local_setup_and_returns_partial_on_failure(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    failure = {"status": "failed", "phase": "install", "install": {"stderr": "denied"}}

    with patch("anyscribecli.vault.scaffold.create_vault", return_value=tmp_path):
        with patch("anyscribecli.core.migrate.maybe_migrate_workspace", return_value=None):
            with patch("anyscribecli.core.onboard_headless.ensure_app_dirs"):
                with patch("anyscribecli.core.local_setup.run_setup", return_value=failure):
                    result = onboard_headless.run_headless_onboard(
                        provider="local", local_model="tiny", install_skill=False
                    )
    assert result["status"] == "partial"
    assert result["local_setup"] == failure


def test_instagram_browser_validation_rejects_unsupported(tmp_path, monkeypatch):
    """An unsupported browser name raises OnboardValidationError, not silently saved."""
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")

    with pytest.raises(onboard_headless.OnboardValidationError) as exc_info:
        onboard_headless.run_headless_onboard(
            provider="openai",
            api_key="sk-test",
            instagram_browser="firefoxx",  # typo — should be rejected
        )
    payload = exc_info.value.payload
    assert "firefoxx" in payload["error"]
    assert "firefox" in payload["choices"]


def test_instagram_browser_validation_accepts_empty_and_none(tmp_path, monkeypatch):
    """Empty string and 'none' are valid (mean: no cookies)."""
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")

    with patch("anyscribecli.vault.scaffold.create_vault", return_value=tmp_path):
        with patch("anyscribecli.core.migrate.maybe_migrate_workspace", return_value=None):
            with patch("anyscribecli.core.onboard_headless.ensure_app_dirs"):
                # Empty — accepted.
                result1 = onboard_headless.run_headless_onboard(
                    provider="openai",
                    api_key="sk-test",
                    instagram_browser="",
                    install_skill=False,
                )
    assert result1["status"] in ("onboarded", "partial")

    with patch("anyscribecli.vault.scaffold.create_vault", return_value=tmp_path):
        with patch("anyscribecli.core.migrate.maybe_migrate_workspace", return_value=None):
            with patch("anyscribecli.core.onboard_headless.ensure_app_dirs"):
                # 'none' — accepted.
                result2 = onboard_headless.run_headless_onboard(
                    provider="openai",
                    api_key="sk-test",
                    instagram_browser="none",
                    install_skill=False,
                )
    assert result2["status"] in ("onboarded", "partial")


def test_instagram_browser_routes_to_config_not_env(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    saved = {}

    def fake_save_env(keys):
        saved.update(keys)

    with patch("anyscribecli.vault.scaffold.create_vault", return_value=tmp_path):
        with patch("anyscribecli.core.migrate.maybe_migrate_workspace", return_value=None):
            with patch("anyscribecli.core.onboard_headless.ensure_app_dirs"):
                with patch(
                    "anyscribecli.core.onboard_headless.save_env", side_effect=fake_save_env
                ):
                    result = onboard_headless.run_headless_onboard(
                        provider="openai",
                        instagram_browser="firefox",
                        install_skill=False,
                    )
    # Browser name goes to config, NOT to .env — INSTAGRAM_PASSWORD is never written.
    assert "INSTAGRAM_PASSWORD" not in saved
    assert "INSTAGRAM_PASSWORD" not in result["api_keys_set"]
