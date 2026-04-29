"""Headless onboarding — shared backend for CLI --yes mode and Web UI wizard.

The TUI `scribe onboard` wizard, the agentic `scribe onboard --yes ...` path,
and the Web UI onboarding wizard all converge on ``run_headless_onboard()``:
validate inputs, persist config + secrets, create the vault, optionally set up
local transcription, optionally install the Claude Code skill. One function,
structured input, structured output — no interactive prompts.

Design contract:

* Never prompts the user or reads stdin.
* Never prints anything (except via an optional ``on_progress`` callback).
* Returns a dict with ``status`` + ``details`` so callers can render results in
  whatever shape their surface needs (JSON, Rich summary, React component).
* Idempotent — safe to re-run. Existing config fields get overwritten; secrets
  are merged into ``.env`` alongside whatever's already there.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Callable

from anyscribecli.config.paths import (
    APP_HOME,
    CLAUDE_HOME,
    DEFAULT_WORKSPACE,
    ensure_app_dirs,
)
from anyscribecli.config.settings import (
    load_config,
    load_env,
    save_config,
    save_env,
)

# Maps provider → env var for its API key. Kept in sync with config_cmd.py and
# web/routes/config.py; extracting once more would be premature abstraction.
PROVIDER_KEY_ENV = {
    "openai": "OPENAI_API_KEY",
    "deepgram": "DEEPGRAM_API_KEY",
    "elevenlabs": "ELEVENLABS_API_KEY",
    "sargam": "SARGAM_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
}

API_PROVIDERS = set(PROVIDER_KEY_ENV.keys())
ALL_PROVIDERS = API_PROVIDERS | {"local"}

ProgressFn = Callable[[dict[str, Any]], None]


class OnboardValidationError(ValueError):
    """Raised when required onboarding inputs are missing or invalid.

    Carries a ``payload`` dict so CLI/web handlers can turn it into a
    structured error response without re-parsing the message.
    """

    def __init__(self, payload: dict[str, Any]):
        super().__init__(payload.get("error", "invalid onboarding input"))
        self.payload = payload


def _emit(on_progress: ProgressFn | None, event: dict[str, Any]) -> None:
    if on_progress is not None:
        try:
            on_progress(event)
        except Exception:
            pass


def _validate(
    provider: str,
    api_key: str | None,
    local_model: str | None,
    instagram_browser: str | None,
) -> None:
    """Raise OnboardValidationError if required fields for the chosen provider
    aren't present in either argv or the environment.
    """
    if provider not in ALL_PROVIDERS:
        raise OnboardValidationError(
            {
                "error": f"unknown provider '{provider}'",
                "choices": sorted(ALL_PROVIDERS),
            }
        )

    if provider == "local":
        # Local needs a model size. We don't validate the size string itself
        # here — local_setup.run_setup does that.
        if not local_model:
            from anyscribecli.providers.local_models import (
                MODEL_SIZES,
                RECOMMENDED_MODEL,
            )

            raise OnboardValidationError(
                {
                    "error": "--local-model is required when --provider=local",
                    "recommended": RECOMMENDED_MODEL,
                    "choices": list(MODEL_SIZES),
                }
            )
        return

    # API provider — need a key via arg or env.
    env_var = PROVIDER_KEY_ENV[provider]
    env_value = os.environ.get(env_var)
    if not api_key and not env_value:
        raise OnboardValidationError(
            {
                "error": f"api key required for provider '{provider}'",
                "env_var": env_var,
                "hint": f"pass --api-key or set {env_var}=... in the environment",
            }
        )

    # Validate Instagram browser if provided. Empty string is treated as
    # "no cookies (anonymous)" and is always valid.
    if instagram_browser:
        from anyscribecli.downloaders.instagram import SUPPORTED_BROWSERS

        normalized = instagram_browser.strip().lower()
        if normalized and normalized != "none" and normalized not in SUPPORTED_BROWSERS:
            raise OnboardValidationError(
                {
                    "error": f"unsupported instagram browser '{instagram_browser}'",
                    "choices": list(SUPPORTED_BROWSERS),
                    "hint": "Pass an empty string or 'none' to skip cookie configuration.",
                }
            )


def run_headless_onboard(
    provider: str,
    *,
    api_key: str | None = None,
    workspace: str | None = None,
    language: str | None = None,
    keep_media: bool | None = None,
    output_format: str | None = None,
    local_model: str | None = None,
    extra_api_keys: dict[str, str] | None = None,
    instagram_browser: str | None = None,
    install_skill: bool = True,
    on_progress: ProgressFn | None = None,
) -> dict[str, Any]:
    """Run onboarding end-to-end without prompting. Returns a structured result.

    All inputs except ``provider`` are optional; missing ones fall back to
    defaults from ``Settings()``. Environment variables are read for API keys
    when ``api_key`` isn't passed explicitly.

    Returns
    -------
    ``{status, provider, workspace, local_enabled, api_keys_set, skill_installed,
       local_setup?: {...}}``. ``status`` is ``"onboarded"`` on success; if
    local setup was requested and failed, status is ``"partial"`` and the
    ``local_setup`` payload carries the failure detail.
    """
    _validate(provider, api_key, local_model, instagram_browser)
    _emit(on_progress, {"event": "validated", "provider": provider})

    # Load existing env so save_env merges rather than replaces. ensure_app_dirs
    # creates ~/.anyscribecli and its children.
    load_env()
    ensure_app_dirs()

    # Merge settings from current config (or defaults if none), overlaying what
    # was passed.
    settings = load_config()
    settings.provider = provider
    if language is not None:
        settings.language = language
    if keep_media is not None:
        settings.keep_media = keep_media
    if output_format is not None:
        settings.output_format = output_format
    if workspace is not None:
        resolved = Path(workspace).expanduser()
        settings.workspace_path = "" if resolved == DEFAULT_WORKSPACE else str(resolved)
    if local_model is not None:
        settings.local_model = local_model
    if instagram_browser is not None:
        settings.instagram.browser = instagram_browser

    save_config(settings)
    _emit(on_progress, {"event": "config_saved"})

    # Collect secrets to write to .env. Skip empty values and skip the provider
    # key if it's already set in the environment (user already has it).
    env_keys: dict[str, str] = {}
    if provider in API_PROVIDERS and api_key:
        env_keys[PROVIDER_KEY_ENV[provider]] = api_key
    if extra_api_keys:
        for name, key in extra_api_keys.items():
            env_var = PROVIDER_KEY_ENV.get(name)
            if env_var and key:
                env_keys[env_var] = key
    if env_keys:
        save_env(env_keys)
        # Also update the current process env so downstream calls (e.g., local
        # setup) see the new keys immediately.
        for k, v in env_keys.items():
            os.environ[k] = v
        _emit(on_progress, {"event": "secrets_saved", "keys": list(env_keys.keys())})

    # Vault — created if missing. maybe_migrate_workspace handles legacy paths.
    from anyscribecli.core.migrate import maybe_migrate_workspace
    from anyscribecli.vault.scaffold import create_vault

    maybe_migrate_workspace()
    vault_path = create_vault()
    _emit(on_progress, {"event": "vault_created", "path": str(vault_path)})

    # Optional: install the Claude Code skill. Silent best-effort — skill
    # install failures should never break onboarding.
    skill_installed = False
    if install_skill and CLAUDE_HOME.exists():
        try:
            from anyscribecli.cli.skill_cmd import copy_skill_files

            copy_skill_files(quiet=True)
            skill_installed = True
            _emit(on_progress, {"event": "skill_installed"})
        except Exception:
            pass

    # Optional: set up local transcription. Only when provider == "local" (user
    # explicitly picked it) — the "opt-in alongside API provider" path is a
    # different codepath in the Web UI wizard that calls run_setup() directly.
    local_setup_result: dict[str, Any] | None = None
    status = "onboarded"
    if provider == "local":
        from anyscribecli.core.local_setup import run_setup as run_local_setup

        _emit(on_progress, {"event": "local_setup_starting", "size": local_model})
        local_setup_result = run_local_setup(local_model, on_progress=on_progress)
        if local_setup_result.get("status") == "failed":
            status = "partial"

    return {
        "status": status,
        "provider": provider,
        "workspace": str(vault_path),
        "local_enabled": provider == "local"
        and (local_setup_result or {}).get("status") != "failed",
        "api_keys_set": sorted(env_keys.keys()),
        "skill_installed": skill_installed,
        "local_setup": local_setup_result,
        "config_file": str(APP_HOME / "config.yaml"),
    }
