"""Transcription provider registry."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from anyscribecli.providers.base import TranscriptionProvider

# Maps provider name -> module path, class name (lazy import to avoid loading all deps)
PROVIDER_REGISTRY: dict[str, tuple[str, str]] = {
    "openai": ("anyscribecli.providers.openai", "OpenAIProvider"),
    "openrouter": ("anyscribecli.providers.openrouter", "OpenRouterProvider"),
    "elevenlabs": ("anyscribecli.providers.elevenlabs", "ElevenLabsProvider"),
    "sargam": ("anyscribecli.providers.sargam", "SargamProvider"),
    "deepgram": ("anyscribecli.providers.deepgram", "DeepgramProvider"),
    "local": ("anyscribecli.providers.local", "LocalProvider"),
}


def get_provider(name: str) -> TranscriptionProvider:
    """Get an instantiated provider by name."""
    if name not in PROVIDER_REGISTRY:
        available = ", ".join(sorted(PROVIDER_REGISTRY.keys()))
        raise ValueError(f"Unknown provider '{name}'. Available: {available}")

    module_path, class_name = PROVIDER_REGISTRY[name]
    import importlib

    module = importlib.import_module(module_path)
    provider_class = getattr(module, class_name)
    return provider_class()


def list_providers() -> list[str]:
    """List all registered provider names."""
    return sorted(PROVIDER_REGISTRY.keys())
