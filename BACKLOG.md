# Backlog

What's built, what's next, and what's on the horizon.

## Versioning

This project uses **Semantic Versioning** (SemVer): `MAJOR.MINOR.PATCH`

- **PATCH** (0.1.0 → 0.1.1): bug fixes, typos, small tweaks
- **MINOR** (0.1.0 → 0.2.0): new features, new provider, new command — backwards compatible
- **MAJOR** (0.x → 1.0.0): breaking changes (config format, removed commands, renamed flags)

The `0.x` prefix means pre-stable — breaking changes are allowed between minor versions. `1.0.0` signals stability.

### Version → Release mapping

| Version | Milestone | Status |
|---------|-----------|--------|
| 0.1.0 | YouTube + OpenAI MVP | **Current** |
| 0.2.0 | Instagram + config commands | Planned |
| 0.3.0 | Additional providers (OpenRouter, ElevenLabs, Sargam) | Planned |
| 0.4.0 | Batch processing + timestamped output | Planned |
| 0.5.0 | Local model support (whisper.cpp / faster-whisper) | Planned |
| 1.0.0 | Stable: all platforms, all providers, polished | Future |

### How to bump versions

Version lives in one place: `src/anyscribecli/__init__.py`

```python
__version__ = "0.1.0"  # ← change this
```

The `pyproject.toml` reads from the same source. Bump, commit, tag:

```bash
# After changing __init__.py:
git add -A && git commit -m "Bump version to 0.2.0"
git tag v0.2.0
git push && git push --tags
```

---

## v0.1.0 — YouTube + OpenAI MVP ✅

**Released:** 2026-03-26

Everything needed to transcribe a YouTube video to markdown:

- [x] YouTube download via yt-dlp (optimized audio: 16kHz, mono, 64kbps)
- [x] OpenAI Whisper transcription (verbose_json, segment timestamps)
- [x] Audio chunking for files >25MB (18-min chunks)
- [x] Obsidian vault output with YAML frontmatter
- [x] Master index (_index.md) + daily processing logs
- [x] `ascli onboard` — interactive wizard with dependency checking + auto-install
- [x] `ascli transcribe <url>` — with --provider, --language, --json, --keep-media, --quiet
- [x] `ascli update` — dual-path updater (git + pip)
- [x] `ascli doctor` — system health checks
- [x] `install.sh` — zero-friction installer script
- [x] CLAUDE.md + AGENTS.md — AI developer instructions
- [x] Developer memory layer (docs/building/)
- [x] User documentation (docs/user/) — semi-technical audience
- [x] MIT license, PyPI-ready metadata

---

## v0.2.0 — Instagram + Config + Providers + Batch + Local ✅

**Released:** 2026-03-26

All features originally planned for v0.2.0–v0.5.0, built in one session:

- [x] Instagram downloader (`downloaders/instagram.py`)
  - instaloader Python API with session caching (Dropzone bundle pattern)
  - Auth credentials from config.yaml
  - Reels and posts supported
- [x] `ascli config show` — display current settings (supports --json)
- [x] `ascli config set <key> <value>` — dot-notation for nested keys
- [x] `ascli config path` — print config file location
- [x] `ascli providers list` — show available providers with active indicator
- [x] `ascli providers test <name>` — test a provider's API key
- [x] OpenRouter provider — audio-via-chat using GPT-4o-audio-preview
- [x] ElevenLabs provider — Scribe v1 STT API, word-level timestamps
- [x] Sargam/Sarvam provider — Indic languages, auto-chunks to 30s for REST API limit
- [x] Local provider — faster-whisper, CPU/GPU, no API key, offline
- [x] `ascli batch <file>` — batch transcribe URLs from a file
- [x] Updated user docs for all new commands
- [x] Per-provider API key management in onboarding wizard
- [x] Instagram credentials in onboarding wizard
- [ ] `output_format: timestamped` — transcript with `[mm:ss]` timestamps
- [ ] Progress bar for batch jobs
- [ ] Batch summary in daily log
- [ ] Provider comparison docs

---

## v0.3.0 — Polish + Remaining Features

- [ ] Per-provider API key management in onboarding wizard
- [ ] `output_format: timestamped` — transcript with `[mm:ss]` timestamps per segment
- [ ] Progress bar for batch jobs (Rich progress bar instead of spinner)
- [ ] Batch summary appended to daily log
- [ ] Provider comparison docs (which provider for which language)
- [ ] Comprehensive error handling and retry logic
- [ ] Full test suite

---

- [ ] Local provider (`providers/local.py`)
  - whisper.cpp or faster-whisper bindings
  - No API key needed, no internet required
  - Model download management
- [ ] Offline mode detection
- [ ] Local model selection in config

---

## v1.0.0 — Stable Release

- [ ] All platforms working (YouTube, Instagram)
- [ ] All planned providers working
- [ ] Comprehensive error handling and recovery
- [ ] PyPI published (`pip install anyscribecli`)
- [ ] Full test suite
- [ ] Stable config format (breaking changes require v2.0.0)

---

## Icebox (ideas for later, no timeline)

- GUI (web UI via FastAPI + React, or TUI via Textual)
- Speaker diarization (who said what)
- AI-generated summaries (TL;DR via LLM after transcription)
- Chapter/section detection
- Search across all transcripts (`ascli search <query>`)
- Export formats beyond markdown (PDF, DOCX, SRT subtitles)
- Podcast RSS feed ingestion
- Topic file generation (Foundry-style, when 3+ transcripts share a topic)
- Cache system (skip re-transcription of same URL)
- Cost tracking (Whisper API usage per month)
