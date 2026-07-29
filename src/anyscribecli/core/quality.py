"""Quality presets — map an accuracy↔cost tier to a transcription provider.

`quality` is a friendly knob that resolves to a provider. Each tier maps to a
distinct provider whose own default model is right for that tier; a pinned
model in `settings.provider_models` (or `--model`) rides on top of whichever
provider wins. The tier is applied by `core/resolve.py`, which owns the whole
provider ladder (flag > diarize > tier > config).

`quality = "custom"` is the sentinel for "respect `settings.provider`": it is
not a tier, so `apply_quality` finds no target and leaves the provider alone.
Setting a provider anywhere writes `quality = "custom"` in the same write, so
the choice sticks instead of being overridden by a tier on the next run.
"""

from __future__ import annotations

import os

from anyscribecli.providers import PROVIDER_KEY_ENV

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


def has_key(provider: str) -> bool:
    """True if the provider needs no key, or its key is set in the environment."""
    env = PROVIDER_KEY_ENV.get(provider)
    return env is None or bool(os.environ.get(env))
