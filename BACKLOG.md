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
| 0.1.0 | YouTube + OpenAI MVP | Released 2026-03-26 |
| 0.2.0 | Full feature build (Instagram, all providers, batch, config, onboarding) | Released 2026-03-26 |
| 0.3.0 | Download command, media restructure, post-transcription prompts, UX polish | Released 2026-03-27 |
| 0.3.1 | Documentation accuracy audit — 16 issues fixed across all docs. First PyPI publish. | Released 2026-03-29 |
| 0.4.0 | Local file transcription, onboard reconfigure UX, Instagram error fix | **Current** |
| 0.5.0 | Cache/dedup, test suite, error handling | Next |
| 1.0.0 | Stable: full test coverage, CI/CD pipeline | Future |

### How to bump versions

Version lives in TWO places (must match):
- `src/anyscribecli/__init__.py`
- `pyproject.toml`

```bash
# After changing both files:
git add -A && git commit -m "Bump version to X.Y.Z"
git tag vX.Y.Z
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
- [x] `output_format: timestamped` — transcript with `[mm:ss]` timestamps per segment
- [x] Rich progress bar for batch jobs
- [x] Batch summary in daily log (each item indexed via orchestrator)
- [x] Provider comparison docs (`docs/user/providers.md`)

---

## v0.3.0 — Download, Media Restructure, UX Polish ✅

**Released:** 2026-03-27

- [x] `ascli download <url>` — download video or audio only, no transcription
  - `--video` (default) and `--audio-only` flags
  - Saves to `~/.anyscribecli/media/video/` or `media/audio/`
  - Supports --clipboard, --json, interactive prompt
- [x] Media restructured: moved outside workspace, split into audio/ and video/ by platform/date
- [x] Instagram password moved from config.yaml to .env (security fix)
- [x] `prompt_download` config: never/ask/always — post-transcription download offer
- [x] Onboarding wizard: arrow-key selectors (beaupy), post-transcription download step
- [x] URL validation: catches zsh glob mangling, interactive prompt fallback, --clipboard
- [x] instaloader promoted to main dependency (was optional)
- [x] Post-commit checklist (`docs/building/COMMIT_CHECKLIST.md`)
- [x] `build-with-rish.md` — reusable build reference for future projects

---

## v0.4.0 — Local Files, Onboard Reconfig UX ✅

**Released:** 2026-03-30

- [x] **Local file transcription** — `ascli transcribe /path/to/file.mp3`
  - Supports mp3, mp4, m4a, wav, opus, ogg, flac, webm, aac, wma
  - New `LocalFileDownloader` — converts to Whisper-optimized audio via ffmpeg
  - Vault output saved under `sources/local/YYYY-MM-DD/`
  - Works with batch command too
- [x] **Onboard reconfigure UX** — `ascli onboard --force` now shows current settings and asks before overwriting each step
  - Masked API key display (****abcd)
  - Per-step skip/change prompts
  - Arrow-key selectors pre-select current values
- [x] **Instagram error message fix** — corrected to point to `.env` instead of `config set`

---

## v0.5.0 — Cache, Dedup, Quality

- [ ] **Duplicate / cache checking** (inspired by AnyScribe web app's FindStamp pattern):
  - Before transcribing: check if URL was already transcribed (lookup by source URL in _index.md or a cache file)
  - Before downloading: check if video/audio already exists in media/
  - If cached, show the existing transcript and ask to re-transcribe or skip
  - `--force` flag to bypass cache and re-transcribe
  - Track cache hits/misses for cost awareness
- [ ] Full test suite (pytest — unit tests for providers, downloaders, vault, config)
- [ ] Comprehensive error handling and retry logic (network failures, API rate limits)
- [ ] Suppress instaloader's noisy retry output (redirect to log file)
- [ ] `ascli logs` command to view recent log files

---

## v1.0.0 — Stable Release

- [x] PyPI published (`pip install anyscribecli`) — live since v0.3.1
- [ ] GitHub Releases with release notes for each tag
- [ ] Full test coverage
- [ ] Stable config format (breaking changes require v2.0.0)
- [ ] CI/CD pipeline (GitHub Actions: lint, test, build, publish)

### Release process

See `docs/building/ops/release-checklist.md` for the full step-by-step.
See `docs/building/ops/pypi-guide.md` for PyPI setup, tokens, and troubleshooting.

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
- Cost tracking (Whisper API usage per month)
