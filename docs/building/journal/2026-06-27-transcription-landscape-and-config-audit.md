---
type: reference
tags: [providers, research, configuration, transcription, roadmap]
tldr: "Audit of what's configurable vs hard-coded in scribe, a mid-2026 survey of the transcription-provider landscape, and a prioritized gap analysis. Urgent finding: ElevenLabs scribe_v1 is removed 2026-07-09 — scribe targets it and will break."
---

# Transcription landscape & configurability audit

**Date:** 2026-06-27
**Type:** Research + audit (no code changed)
**Scope:** Why some things are tunable and others are constants, where the
constants live, how the 2026 provider market has moved, and what scribe is
missing.

This entry is the audit trail behind the configurability section added to
`architecture.md` and the user-facing "what you can change vs what's fixed"
section in `docs/user/configuration.md`. It also records a market scan done on
2026-06-27 so the next person who revisits provider support has a dated baseline.

---

## 1. Configurability boundary — what's tunable vs hard-coded

The clean split: **user-facing behaviour is configurable; the audio and
transcription mechanics are hard-coded.** That keeps `config.yaml` short and
unintimidating for the semi-technical audience, at the cost of power-user
tunability.

### Configurable (no code change)

Lives in `config/settings.py::Settings`, persisted to `config.yaml`, with
secrets in `.env`. All overridable per-run via CLI flags or the Web UI.

| Setting | Default | Surface |
|---------|---------|---------|
| `provider` | `openai` | config / `--provider` / Web UI |
| `language` | `auto` | config / `--language` / Web UI |
| `output_format` | `clean` | config / Web UI |
| `diarize` | `false` | config / `--diarize` / Web UI |
| `keep_media` | `false` | config / Web UI |
| `prompt_download` | `never` | config / Web UI |
| `local_file_media` | `skip` | config / Web UI |
| `workspace_path` | `~/anyscribe` | config / Web UI |
| `local_model` | `base` | config / `scribe model` / `ASCLI_LOCAL_MODEL` |
| `instagram.username` | `""` | config |
| API keys + IG password | — | `.env` only |
| Web UI port | `8457` | `--port` flag only (not persisted) |

### Hard-coded (constant in source)

| Constant | Value | Where | Why fixed |
|----------|-------|-------|-----------|
| Audio sample rate / channels / bitrate | 16 kHz · mono · 64 kbps mp3 | `downloaders/youtube.py:58`, `downloaders/instagram.py:149`, `downloaders/local_file.py:52`, `core/audio.py:97` | Proven optimal for Whisper accuracy-per-byte. **Note: duplicated across 4 files, no shared constant.** |
| Whisper size trigger | 25 MB (`WHISPER_MAX_BYTES`) | `core/audio.py:9` | OpenAI upload cap |
| Whisper duration trigger | 30 min (`WHISPER_MAX_DURATION_SECONDS`) | `core/audio.py:16` | HTTP timeout ceiling |
| Chunk length / overlap | 18 min / 5 s | `core/audio.py:20,23` | Stay well under 25 MB at 64 kbps |
| Sarvam chunk | 30 s (`SARVAM_MAX_DURATION`) | `providers/sargam.py:27` | Sarvam sync REST cap |
| Provider model IDs | `whisper-1`, `gpt-4o-transcribe-diarize`, `nova-3`/`nova`, `scribe_v1`, `saaras:v2` | each `providers/*.py` | Pinned per provider |
| App home | `~/.anyscribecli` | `config/paths.py:6` | Fixed root for config + state |
| Web bind host | `127.0.0.1` | `web/app.py:63` | Localhost-only by design |
| Provider / downloader registries | the registry tables | `providers/__init__.py`, `downloaders/registry.py` | Code-level plugin lists |

---

## 2. Transcription landscape, mid-2026 (scanned 2026-06-27)

Two structural findings that matter more than any single model:

1. **English accuracy has commoditized.** The top ~6 systems sit within ~1 WER
   point of each other on clean audio; even open `whisper-large-v3-turbo` is
   within ~2.5 points of the best paid model. Accuracy is no longer a strong
   differentiator. (Sources: [Artificial Analysis AA-WER v2.0](https://artificialanalysis.ai/articles/aa-wer-v2),
   [HF Open ASR Leaderboard](https://huggingface.co/blog/open-asr-leaderboard))
2. **The batch-cost floor collapsed.** Open Whisper on Groq runs at ~$0.04/hr —
   roughly 9× cheaper than OpenAI's own hosted Whisper. The frontier moved to
   **streaming latency, multilingual depth, diarization quality, and "speech
   understanding"** (summarize / translate / Q&A over audio in one call).

### Where each provider scribe already uses now stands

- **OpenAI** — current family is `gpt-4o-transcribe`, `gpt-4o-mini-transcribe`,
  `gpt-4o-transcribe-diarize`, plus a May-2026 realtime line
  (`gpt-realtime-whisper`). scribe still defaults to legacy `whisper-1`.
  ([STT guide](https://developers.openai.com/api/docs/guides/speech-to-text))
- **Deepgram** — Nova-3 is current flagship; **Flux** (conversational, turn-aware)
  is the new release. There is no Nova-4. scribe is current enough here.
  ([models](https://developers.deepgram.com/docs/models-languages-overview))
- **ElevenLabs** — **`scribe_v1` is deprecated and removed 2026-07-09.** Current
  is `scribe_v2` (batch) and `scribe_v2_realtime`. scribe_v2 is the most accurate
  model measured (~2.3% English on AA-WER v2.0). scribe targets v1 → **will break.**
  ([Scribe v2](https://elevenlabs.io/blog/introducing-scribe-v2), [models](https://elevenlabs.io/docs/overview/models))
- **Sarvam** — `saaras:v3` (2026-02) is the unified default (transcribe +
  translate, 23 languages) with a WebSocket streaming + batch-async path
  (2 hr/file). scribe is on `saaras:v2` and stuck on the painful 30-second sync
  REST limit. ([Sarvam ASR](https://www.sarvam.ai/blogs/asr))
- **Local (faster-whisper)** — Whisper is no longer the best local model.
  `whisper-large-v3-turbo` (MIT, ~2.7–6× faster) and **NVIDIA Parakeet**
  (more accurate *and* ~23× faster — an hour of audio in ~1 min on an M3 Mac)
  both beat the Whisper sizes scribe ships.
  ([Parakeet card](https://huggingface.co/nvidia/parakeet-tdt-0.6b-v2),
  [turbo card](https://huggingface.co/openai/whisper-large-v3-turbo))

### Notable providers scribe does NOT support

- **AssemblyAI** (Universal-3 Pro) — richest "audio intelligence" suite
  (summarization, chapters, sentiment, PII redaction), promptable model, strong
  diarization, ~$0.21/hr. ([Universal-3 Pro](https://www.assemblyai.com/blog/introducing-universal-3-pro))
- **Groq (fast Whisper)** — cheapest cloud option at ~$0.04/hr, extreme speed,
  and it returns the *exact Whisper JSON scribe already parses*.
  ([Groq STT](https://console.groq.com/docs/speech-to-text))
- **Mistral Voxtral** — transcription + translation + summarization + Q&A in one
  model call; open-weight (Apache 2.0) variants. The clearest "speech
  understanding" product. ([Voxtral Transcribe 2](https://mistral.ai/news/voxtral-transcribe-2/))
- **Google Gemini / Chirp 3**, **Azure MAI-Transcribe-1.5**, **Speechmatics
  Melia**, **Gladia Solaria** — all credible, all lower priority than the above.

> **Source-quality caveat:** WER numbers are not comparable across sources
> (different datasets/methods) and most vendor "we win" claims are self-reported.
> Trust the independent ones: AA-WER v2.0, the HF Open ASR Leaderboard, the
> Pipecat streaming benchmark, and arXiv 2509.26177 (diarization). Several
> official pricing pages timed out on fetch; per-hour figures there came from
> aggregators citing the live pages.

---

## 3. Gap analysis — prioritized by impact-to-effort

**Tier 1 — fix existing providers (urgent / cheap, no new integration):**

1. **ElevenLabs is on `scribe_v1`, removed 2026-07-09 — this will break.** Migrate
   to `scribe_v2`. Do this first; it's a string change plus a response-shape check.
2. **OpenAI runs only `whisper-1`.** Move the default to `gpt-4o-transcribe`
   (lower WER, same price) or `gpt-4o-mini-transcribe` (half the price).
3. **Sarvam on `saaras:v2` + 30 s REST limit.** Upgrade to `saaras:v3` and adopt
   the batch-async endpoint to kill the 30 s chunking.
4. **Local tier lacks `whisper-large-v3-turbo` and Parakeet** — both beat the
   shipped Whisper sizes on speed and (Parakeet) accuracy.

**Tier 2 — high-value new providers:**

5. **Groq** — cheapest + fastest, and zero parsing changes (Whisper format).
   Lowest-effort new provider with the biggest visible win.
6. **AssemblyAI** — best fit for a markdown-output product (summaries, chapters).

**Tier 3 — capability gaps (not just providers):**

7. **LLM post-processing / speech understanding** (summarize, auto-chapter, Q&A
   over the transcript). This is the genuinely new 2026 capability and fits
   scribe's "structured markdown into Obsidian" identity better than chasing
   real-time streaming.
8. **Custom vocabulary / keyterm prompting** — every premium provider now has it;
   scribe exposes none.
9. **Real-time / streaming** — the industry's main frontier, but a poor fit for
   scribe's batch "download → transcribe → write" model. Low priority unless
   scribe pivots to live capture.

---

## 4. How the four hard-coded gaps should evolve

Applying the YAGNI-first decision tree (does it need to exist → reuse → stdlib →
native → dependency → one line → minimum-that-works). The recommended order is
deliberately small.

1. **Provider model IDs (do this).** Promote each provider's model to an optional
   `model:` config key, defaulting to a per-provider constant the code already
   holds. Reuse the existing `Settings` dataclass + `--provider` plumbing; no new
   abstraction. This is the highest-value gap because it unblocks the urgent
   ElevenLabs v1→v2 migration and the cheap OpenAI default bump *without* a
   release every time a vendor ships a model.
2. **Audio params (DRY first, expose maybe).** The 16 kHz/mono/64 kbps triple is
   duplicated in four files. Step one is to collapse it to a single constant in
   `core/audio.py` (or a small `AudioProfile` dataclass) and import it — pure
   reuse, no new feature. Only expose it in config if a real user need appears
   (YAGNI); archival-quality audio is hypothetical today.
3. **Web bind host (one line, gated).** `host` is already a parameter of
   `web/app.py::run()` — it just isn't surfaced. Add a `--host` flag to the `ui`
   command mirroring the existing `--port`. One line of plumbing. Keep the
   `127.0.0.1` default and print a clear warning when bound to `0.0.0.0`, since
   the server has no auth.
4. **Chunk thresholds (leave as constants).** 25 MB / 30 min / 18 min are
   provider-derived, not user preferences. YAGNI — there's no user story for
   tuning them, and the right long-term fix is per-provider limits living next to
   each provider, not a global knob. Skip until a provider actually needs a
   different value.

Net: one new config key (`model`), one DRY refactor, one flag, and a deliberate
"no" — the smallest set that removes the real friction.

---

## References

- AA-WER v2.0 leaderboard — https://artificialanalysis.ai/articles/aa-wer-v2
- HF Open ASR Leaderboard — https://huggingface.co/blog/open-asr-leaderboard
- OpenAI STT guide — https://developers.openai.com/api/docs/guides/speech-to-text
- Deepgram models — https://developers.deepgram.com/docs/models-languages-overview
- ElevenLabs Scribe v2 — https://elevenlabs.io/blog/introducing-scribe-v2
- AssemblyAI Universal-3 Pro — https://www.assemblyai.com/blog/introducing-universal-3-pro
- Groq STT — https://console.groq.com/docs/speech-to-text
- Mistral Voxtral Transcribe 2 — https://mistral.ai/news/voxtral-transcribe-2/
- Sarvam ASR — https://www.sarvam.ai/blogs/asr
- NVIDIA Parakeet — https://huggingface.co/nvidia/parakeet-tdt-0.6b-v2
