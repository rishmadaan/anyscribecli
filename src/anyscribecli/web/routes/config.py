"""Configuration and provider endpoints."""

from __future__ import annotations

import os

from fastapi import APIRouter

from anyscribecli.config.paths import get_workspace_dir
from anyscribecli.config.settings import load_config, load_env, save_config, save_env
from anyscribecli.providers import PROVIDER_REGISTRY, list_providers
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
            }
        )
    return result


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

    return {"success": True, "message": f"API key is set for {name}"}


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
