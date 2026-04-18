"""Configuration and provider endpoints."""

from __future__ import annotations

import os

import httpx
from fastapi import APIRouter, Body

from anyscribecli.config.paths import get_workspace_dir
from anyscribecli.config.settings import load_config, load_env, save_config, save_env
from anyscribecli.core.local_setup import local_ready
from anyscribecli.providers import PROVIDER_REGISTRY, list_providers
from anyscribecli.providers.languages import PROVIDER_LANGUAGES
from anyscribecli.providers.local_models import (
    faster_whisper_importable,
    faster_whisper_version,
    is_cached,
)
from anyscribecli.web.models import ConfigUpdateRequest, KeyUpdateRequest

router = APIRouter(prefix="/api", tags=["config"])

# Provider descriptions for the UI
PROVIDER_INFO: dict[str, str] = {
    "openai": "General purpose, multilingual, segment timestamps",
    "deepgram": "Fast, accurate, native diarization + Hindi Latin support",
    "elevenlabs": "High accuracy, 99 languages, word-level timestamps",
    "sargam": "Optimized for Indic languages (Hindi, Tamil, Telugu, etc.)",
    "openrouter": "Access various models via unified API",
    "local": "Offline, free, runs on your machine (requires faster-whisper)",
}

# Maps provider name -> env var for its API key
PROVIDER_KEY_MAP: dict[str, str] = {
    "openai": "OPENAI_API_KEY",
    "deepgram": "DEEPGRAM_API_KEY",
    "elevenlabs": "ELEVENLABS_API_KEY",
    "sargam": "SARGAM_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
}

# URLs where users can obtain API keys
PROVIDER_SIGNUP_URLS: dict[str, str] = {
    "openai": "https://platform.openai.com/api-keys",
    "deepgram": "https://console.deepgram.com/",
    "elevenlabs": "https://elevenlabs.io/app/settings/api-keys",
    "sargam": "https://dashboard.sarvam.ai",
    "openrouter": "https://openrouter.ai/keys",
}


@router.get("/config")
async def get_config() -> dict:
    settings = load_config()
    data = settings.to_dict()
    data["_resolved_workspace"] = str(get_workspace_dir())
    return data


@router.put("/config")
async def update_config(req: ConfigUpdateRequest) -> dict:
    settings = load_config()
    for field_name, value in req.model_dump(exclude_unset=True).items():
        if hasattr(settings, field_name):
            setattr(settings, field_name, value)
    save_config(settings)
    updated = settings.to_dict()
    updated["_resolved_workspace"] = str(get_workspace_dir())
    return updated


@router.get("/providers")
async def get_providers() -> list[dict]:
    load_env()
    result = []
    local_is_ready = local_ready()
    for name in list_providers():
        env_var = PROVIDER_KEY_MAP.get(name)
        if name == "local":
            # "available" for local means faster-whisper + ffmpeg + at least
            # one model cached. Before setup, the UI shows a CTA button instead
            # of a Test button — driven by set_up=False.
            has_key = local_is_ready
            set_up = local_is_ready
        else:
            has_key = bool(os.environ.get(env_var)) if env_var else False
            set_up = True  # API providers have no separate setup step
        result.append(
            {
                "name": name,
                "description": PROVIDER_INFO.get(name, ""),
                "has_key": has_key,
                "set_up": set_up,
                "key_url": PROVIDER_SIGNUP_URLS.get(name),
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
        from anyscribecli.core.deps import check_dependencies

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
                else f"{default_size} model not cached — run `scribe local setup --model {default_size}`"
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
    return {name: bool(os.environ.get(env_var)) for name, env_var in PROVIDER_KEY_MAP.items()}


@router.put("/keys")
async def update_key(req: KeyUpdateRequest) -> dict:
    env_var = PROVIDER_KEY_MAP.get(req.provider_name)
    if not env_var:
        return {"success": False, "message": f"No API key for provider: {req.provider_name}"}
    save_env({env_var: req.api_key})
    os.environ[env_var] = req.api_key
    return {"success": True}
