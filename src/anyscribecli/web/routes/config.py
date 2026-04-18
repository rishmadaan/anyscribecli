"""Configuration and provider endpoints."""

from __future__ import annotations

import os

import httpx
from fastapi import APIRouter

from anyscribecli.config.paths import get_workspace_dir
from anyscribecli.config.settings import load_config, load_env, save_config, save_env
from anyscribecli.providers import PROVIDER_REGISTRY, list_providers
from anyscribecli.providers.languages import PROVIDER_LANGUAGES
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
    for name in list_providers():
        env_var = PROVIDER_KEY_MAP.get(name)
        has_key = bool(os.environ.get(env_var)) if env_var else (name == "local")
        result.append(
            {
                "name": name,
                "description": PROVIDER_INFO.get(name, ""),
                "has_key": has_key,
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
async def test_provider(name: str) -> dict:
    load_env()
    if name not in PROVIDER_REGISTRY:
        return {"success": False, "message": f"Unknown provider: {name}"}

    env_var = PROVIDER_KEY_MAP.get(name)
    if env_var and not os.environ.get(env_var):
        return {"success": False, "message": f"API key not set ({env_var})"}

    if name == "local":
        try:
            import faster_whisper  # noqa: F401

            return {"success": True, "message": "faster-whisper is installed"}
        except ImportError:
            return {"success": False, "message": "faster-whisper not installed"}

    # Real validation: make a lightweight API call to verify the key works
    api_key = os.environ[env_var]
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
                return {"success": False, "message": f"API returned {r.status_code} — key may be invalid"}
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
