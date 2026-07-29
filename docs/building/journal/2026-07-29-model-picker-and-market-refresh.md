---
type: feature
tags: [providers, models, openai, sarvam, openrouter, local, web-ui, mcp]
tldr: "v0.14.0. Per-provider model picker across CLI/Web/MCP (settings.provider_models + --model). Adds OpenAI's new gpt-transcribe (July 28 release), migrates Sarvam to saaras:v3 (v2.5 endpoint deprecated), fixes OpenRouter's dead default slug, adds large-v3-turbo + distil-large-v3.5 local sizes."
---

# Per-provider model picker + July-2026 model market refresh

**Date:** 2026-07-29 · **Version:** 0.14.0

## Why now

OpenAI shipped two new transcription models on **2026-07-28**: `gpt-transcribe`
(file transcription; $0.0045/min — 25% below whisper-1 — and roughly half
Whisper's error rate in OpenAI's benchmarks) and `gpt-live-transcribe`
(realtime WebSocket only — irrelevant to a file-based tool, deliberately not
integrated). Until now every cloud provider had exactly one hardcoded model, a
deliberate simplification recorded in `core/quality.py`. Wanting to actually
use `gpt-transcribe` forced the model-override machinery into existence.

A full market sweep (two research agents, primary sources, 2026-07-29) also found:

- **OpenRouter had silently broken**: our default `openai/gpt-4o-audio-preview`
  no longer exists on OpenRouter at all — every openrouter transcription would
  have 404'd. New default: `openai/gpt-audio-mini` (like-for-like successor).
  Gemini 2.5/3 Flash and Voxtral slugs offered as suggestions; field stays
  freeform since any audio-capable slug is valid.
- **Sarvam's `/speech-to-text-translate` endpoint (saaras:v2.5) is on a
  deprecation path** per docs.sarvam.ai. Default migrated to `saaras:v3` on
  `/speech-to-text` with `mode=translate` (preserves the historical
  translate-to-English behaviour; ~19% WER on IndicVoices vs v2.5's worse
  baseline). Sync API still has the exclusive 30s limit → 28s chunking
  unchanged. `saaras:v2.5` remains pickable and routes to the legacy endpoint.
- **Deepgram nova-3 and ElevenLabs scribe_v2 are still each vendor's best
  prerecorded model** (Deepgram Flux and scribe_v2_realtime are streaming-only).
  Nothing to change.
- **Groq** exposes `whisper-large-v3` (higher accuracy, $0.111/hr) alongside
  our default `whisper-large-v3-turbo` — now pickable.
- **Local**: faster-whisper natively supports `large-v3-turbo`
  (mobiuslabsgmbh repo, ~8x faster than large-v3 at near-equal accuracy) and
  `distil-large-v3.5` (distil-whisper CT2 repo, English-focused). Added as
  sizes. `local.py` now loads by HF repo id instead of size alias so new sizes
  work regardless of the installed faster-whisper's alias table.

## The machinery

Single source of truth: `providers/__init__.py::PROVIDER_MODELS`
(provider → pickable ids, first = default; `OPEN_MODEL_PROVIDERS = {"openrouter"}`
skips validation). `get_provider(name, model=None)` validates and sets
`provider.model` (new attr on the base class; each provider reads
`self.model or <default>`).

Persistence: `settings.provider_models: dict[str, str]` (provider → pinned id;
missing = default). Surfaces:

- CLI: `--model/-m` on `scribe` and `scribe batch` (applies to whichever
  provider wins quality/diarize resolution); `scribe config set
  provider_models.<provider> <model>` (validated); `scribe providers list` now
  shows Model + Also available columns.
- Web: `GET /api/providers` gains `models` + `freeform_model`;
  `PUT /api/config` accepts `provider_models`; `POST /api/transcribe` accepts
  `model`. UI: shared `ModelInput` component (select, or datalist text input
  for openrouter) on Transcribe + Settings pages.
- MCP: `transcribe(model=...)` param; `list_providers` returns model info.

## The gpt-transcribe caveat that shaped the default

`gpt-transcribe` (like the gpt-4o transcribe family) does **not** support
`response_format=verbose_json` — no segment timestamps. `timestamped` and
`diarized` output formats need segments, so **whisper-1 stays the OpenAI
default**; gpt-transcribe is the pick for `clean` output at better accuracy
and lower cost. The provider sends `response_format=json` for the no-segment
models and reads the new `languages` (list) response field. Diarization still
auto-routes to `gpt-4o-transcribe-diarize`, untouched.

## Verification

- 305 tests pass (was 294 + 4 stale expectations updated; 6 new model-picker
  tests: pin validation, json fallback request shape, legacy Sarvam pin,
  openrouter pin-beats-env).
- Live checks: `scribe providers list` table, `config set provider_models.*`
  accept/reject, `/api/providers` + `/api/config` via TestClient, Vite build
  green.

## Addendum (same day): independent audit → 0.14.1

Rish asked for an adversarial post-release audit; it confirmed release
integrity (tag/wheel/PyPI/skill all consistent; OpenRouter + Sarvam claims
verified against primary sources) but found real defects, fixed in 0.14.1 via
the new branch→PR→audit workflow:

- **HIGH:** `gpt-transcribe` reports `languages` as a list of *objects*
  (`[{"code": "fr"}]`), not strings — the parser wrote a raw dict into vault
  frontmatter, and the covering test had stubbed a shape OpenAI never returns.
  Both fixed.
- **MED:** a hand-edited bare `provider_models:` YAML line (→ `None`) crashed
  every transcription; `from_dict` now coerces non-dict values to `{}`.
- **MED:** `-m` on `local` was silently swallowed; `get_provider` now rejects
  pins for providers without a pickable list.
- **MED:** the OpenAI diarize call sent `verbose_json`, but the spec allows
  only `json`/`text`/`diarized_json` for `gpt-4o-transcribe-diarize` (speaker
  labels need `diarized_json`; `chunking_strategy` required >30s). Fixed
  per spec — **not yet live-tested** (Rish's stored OpenAI key returns 401 and
  needs rotation).
- **LOW:** `large-v3-turbo` repo id updated to canonical
  `dropbox-dash/faster-whisper-large-v3-turbo` (mobiuslabsgmbh is a 307
  redirect). Known cost: anyone who pulled turbo under the old id between
  0.14.0 and 0.14.1 has an orphaned cache entry (invisible to
  `scribe model list/rm`) and re-downloads ~1.6 GB — accepted, tiny window; Sarvam `with_diarization` removed (never documented on either
  sync endpoint — Batch API only); doc contradictions fixed (gpt-4o-transcribe
  price claim, SKILL.md diarize note, sargam diarization column).

Process change (Rish, 2026-07-29): all future feature work goes branch → PR →
independent audit → merge, never straight to main.

## Sources

OpenAI model pages + API changelog (developers.openai.com, 2026-07-28 entries),
Whisper→GPT-Transcribe migration cookbook, OpenRouter live `/api/v1/models`,
docs.sarvam.ai STT REST guide, developers.deepgram.com changelog,
elevenlabs.io models doc, console.groq.com/docs/models, SYSTRAN/faster-whisper
`utils.py`. Full reports in the session transcript of 2026-07-29.
