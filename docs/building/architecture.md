# Architecture

**Last updated:** 2026-03-26 (v0.2.0)

## Overview

anyscribecli is a Python CLI tool with a layered pipeline architecture:

```
URL input -> Platform detection -> Download (yt-dlp / instaloader)
          -> Audio optimization (16kHz, mono, 64kbps mp3)
          -> Chunking if needed (18-min for Whisper, 30s for Sarvam)
          -> Transcription (pluggable provider)
          -> Markdown generation (frontmatter + body, clean or timestamped)
          -> Vault indexing (_index.md + daily log)
```

## Layers

### CLI Layer (`cli/`)
- Typer app with `rich_markup_mode="rich"`
- Commands: `onboard`, `transcribe`, `download`, `batch`, `config`, `providers`, `update`, `doctor`
- Global flags: `--json`, `--quiet`
- `--json` on all commands for AI agent and scripting integration

### Config Layer (`config/`)
- `paths.py`: all path constants via pathlib
- `settings.py`: Settings dataclass, YAML serialization, dotenv loading

### Download Layer (`downloaders/`)
- Abstract base with `download()` and `can_handle()` methods
- YouTube: yt-dlp subprocess with `--extract-audio --audio-format mp3`
- Instagram: instaloader Python API with session caching, direct video download
- Registry dispatches URL to correct downloader

### Provider Layer (`providers/`)
- Abstract base with `transcribe(audio_path) -> TranscriptResult`
- 5 providers implemented:
  - **OpenAI** (default): Whisper API, verbose_json, segment timestamps
  - **ElevenLabs**: Scribe v1, word-level timestamps, 99 languages
  - **OpenRouter**: Audio-via-chat (GPT-4o-audio-preview), no timestamps
  - **Sargam/Sarvam**: Indic languages, auto-chunks to 30s REST API limit
  - **Local**: faster-whisper, offline, CPU/GPU, no API key
- Lazy-import registry — each provider only loaded when requested
- Provider selected via config, overridable per-run with `--provider`

### Vault Layer (`vault/`)
- Scaffold creates Obsidian vault with .obsidian/ config
- Writer generates markdown with YAML frontmatter
- Supports `clean` (default) and `timestamped` output formats
- Index maintains _index.md MOC and daily processing logs

### Core Layer (`core/`)
- Orchestrator ties the pipeline together
- Audio module handles chunking (18-min for Whisper 25MB limit, 30s for Sarvam)
- Dependency checker detects OS, checks/installs yt-dlp, ffmpeg, Python
- Updater supports both git-based (dev) and pip-based (user) installs

## Key Technical Decisions

- **Python** over JS/TS: pipeline tools (yt-dlp, instaloader, whisper) are Python-native
- **yt-dlp via subprocess** (not Python API): CLI is stable and documented, Python API is not
- **instaloader via Python API**: need session management for auth
- **httpx** over requests: async-capable for batch processing
- **Dataclasses** over pydantic: fewer deps, sufficient for config/results
- **src/ layout**: prevents accidental imports from project root
- **Audio: 16kHz mono 64kbps**: proven optimal for Whisper from AnyScribe web app
- **Lazy imports**: optional deps (faster-whisper for local provider) only imported when needed
- **Three install paths**: install.sh (users), pip from GitHub (power users), git clone (devs)
- **SemVer**: 0.x for pre-stable, 1.0.0 when all platforms + providers stable
