"""Unit tests for the headless onboarding backend.

Local-setup side effects (pip install, HF download) are always mocked; these
tests stay fast and network-free.
"""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest

from anyscribe.core import onboard_headless


def _isolated_config(tmp_path):
    app_home = tmp_path / ".anyscribe"
    return patch.multiple(
        "anyscribe.config.settings",
        CONFIG_FILE=app_home / "config.yaml",
        ENV_FILE=app_home / ".env",
    )


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
    with _isolated_config(tmp_path):
        with patch("anyscribe.vault.scaffold.create_vault", return_value=tmp_path):
            with patch("anyscribe.core.migrate.maybe_migrate_workspace", return_value=None):
                with patch("anyscribe.core.onboard_headless.ensure_app_dirs"):
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

    with _isolated_config(tmp_path):
        with patch("anyscribe.vault.scaffold.create_vault", return_value=tmp_path):
            with patch("anyscribe.core.migrate.maybe_migrate_workspace", return_value=None):
                with patch("anyscribe.core.onboard_headless.ensure_app_dirs"):
                    with patch(
                        "anyscribe.core.onboard_headless.save_env", side_effect=fake_save_env
                    ):
                        result = onboard_headless.run_headless_onboard(
                            provider="openai", api_key="sk-abc", install_skill=False
                        )
    assert saved == {"OPENAI_API_KEY": "sk-abc"}
    assert os.environ["OPENAI_API_KEY"] == "sk-abc"
    assert result["api_keys_set"] == ["OPENAI_API_KEY"]


def test_local_provider_runs_local_setup_and_returns_partial_on_failure(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    failure = {"status": "failed", "phase": "install", "install": {"stderr": "denied"}}

    with _isolated_config(tmp_path):
        with patch("anyscribe.vault.scaffold.create_vault", return_value=tmp_path):
            with patch("anyscribe.core.migrate.maybe_migrate_workspace", return_value=None):
                with patch("anyscribe.core.onboard_headless.ensure_app_dirs"):
                    with patch("anyscribe.core.local_setup.run_setup", return_value=failure):
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

    with patch("anyscribe.vault.scaffold.create_vault", return_value=tmp_path):
        with patch("anyscribe.core.migrate.maybe_migrate_workspace", return_value=None):
            with patch("anyscribe.core.onboard_headless.ensure_app_dirs"):
                # Empty — accepted.
                result1 = onboard_headless.run_headless_onboard(
                    provider="openai",
                    api_key="sk-test",
                    instagram_browser="",
                    install_skill=False,
                )
    assert result1["status"] in ("onboarded", "partial")

    with patch("anyscribe.vault.scaffold.create_vault", return_value=tmp_path):
        with patch("anyscribe.core.migrate.maybe_migrate_workspace", return_value=None):
            with patch("anyscribe.core.onboard_headless.ensure_app_dirs"):
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

    with patch("anyscribe.vault.scaffold.create_vault", return_value=tmp_path):
        with patch("anyscribe.core.migrate.maybe_migrate_workspace", return_value=None):
            with patch("anyscribe.core.onboard_headless.ensure_app_dirs"):
                with patch("anyscribe.core.onboard_headless.save_env", side_effect=fake_save_env):
                    result = onboard_headless.run_headless_onboard(
                        provider="openai",
                        instagram_browser="firefox",
                        install_skill=False,
                    )
    # Browser name goes to config, NOT to .env — INSTAGRAM_PASSWORD is never written.
    assert "INSTAGRAM_PASSWORD" not in saved
    assert "INSTAGRAM_PASSWORD" not in result["api_keys_set"]


def test_instagram_browser_validation_runs_even_when_provider_is_local(tmp_path, monkeypatch):
    """Regression: previously _validate returned early on provider='local',
    skipping the IG browser check. The validator must reject typos
    regardless of provider."""
    from anyscribe.core.onboard_headless import (
        OnboardValidationError,
        run_headless_onboard,
    )

    monkeypatch.setenv("HOME", str(tmp_path))

    with pytest.raises(OnboardValidationError) as exc_info:
        run_headless_onboard(
            provider="local",
            local_model="tiny",
            instagram_browser="firefoxx",  # typo
        )
    assert "firefoxx" in exc_info.value.payload["error"]


def test_instagram_browser_is_normalized_on_save(tmp_path, monkeypatch):
    """Browser is stored in canonical form: lowercase, stripped, with 'none' -> ''."""
    from anyscribe.config.settings import load_config
    from anyscribe.core.onboard_headless import run_headless_onboard

    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("ANYSCRIBE_HOME", str(tmp_path))
    monkeypatch.setattr("anyscribe.config.paths.APP_HOME", tmp_path)

    # Uppercase + whitespace -> canonical lowercase
    with patch("anyscribe.vault.scaffold.create_vault", return_value=tmp_path):
        with patch("anyscribe.core.migrate.maybe_migrate_workspace", return_value=None):
            with patch("anyscribe.core.onboard_headless.ensure_app_dirs"):
                run_headless_onboard(
                    provider="openai",
                    api_key="sk-test",
                    instagram_browser="  FIREFOX  ",
                    install_skill=False,
                )
    assert load_config().instagram.browser == "firefox"

    # 'none' -> empty string (canonical "no cookies")
    with patch("anyscribe.vault.scaffold.create_vault", return_value=tmp_path):
        with patch("anyscribe.core.migrate.maybe_migrate_workspace", return_value=None):
            with patch("anyscribe.core.onboard_headless.ensure_app_dirs"):
                run_headless_onboard(
                    provider="openai",
                    api_key="sk-test",
                    instagram_browser="none",
                    install_skill=False,
                )
    assert load_config().instagram.browser == ""


def _run_isolated(tmp_path, **kwargs):
    """run_headless_onboard against an isolated config file, no side effects."""
    with _isolated_config(tmp_path):
        with patch("anyscribe.vault.scaffold.create_vault", return_value=tmp_path):
            with patch("anyscribe.core.migrate.maybe_migrate_workspace", return_value=None):
                with patch("anyscribe.core.onboard_headless.ensure_app_dirs"):
                    result = onboard_headless.run_headless_onboard(install_skill=False, **kwargs)
                    from anyscribe.config.settings import load_config

                    return result, load_config()


def test_explicit_provider_persists_quality_custom(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    result, saved = _run_isolated(tmp_path, provider="deepgram", api_key="dg-key")
    assert saved.quality == "custom"
    assert saved.provider == "deepgram"
    assert result["quality"] == "custom"


def test_explicit_quality_flag_wins_over_custom(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    result, saved = _run_isolated(
        tmp_path, provider="openai", api_key="sk-test", quality="accuracy"
    )
    assert saved.quality == "accuracy"
    assert result["quality"] == "accuracy"


def test_unknown_quality_is_rejected_with_choices(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    with pytest.raises(onboard_headless.OnboardValidationError) as exc:
        onboard_headless.run_headless_onboard(provider="openai", api_key="sk-test", quality="turbo")
    assert "turbo" in exc.value.payload["error"]
    assert "balanced" in exc.value.payload["choices"]


def test_model_flag_persists_pin(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    result, saved = _run_isolated(tmp_path, provider="openai", api_key="sk-test", model="whisper-1")
    assert saved.provider_models["openai"] == "whisper-1"
    assert result["model"] == "whisper-1"


def test_no_model_flag_reports_catalog_default_without_pinning(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    result, saved = _run_isolated(tmp_path, provider="openai", api_key="sk-test")
    assert saved.provider_models == {}
    assert result["model"] == "gpt-transcribe"


def test_unknown_model_is_rejected_with_choices(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    with pytest.raises(onboard_headless.OnboardValidationError) as exc:
        onboard_headless.run_headless_onboard(provider="deepgram", api_key="dg-key", model="nova-9")
    assert "nova-9" in exc.value.payload["error"]
    assert exc.value.payload["choices"] == ["nova-3", "nova-2"]


def test_openrouter_accepts_any_model_slug(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    _, saved = _run_isolated(
        tmp_path, provider="openrouter", api_key="or-key", model="vendor/whatever"
    )
    assert saved.provider_models["openrouter"] == "vendor/whatever"


def test_local_provider_model_flag_points_at_local_model(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    with pytest.raises(onboard_headless.OnboardValidationError) as exc:
        onboard_headless.run_headless_onboard(
            provider="local", local_model="tiny", model="large-v3"
        )
    assert "--local-model" in exc.value.payload["hint"]


def test_onboarding_accepts_the_sarvam_spelling(tmp_path, monkeypatch):
    """Docs promise `sarvam` works "everywhere a provider name goes" — the
    onboarding validator has to honour that too, and persist the canonical
    name so PROVIDER_KEY_ENV lookups downstream don't KeyError."""
    monkeypatch.setenv("HOME", str(tmp_path))
    result, saved = _run_isolated(tmp_path, provider="sarvam", api_key="sv-key")
    assert result["provider"] == "sargam"
    assert saved.provider == "sargam"
    assert result["api_keys_set"] == ["SARGAM_API_KEY"]
