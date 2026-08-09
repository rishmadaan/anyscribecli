"""Transcription provider registry."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from anyscribe.providers.base import TranscriptionProvider

# Maps provider name -> module path, class name (lazy import to avoid loading all deps)
PROVIDER_REGISTRY: dict[str, tuple[str, str]] = {
    "openai": ("anyscribe.providers.openai", "OpenAIProvider"),
    "openrouter": ("anyscribe.providers.openrouter", "OpenRouterProvider"),
    "elevenlabs": ("anyscribe.providers.elevenlabs", "ElevenLabsProvider"),
    "sargam": ("anyscribe.providers.sargam", "SargamProvider"),
    "deepgram": ("anyscribe.providers.deepgram", "DeepgramProvider"),
    "groq": ("anyscribe.providers.groq", "GroqProvider"),
    "local": ("anyscribe.providers.local", "LocalProvider"),
}

# Canonical provider -> env var holding its API key (None = no key needed).
# Single source of truth — every other map (web, cli, mcp, preflight,
# onboarding, quality) imports or derives from this. Was hand-copied in
# 7 places and drifted twice (groq went missing from preflight + mcp).
PROVIDER_KEY_ENV: dict[str, str | None] = {
    "openai": "OPENAI_API_KEY",
    "deepgram": "DEEPGRAM_API_KEY",
    "elevenlabs": "ELEVENLABS_API_KEY",
    "sargam": "SARGAM_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
    "groq": "GROQ_API_KEY",
    "local": None,
}

# Canonical provider -> pickable model ids. First entry is the provider's
# default; a single-entry list means "no picker" (UI hides the dropdown).
# "local" is empty because local model choice lives in settings.local_model
# with its own download/cache lifecycle (anyscribe model pull, Web UI cards).
# Verified against provider docs 2026-07-29 — see journal entry of that date.
PROVIDER_MODELS: dict[str, list[str]] = {
    "openai": ["gpt-transcribe", "whisper-1", "gpt-4o-transcribe", "gpt-4o-mini-transcribe"],
    "deepgram": ["nova-3", "nova-2"],
    "elevenlabs": ["scribe_v2"],
    "sargam": ["saaras:v3"],
    "openrouter": [
        "openai/gpt-audio-mini",
        "google/gemini-2.5-flash-lite",
        "google/gemini-2.5-flash",
        "google/gemini-3-flash-preview",
        "mistralai/voxtral-small-24b-2507",
        "openai/gpt-audio",
    ],
    "groq": ["whisper-large-v3-turbo", "whisper-large-v3"],
    "local": [],
}

# Providers whose model list is open-ended (any slug the service accepts is
# valid), so a pinned model outside PROVIDER_MODELS is allowed through.
# This is also why `get_provider` needs no extra_models knowledge: user-added
# slugs (settings.extra_models) exist only for openrouter, already open here.
OPEN_MODEL_PROVIDERS = {"openrouter"}


def get_models(name: str, extra_models: dict[str, list[str]] | None = None) -> list[str]:
    """Pickable models for `name`: the catalog plus user-added slugs.

    Order is preserved (catalog first, extras in the order the user added
    them) and duplicates are dropped, so callers can keep treating index 0 as
    the provider's default.
    """
    models = PROVIDER_MODELS.get(name, [])
    extra = (extra_models or {}).get(name) or []
    return models + [m for m in dict.fromkeys(extra) if m not in models]


def validate_model(name: str, model: str, extra_models: dict[str, list[str]] | None = None) -> None:
    """Raise ValueError if `model` isn't pickable for `name`. Open providers accept anything."""
    if name in OPEN_MODEL_PROVIDERS:
        return
    known = get_models(name, extra_models)
    if not known:
        hint = (
            " Local model choice uses `anyscribe local setup --model` / settings.local_model."
            if name == "local"
            else ""
        )
        raise ValueError(f"Provider '{name}' does not support model selection.{hint}")
    if model not in known:
        raise ValueError(
            f"Unknown model '{model}' for provider '{name}'. Available: {', '.join(known)}"
        )


def get_provider(name: str, model: str | None = None) -> TranscriptionProvider:
    """Get an instantiated provider by name, optionally pinned to a model."""
    if name not in PROVIDER_REGISTRY:
        available = ", ".join(sorted(PROVIDER_REGISTRY.keys()))
        raise ValueError(f"Unknown provider '{name}'. Available: {available}")

    module_path, class_name = PROVIDER_REGISTRY[name]
    import importlib

    module = importlib.import_module(module_path)
    provider_class = getattr(module, class_name)
    provider = provider_class()
    if model:
        validate_model(name, model)
        provider.model = model
    return provider


def list_providers() -> list[str]:
    """List all registered provider names."""
    return sorted(PROVIDER_REGISTRY.keys())
