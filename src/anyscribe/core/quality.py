"""Quality presets — map an accuracy↔cost tier to a transcription provider.

`quality` is a friendly knob that resolves to a provider. Each tier maps to a
distinct provider whose own default model is right for that tier, so there is no
per-provider model-override machinery. Resolution mirrors the `--diarize →
deepgram` auto-routing in `cli/transcribe.py`.
"""

from __future__ import annotations

import os

from anyscribe.config.settings import Settings
from anyscribe.providers import PROVIDER_KEY_ENV

# tier -> provider. The provider's own default model is correct for the tier:
#   accuracy → elevenlabs scribe_v2 (top WER, best for primarily-English)
#   balanced → deepgram nova-3 (native diarization, no chunking, hi-Latn path)
#   cost     → groq whisper-large-v3-turbo (cheapest + fastest cloud)
#   free     → local faster-whisper (offline, $0)
QUALITY_TIERS: dict[str, str] = {
    "accuracy": "elevenlabs",
    "balanced": "deepgram",
    "cost": "groq",
    "free": "local",
}


def _has_key(provider: str) -> bool:
    """True if the provider needs no key, or its key is set in the environment."""
    env = PROVIDER_KEY_ENV.get(provider)
    return env is None or bool(os.environ.get(env))


def apply_quality(settings: Settings, explicit_provider: bool) -> None:
    """Resolve `settings.quality` into `settings.provider`, in place.

    No-op when the user explicitly chose a provider. If the tier's provider has
    no API key configured, keep the configured provider (graceful fallback) so a
    keyless user still works out of the box.
    """
    if explicit_provider:
        return
    target = QUALITY_TIERS.get(settings.quality)
    if target and _has_key(target):
        settings.provider = target
    # unknown tier or missing key → leave settings.provider unchanged
