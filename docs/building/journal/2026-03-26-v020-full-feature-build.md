---
type: project-note
tags: [v0.2.0, instagram, providers, batch, config, local-models, onboarding]
tldr: "Built all planned features in one session — Instagram, 4 new providers, batch processing, config commands, full onboarding wizard"
---

# v0.2.0 — Full Feature Build

## Context

After completing the Phase 1 MVP (YouTube + OpenAI), built everything originally planned for v0.2.0 through v0.5.0 in a single session. Audit revealed stale docs and an incomplete onboarding wizard, which were then fixed.

## What Was Built

### Downloaders
- **Instagram** (`downloaders/instagram.py`): instaloader Python API, session caching mirroring Dropzone bundle pattern (load → test_login → fresh login → save). Lazy-loaded in registry so missing instaloader doesn't crash.

### Providers (4 new, 5 total)
- **OpenRouter** (`providers/openrouter.py`): No dedicated STT endpoint — uses audio-via-chat with base64-encoded audio. Research found this is a workaround, not a real transcription API.
- **ElevenLabs** (`providers/elevenlabs.py`): Scribe v1 API, `xi-api-key` header, word-level timestamps grouped into readable segments.
- **Sargam/Sarvam** (`providers/sargam.py`): REST API limited to 30-second clips — auto-chunks with custom 30s chunking (different from standard 18-min Whisper chunks).
- **Local** (`providers/local.py`): faster-whisper, auto-detects CUDA/CPU, VAD filtering, configurable model size via `ASCLI_LOCAL_MODEL`.

### CLI Commands
- **`ascli batch <file>`**: Batch transcribe URLs from a file, Rich progress bar, `--stop-on-error`, JSON output.
- **`ascli config show/set/path`**: View/change settings with dot-notation for nested keys (e.g., `instagram.username`).
- **`ascli providers list/test`**: Show providers with active indicator, test API key connectivity.

### Onboarding Wizard (rewritten)
- Shows all 5 providers in a Rich table
- Prompts for the correct API key based on selected provider
- Offers to configure additional provider keys
- Asks for Instagram username/password (optional, with security note)
- Summary shows all configured keys and Instagram status

### Output Formats
- `output_format: timestamped` — writes `[mm:ss]` timestamps per segment in transcript body

### Documentation
- `docs/user/providers.md` — full provider comparison (features, pricing, languages, setup)
- All living docs updated to reflect v0.2.0 state
- All user docs updated with new commands

## Research Findings (incorporated)

- OpenRouter has no STT endpoint — audio-via-chat is a workaround
- Sarvam REST API limited to 30 seconds — need custom chunking
- ElevenLabs returns word-level timestamps — grouped for readability
- faster-whisper auto-detects CUDA, falls back to CPU int8
