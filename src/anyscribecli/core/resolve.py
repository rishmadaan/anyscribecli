"""One place that answers "which provider and model does this run use?".

The CLI, batch, Web UI and MCP each used to inline the same ladder — flag >
diarize auto-route > quality tier > config — and each inlined a different
subset of it, so a swap that was visible on one surface was silent on
another. `resolve_run` owns the ladder and hands back the notes every surface
prints, which is also how the previously-silent fallbacks (keyless quality
tier, timestamp-incapable OpenAI model) became visible.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field

from anyscribecli.config.settings import Settings
from anyscribecli.core.quality import QUALITY_TIERS, has_key
from anyscribecli.providers import PROVIDER_KEY_ENV, get_models, validate_model
from anyscribecli.providers.openai import OpenAIProvider

# output formats that need per-segment timestamps from the provider
_TIMED_FORMATS = {"timestamped", "diarized"}


@dataclass
class RunPlan:
    provider: str
    model: str | None
    via: str  # "flag" | "diarize" | "quality: <tier>" | "config"
    notes: list[str] = field(default_factory=list)


def resolve_run(
    settings: Settings,
    *,
    cli_provider: str | None = None,
    cli_model: str | None = None,
    diarize: bool = False,
) -> RunPlan:
    """Resolve the provider + model for one run. Raises ValueError on a bad
    provider or model."""
    from anyscribecli.providers import PROVIDER_REGISTRY

    notes: list[str] = []
    provider, via = settings.provider, "config"
    # A per-run --diarize flag and a persisted diarize: true default must
    # resolve identically — the run executes the same diarize branch either way.
    diarize = diarize or settings.diarize

    if cli_provider:
        provider, via = cli_provider, "flag"
    elif diarize:
        # Deepgram handles large files natively and labels speakers consistently
        # without chunking, so it wins for diarization when a key exists.
        if provider != "deepgram" and os.environ.get("DEEPGRAM_API_KEY"):
            notes.append(f"switched from {provider} to deepgram for diarization")
            provider, via = "deepgram", "diarize"
        elif (tier := QUALITY_TIERS.get(settings.quality)) == "deepgram":
            # Reaching here means no DEEPGRAM_API_KEY — the tier's provider is
            # the diarize choice too, so the missing key is the real story.
            notes.append(
                f"WARNING: quality '{settings.quality}' wants deepgram (also the "
                f"diarization choice) but no DEEPGRAM_API_KEY is set — using {provider}"
            )
        elif tier:
            notes.append(
                f"diarize: quality '{settings.quality}' tier skipped ({tier} "
                f"can't diarize) — using {provider}"
            )
    else:
        tier = QUALITY_TIERS.get(settings.quality)
        if tier and has_key(tier):
            provider, via = tier, f"quality: {settings.quality}"
        elif tier:
            notes.append(
                f"WARNING: quality '{settings.quality}' wants {tier} but no "
                f"{PROVIDER_KEY_ENV[tier]} is set — using {provider} instead"
            )
        elif settings.quality != "custom":
            # A hand-edited unknown tier would otherwise be silently ignored —
            # and the Next-run banner would show a confident plan built on it.
            notes.append(
                f"WARNING: unknown quality '{settings.quality}' — using {provider} "
                f"(valid: accuracy, balanced, cost, free, custom)"
            )

    if provider not in PROVIDER_REGISTRY:
        available = ", ".join(sorted(PROVIDER_REGISTRY))
        raise ValueError(f"Unknown provider '{provider}'. Available: {available}")

    if cli_model:
        validate_model(provider, cli_model, settings.extra_models)
        model = cli_model
    else:
        model = settings.provider_models.get(provider) or next(
            iter(get_models(provider, settings.extra_models)), None
        )

    if (
        provider == "openai"
        and not diarize
        and not cli_model
        and settings.output_format in _TIMED_FORMATS
        and model in OpenAIProvider.NO_SEGMENT_MODELS
    ):
        notes.append(f"switched to whisper-1 — {model} can't produce timestamps")
        model = "whisper-1"

    if provider == "deepgram" and settings.language.lower() == "hi-latn":
        notes.append("hi-Latn is transcribed by deepgram's nova model")
    if provider == "openai" and diarize:
        notes.append("diarization is handled by gpt-4o-transcribe-diarize")

    return RunPlan(provider=provider, model=model, via=via, notes=notes)
