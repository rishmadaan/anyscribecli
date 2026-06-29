---
type: feature
tags: [providers, quality, groq, elevenlabs, config, web-ui]
tldr: "Added an accuracy↔cost quality picker (accuracy/balanced/cost/free) that resolves to a provider via the same auto-routing pattern as --diarize. Ships a new Groq provider, migrates ElevenLabs to scribe_v2 (v1 removed 2026-07-09), and makes config loading tolerant of version drift."
---

# Quality picker (accuracy ↔ cost)

**Date:** 2026-06-29
**Version:** 0.9.0
**Follows:** the [2026-06-27 transcription landscape audit](2026-06-27-transcription-landscape-and-config-audit.md)

## Why

Users wanted to pick *intent* — "most accurate" vs "cheapest" — instead of
remembering which provider is which. Accuracy is the priority (primarily-English
with Hinglish); cost matters but isn't limiting. The audit also surfaced an
urgent break: ElevenLabs `scribe_v1` is removed 2026-07-09 and we pinned it —
and `scribe_v2` happens to be the most accurate model, so the urgent fix is the
accuracy tier.

## Design — the lazy version

The four tiers map to four **distinct** providers, so `quality` is just a
friendly alias that resolves to a provider. No per-provider model-override
machinery: it reuses the existing `--diarize → deepgram` auto-routing pattern.

| Tier | Provider | Model |
|------|----------|-------|
| `balanced` (default) | deepgram | `nova-3` |
| `accuracy` | elevenlabs | `scribe_v2` |
| `cost` | groq | `whisper-large-v3-turbo` |
| `free` | local | configured `local_model` |

- `core/quality.py` — `QUALITY_TIERS` dict + `apply_quality(settings, explicit_provider)`.
- **Precedence**: explicit `--provider` → `--diarize` routing → `quality` routing → configured provider.
- **Graceful fallback**: if the tier's provider key is absent, keep the
  configured provider so keyless users still work.
- **Default = `balanced` (Deepgram).** Originally `accuracy` (ElevenLabs), but
  changed pre-release: Deepgram is already tested in this project and a key is on
  hand, while `accuracy` needs an ElevenLabs key not everyone has. `accuracy`
  stays one flag away. (Deepgram is also the `--diarize` workhorse, so the
  default tier and the diarization default agree.)
- Surfaces: `--quality` on `transcribe` + `batch`; `quality` in config; Web UI
  picker on the Transcribe Options panel (with a "Provider: auto · from quality"
  dropdown override) and the Settings page. The Web UI sends `quality` and only
  sends `provider` when explicitly overridden, so the backend stays the single
  resolver (no duplicated tier map in TypeScript).

## Other changes

- **New Groq provider** (`providers/groq.py`) — a ~20-line subclass of
  `OpenAIProvider`. Groq's STT API is OpenAI-compatible, so only the endpoint,
  `GROQ_API_KEY`, and model differ; chunking and response parsing are inherited.
  Diarize path overridden to raise a clear error (Groq has no diarization model).
  `OpenAIProvider` gained a `MODEL` class attribute so the subclass is clean.
- **ElevenLabs `scribe_v1` → `scribe_v2`** — one string; v2 keeps the same
  `{text, language_code, words[]}` response contract.
- **Config-load resilience** — `Settings.from_dict` now ignores unknown keys
  (top-level and inside `instagram`). A config written by a different version
  (e.g. a branch with an extra `instagram.browser` field) loads instead of
  crashing on `TypeError`. Covered by `tests/test_settings.py`.

## What ponytail skipped

- No per-provider model-override subsystem (tiers map to providers).
- OpenAI untouched — no `gpt-4o-transcribe` response-format rework (it drops
  segment timestamps).
- No Groq diarization, no fallback "engine" (one key-presence check).

## Open follow-up — Hinglish bake-off

The accuracy tier is set to ElevenLabs `scribe_v2` on the basis that the audio is
primarily English. For genuine Hinglish, the specialist may be Deepgram
(`hi-Latn`, the balanced tier) or Sarvam. The right call is empirical: run a real
sample through the tiers and, if a specialist wins, remap the one-line
`QUALITY_TIERS["accuracy"]` entry. The dict makes that a one-line change.
