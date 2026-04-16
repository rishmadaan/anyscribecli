---
type: project-note
tags: [diarization, deepgram, openai, sarvam, multi-speaker, v0.7.0]
tldr: Added multi-speaker diarization with --diarize flag, Deepgram Nova provider, OpenAI gpt-4o-transcribe-diarize, Sarvam diarization, and speaker-grouped output format.
---

# v0.7.0 — Multi-Speaker Diarization + Deepgram Provider

## What Was Built

Multi-speaker transcription support across the full pipeline: data model, 3 providers with diarization, CLI flag, MCP tool parameter, and a new output format.

### Data Model Changes
- `TranscriptSegment` gained `speaker: str | None = None` field
- `TranscriptionProvider.transcribe()` ABC gained `diarize: bool = False` parameter
- `Settings` gained `diarize: bool = False` config option
- `output_format` now accepts `"diarized"` alongside `"clean"` and `"timestamped"`

### New Provider: Deepgram Nova
- `providers/deepgram.py` — `POST https://api.deepgram.com/v1/listen`
- Model: `nova-3`, auth: `Token` header (not Bearer)
- Native `diarize=true` query param with per-word speaker IDs
- Supports `hi-Latn` language code for romanized Hindi (Hinglish)
- Response parsing: groups consecutive words by speaker into segments
- Without diarize: groups words into ~30-word segments for timestamps
- Reuses standard `needs_chunking()` / `chunk_audio()` for large files

### OpenAI Diarization
- When `diarize=True`: switches model from `whisper-1` to `gpt-4o-transcribe-diarize`
- Removes `timestamp_granularities[]` (not supported by diarize model)
- Bypasses client-side chunking — server handles it via `chunking_strategy=auto`
- Parses `speaker` field from response segments

### Sarvam Diarization
- Added `with_diarization=true` request param
- Parses `turns` or `diarized_transcript` from response
- Known limitation: 30s chunk boundaries may restart speaker IDs

### Diarized Output Format
- New `_format_diarized()` in vault writer
- Groups consecutive same-speaker segments into single blocks
- Format: `**Speaker 0** *[00:01:15]*: merged text from consecutive segments`
- Fallback: if all segments lack speaker data, falls back to timestamped format
- Frontmatter includes `diarized: true` when diarization was used

### CLI + MCP
- `--diarize` / `-d` flag on `transcribe` and `batch` commands
- When `--diarize` is set and `output_format` is `clean`, auto-upgrades to `diarized`
- MCP server: `diarize` param on `transcribe()` and `batch_transcribe()` tools

## Design Decisions

**Why Deepgram as the new provider** — Native `hi-Latn` support for Hinglish transcription (romanized Hindi), fast diarization, $200 free credit. Best fit for the user's primary use case (Hindi-English meeting transcripts).

**Why `--diarize` flag (not auto-detect)** — Diarization models are different models or add latency/cost. For single-speaker content (most YouTube), it's wasted compute and can introduce false speaker splits. Explicit opt-in is cleaner.

**Why speaker-grouped output** — Inspired by the dashing-kx/Fireflies transcript format. Consecutive sentences by the same speaker merged into blocks with timestamps only on block start. Much more readable than per-sentence labels.

**Why not AssemblyAI** — Deferred for now. OpenAI + Deepgram + Sarvam cover the key use cases (English, Hinglish, Indian languages). AssemblyAI can be added later.

## Files Changed

**New (1):** `src/anyscribecli/providers/deepgram.py`

**Modified (14):** base.py, __init__.py, openai.py, sargam.py, elevenlabs.py, openrouter.py, local.py, settings.py, orchestrator.py, writer.py, transcribe.py, batch.py, onboard.py, config_cmd.py, server.py
