"""Configuration and provider endpoints."""

from __future__ import annotations

import os

import httpx
from fastapi import APIRouter, Body
from fastapi.responses import JSONResponse

from anyscribe.config.paths import get_workspace_dir
from anyscribe.config.settings import (
    delete_env,
    env_file_keys,
    forget_env_var,
    load_config,
    load_env,
    save_env,
)
from anyscribe.core.config_set import set_value
from anyscribe.core.local_setup import local_ready
from anyscribe.core.quality import QUALITY_TIERS
from anyscribe.providers import (
    OPEN_MODEL_PROVIDERS,
    PROVIDER_KEY_ENV,
    PROVIDER_REGISTRY,
    get_models,
    list_providers,
)
from anyscribe.providers.languages import PROVIDER_LANGUAGES
from anyscribe.providers.local_models import (
    faster_whisper_importable,
    faster_whisper_version,
    is_cached,
)
from anyscribe.web.models import ConfigUpdateRequest, KeyUpdateRequest

router = APIRouter(prefix="/api", tags=["config"])

# Provider descriptions for the UI
PROVIDER_INFO: dict[str, str] = {
    "openai": "General purpose, multilingual, segment timestamps",
    "deepgram": "Fast, accurate, native diarization + Hindi Latin support",
    "elevenlabs": "High accuracy, 99 languages, word-level timestamps",
    "sargam": "Optimized for Indic languages (Hindi, Tamil, Telugu, etc.)",
    "openrouter": "Access various models via unified API",
    "groq": "Cheapest + fastest cloud Whisper (large-v3-turbo)",
    "local": "Offline, free, runs on your machine (requires faster-whisper)",
}

# Maps provider name -> env var for its API key (API providers only)
PROVIDER_KEY_MAP: dict[str, str] = {k: v for k, v in PROVIDER_KEY_ENV.items() if v}

# URLs where users can obtain API keys
PROVIDER_SIGNUP_URLS: dict[str, str] = {
    "openai": "https://platform.openai.com/api-keys",
    "deepgram": "https://console.deepgram.com/",
    "elevenlabs": "https://elevenlabs.io/app/settings/api-keys",
    "sargam": "https://dashboard.sarvam.ai",
    "openrouter": "https://openrouter.ai/keys",
    "groq": "https://console.groq.com/keys",
}


def _config_payload() -> dict:
    """Config as the UI wants it: settings plus read-only context (leading _)."""
    load_env()
    settings = load_config()
    data = settings.to_dict()
    data["_resolved_workspace"] = str(get_workspace_dir())
    # Tier -> provider, so the UI can caption each quality choice with what it
    # actually resolves to instead of hardcoding a second copy of the map.
    data["_quality_tiers"] = QUALITY_TIERS
    # What the next run will actually use — the Settings page leads with this,
    # mirroring the CLI dashboard. Guarded: a hand-edited config with a bogus
    # provider must not take the whole settings page down.
    from anyscribe.core.resolve import resolve_run

    try:
        plan = resolve_run(settings)
        data["_resolved"] = {
            "provider": plan.provider,
            "model": plan.model,
            "via": plan.via,
            "notes": plan.notes,
        }
    except ValueError as e:
        data["_resolved"] = {"error": str(e)}
    return data


@router.get("/config")
async def get_config() -> dict:
    return _config_payload()


@router.put("/config")
async def update_config(req: ConfigUpdateRequest):
    from anyscribe.config.paths import CONFIG_FILE

    # set_value persists per field; snapshot config.yaml so a mixed
    # valid+invalid payload rolls back instead of half-committing (a 422
    # must mean "nothing was saved").
    snapshot = CONFIG_FILE.read_bytes() if CONFIG_FILE.exists() else None
    for field_name, value in req.model_dump(exclude_unset=True).items():
        if value is None:
            continue
        if field_name == "instagram" and isinstance(value, dict):
            # Nested block -> dotted keys, the shape set_value speaks.
            outcomes = [set_value(f"instagram.{k}", v) for k, v in value.items()]
            outcome = next((o for o in outcomes if not o.ok), None)
            if outcome is None:
                continue
        else:
            outcome = set_value(field_name, value)
        if not outcome.ok:
            if snapshot is not None:
                CONFIG_FILE.write_bytes(snapshot)
            elif CONFIG_FILE.exists():
                CONFIG_FILE.unlink()
            return JSONResponse(
                status_code=422,
                content={"success": False, "error": outcome.error, "choices": outcome.choices},
            )
    return _config_payload()


@router.get("/providers")
async def get_providers() -> list[dict]:
    load_env()
    extra_models = load_config().extra_models
    result = []
    local_is_ready = local_ready()
    persisted = env_file_keys()  # keys actually saved in .env (vs inherited env)
    for name in list_providers():
        env_var = PROVIDER_KEY_MAP.get(name)
        if name == "local":
            # "available" for local means faster-whisper + ffmpeg + at least
            # one model cached. Before setup, the UI shows a CTA button instead
            # of a Test button — driven by set_up=False.
            has_key = local_is_ready
            set_up = local_is_ready
            key_in_env_file = False
        else:
            has_key = bool(os.environ.get(env_var)) if env_var else False
            set_up = True  # API providers have no separate setup step
            # Only .env-persisted keys are removable; a key inherited from the
            # parent shell can't be durably deleted, so the UI hides "Remove".
            key_in_env_file = bool(env_var and env_var in persisted)
        result.append(
            {
                "name": name,
                "description": PROVIDER_INFO.get(name, ""),
                "has_key": has_key,
                "set_up": set_up,
                "key_in_env_file": key_in_env_file,
                "key_url": PROVIDER_SIGNUP_URLS.get(name),
                # Pickable models (catalog + user-added slugs); first is the
                # default. Empty for "local" (its model choice lives in
                # local_model + the model cards).
                "models": get_models(name, extra_models),
                "freeform_model": name in OPEN_MODEL_PROVIDERS,
            }
        )
    return result


@router.get("/providers/{name}/languages")
async def get_provider_languages(name: str) -> dict:
    """Return the supported-language list for a provider.

    `freeform=true` means there is no canonical list and the caller should
    render a plain text input (currently OpenRouter only).
    """
    if name not in PROVIDER_LANGUAGES:
        return {"languages": [], "freeform": False}
    langs = PROVIDER_LANGUAGES[name]
    if langs is None:
        return {"languages": [], "freeform": True}
    # Strip internal-only keys (e.g. "model" for Deepgram routing) — UI only
    # needs code + name.
    return {
        "languages": [{"code": e["code"], "name": e["name"]} for e in langs],
        "freeform": False,
    }


@router.post("/providers/{name}/test")
async def test_provider(
    name: str,
    body: dict | None = Body(default=None),
) -> dict:
    """Validate a provider's API key.

    If the request body carries ``{"api_key": "..."}``, that key is validated
    directly without touching ``.env`` or ``os.environ`` — lets the Web UI
    wizard test a key the user just typed but hasn't yet saved. Without a
    body, falls back to the key stored in the environment (original behaviour
    for existing UI callers and agents).
    """
    load_env()
    if name not in PROVIDER_REGISTRY:
        return {"success": False, "message": f"Unknown provider: {name}"}

    env_var = PROVIDER_KEY_MAP.get(name)
    override_key = (body or {}).get("api_key") if isinstance(body, dict) else None
    effective_key = override_key or (os.environ.get(env_var) if env_var else None)

    if env_var and not effective_key:
        return {"success": False, "message": f"API key not set ({env_var})"}

    if name == "local":
        # Three structured checks: faster-whisper installed, ffmpeg on PATH,
        # and the currently-selected default model cached. UI renders each sub-
        # check; top-level success is the AND.
        from anyscribe.core.deps import check_dependencies

        settings = load_config()
        default_size = settings.local_model or "base"

        fw_ok = faster_whisper_importable()
        fw_version = faster_whisper_version()
        fw_check = {
            "ok": fw_ok,
            "message": (
                f"faster-whisper {fw_version}" if fw_version else "faster-whisper not installed"
            ),
        }

        ffmpeg_ok = False
        ffmpeg_msg = "ffmpeg not found on PATH"
        for r in check_dependencies():
            if r.dep.name == "ffmpeg":
                ffmpeg_ok = bool(r.found)
                ffmpeg_msg = r.version or ("ffmpeg found" if r.found else ffmpeg_msg)
                break
        ffmpeg_check = {"ok": ffmpeg_ok, "message": ffmpeg_msg}

        model_ok = fw_ok and is_cached(default_size)
        model_check = {
            "ok": model_ok,
            "message": (
                f"{default_size} model cached"
                if model_ok
                else f"{default_size} model not cached — run `anyscribe local setup --model {default_size}`"
            ),
            "size": default_size,
        }

        checks = {
            "faster_whisper": fw_check,
            "ffmpeg": ffmpeg_check,
            "model_cached": model_check,
        }
        all_ok = fw_check["ok"] and ffmpeg_check["ok"] and model_check["ok"]
        return {
            "success": all_ok,
            "message": (
                "all checks passed"
                if all_ok
                else next(
                    (c["message"] for c in checks.values() if not c["ok"]),
                    "check failed",
                )
            ),
            "checks": checks,
        }

    # Real validation: make a lightweight API call to verify the key works.
    # Use the override key from the request body if present, else the env var.
    api_key = effective_key  # type: ignore[assignment]
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            if name == "openai":
                r = await client.get(
                    "https://api.openai.com/v1/models",
                    headers={"Authorization": f"Bearer {api_key}"},
                )
            elif name == "deepgram":
                r = await client.get(
                    "https://api.deepgram.com/v1/projects",
                    headers={"Authorization": f"Token {api_key}"},
                )
            elif name == "elevenlabs":
                r = await client.get(
                    "https://api.elevenlabs.io/v1/user",
                    headers={"xi-api-key": api_key},
                )
            elif name == "openrouter":
                r = await client.get(
                    "https://openrouter.ai/api/v1/models",
                    headers={"Authorization": f"Bearer {api_key}"},
                )
            elif name == "sargam":
                return {"success": True, "message": "API key is set (no validation endpoint)"}
            else:
                return {"success": True, "message": f"API key is set for {name}"}

            if r.status_code < 400:
                return {"success": True, "message": f"API key is valid for {name}"}
            else:
                return {
                    "success": False,
                    "message": f"API returned {r.status_code} — key may be invalid",
                }
    except httpx.TimeoutException:
        return {"success": False, "message": "Validation request timed out"}
    except Exception as e:
        return {"success": False, "message": f"Validation failed: {e}"}


@router.get("/keys/status")
async def keys_status() -> dict:
    load_env()
    status = {name: bool(os.environ.get(env_var)) for name, env_var in PROVIDER_KEY_MAP.items()}
    # local needs no key — count it as configured when faster-whisper is installed
    status["local"] = faster_whisper_importable()
    return status


@router.put("/keys")
async def update_key(req: KeyUpdateRequest) -> dict:
    env_var = PROVIDER_KEY_MAP.get(req.provider_name)
    if not env_var:
        return {"success": False, "message": f"No API key for provider: {req.provider_name}"}
    save_env({env_var: req.api_key})
    os.environ[env_var] = req.api_key
    return {"success": True}


@router.delete("/keys/{provider_name}")
async def delete_key(provider_name: str) -> dict:
    """Remove a provider's saved API key from .env and the live environment."""
    env_var = PROVIDER_KEY_MAP.get(provider_name)
    if not env_var:
        return {"success": False, "message": f"No API key for provider: {provider_name}"}
    delete_env([env_var])
    # Drop it from the live process env, but keep any value inherited from the
    # parent shell — deleting our saved copy must not disable a shell-set key.
    forget_env_var(env_var)
    return {"success": True}
