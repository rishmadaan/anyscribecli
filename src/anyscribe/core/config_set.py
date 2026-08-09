"""The single validated write path for settings — CLI, Web UI and MCP all use it.

Every surface used to hand-roll its own coercion and validation, which is how
`provider` could be written without `quality = "custom"` on one path and with it
on another. `set_value` owns both the validation tables and the invariants; the
callers only render the `SetOutcome`.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from anyscribe.config.paths import ENV_FILE
from anyscribe.config.settings import Settings, load_config, save_config, save_env
from anyscribe.providers import (
    OPEN_MODEL_PROVIDERS,
    PROVIDER_KEY_ENV,
    PROVIDER_REGISTRY,
    get_models,
)
from anyscribe.providers.local_models import MODEL_SIZES

# "openai_api_key" -> "OPENAI_API_KEY", for `anyscribe config set <x>_api_key`
API_KEY_MAP: dict[str, str] = {
    f"{name}_api_key": env for name, env in PROVIDER_KEY_ENV.items() if env
}

# Scalar settings with a closed set of values.
ENUMS: dict[str, list[str]] = {
    "provider": sorted(PROVIDER_REGISTRY),
    "quality": ["accuracy", "balanced", "cost", "free", "custom"],
    "output_format": ["clean", "timestamped", "diarized"],
    "prompt_download": ["never", "always", "ask"],
    "local_file_media": ["skip", "copy", "move", "ask"],
    "local_model": MODEL_SIZES,
}

_TRUTHY = ("true", "1", "yes", "on")


@dataclass
class SetOutcome:
    ok: bool
    message: str = ""
    error: str | None = None
    choices: list[str] | None = None


class _Invalid(Exception):
    """Internal — carried up to `set_value` and rendered as a failed outcome."""

    def __init__(self, error: str, choices: list[str] | None = None) -> None:
        super().__init__(error)
        self.error = error
        self.choices = choices


def _flat_keys(d: dict, prefix: str = "") -> list[str]:
    """Flatten a settings dict into dot-notation keys."""
    keys = []
    for k, v in d.items():
        full = f"{prefix}{k}" if not prefix else f"{prefix}.{k}"
        if isinstance(v, dict):
            keys.extend(_flat_keys(v, full))
        else:
            keys.append(full)
    return keys


def valid_keys() -> list[str]:
    """Every key `set_value` accepts, for error messages and `list-keys`."""
    return sorted(
        _flat_keys(Settings().to_dict())
        + ["provider_models.<provider>", "extra_models.openrouter"]
        + list(API_KEY_MAP)
    )


def set_value(key: str, value) -> SetOutcome:
    """Validate and persist one setting. Never raises — see `SetOutcome.error`."""
    key = str(key).strip()
    env_var = API_KEY_MAP.get(key.lower().replace("-", "_"))
    if env_var:
        save_env({env_var: str(value)})
        os.environ[env_var] = str(value)
        return SetOutcome(True, f"Saved {env_var} to {ENV_FILE}")

    data = load_config().to_dict()
    field, _, sub = key.partition(".")
    try:
        if field in ("provider_models", "extra_models"):
            message = _set_models(field, sub, value, data)
        elif key in ENUMS:
            message = _set_enum(key, value, data)
        else:
            message = _set_scalar(key, value, data)
    except _Invalid as e:
        return SetOutcome(False, error=e.error, choices=e.choices)

    save_config(Settings.from_dict(data))
    return SetOutcome(True, message)


def _set_enum(key: str, value, data: dict) -> str:
    choices = ENUMS[key]
    v = str(value).strip()
    if v not in choices:
        raise _Invalid(f"Invalid value for {key}: {v}", choices)
    data[key] = v
    if key == "provider":
        # The invariant: an explicit provider choice must survive the next run,
        # so it always lands together with the "custom" tier.
        data["quality"] = "custom"
        return f"Set provider = {v} (quality = custom, so this choice sticks)"
    return f"Set {key} = {v}"


def _set_scalar(key: str, value, data: dict) -> str:
    target = data
    keys = key.split(".")
    for k in keys[:-1]:
        if not isinstance(target.get(k), dict):
            raise _Invalid(f"Unknown key: {key}", valid_keys())
        target = target[k]
    final = keys[-1]
    if final not in target or isinstance(target[final], (dict, list)):
        raise _Invalid(f"Unknown key: {key}", valid_keys())

    if isinstance(target[final], bool):
        typed = value if isinstance(value, bool) else str(value).strip().lower() in _TRUTHY
    else:
        typed = str(value)
        if key == "workspace_path" and typed:
            typed = str(Path(typed).expanduser())
    target[final] = typed
    return f"Set {key} = {typed}"


def _set_models(field: str, sub: str, value, data: dict) -> str:
    """Write `provider_models` / `extra_models`, per-entry or whole-dict."""
    if isinstance(value, dict):
        entries, replace = value, True
    elif sub:
        entries, replace = {sub: value}, False
    else:
        raise _Invalid(f"Use {field}.<provider> <value>")

    cleaned: dict = {}
    for prov, v in entries.items():
        if field == "provider_models":
            cleaned[prov] = _check_pin(prov, v, data["extra_models"])
        else:
            slugs = _check_extras(prov, v)
            if slugs:  # empty value clears the entry
                cleaned[prov] = slugs

    if replace:
        data[field] = cleaned
        return f"Set {field}"
    data[field].update(cleaned)
    for prov in entries:
        if prov not in cleaned:
            data[field].pop(prov, None)
    return f"Set {field}.{sub} = {cleaned.get(sub, '')}"


def _check_pin(provider: str, value, extra_models: dict) -> str:
    if provider not in PROVIDER_REGISTRY:
        raise _Invalid(f"Unknown provider: {provider}", sorted(PROVIDER_REGISTRY))
    known = get_models(provider, extra_models)
    if not known:
        hint = (
            " Local model choice uses `anyscribe local setup --model` / settings.local_model."
            if provider == "local"
            else ""
        )
        raise _Invalid(f"No pickable models for provider: {provider}.{hint}")
    model = str(value).strip()
    if model not in known and provider not in OPEN_MODEL_PROVIDERS:
        raise _Invalid(f"Unknown model '{model}' for {provider}.", known)
    return model


def _check_extras(provider: str, value) -> list[str]:
    if provider != "openrouter":
        raise _Invalid("custom models are only supported for openrouter (curated lists elsewhere)")
    items = value if isinstance(value, list) else str(value).split(",")
    return list(dict.fromkeys(str(s).strip() for s in items if str(s).strip()))
