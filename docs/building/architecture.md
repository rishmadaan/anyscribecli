# Architecture

**Last updated:** 2026-03-26

## Overview

anyscribecli is a Python CLI tool with a layered pipeline architecture:

```
URL input -> Platform detection -> Download (yt-dlp/instaloader)
          -> Audio optimization (16kHz, mono, 64kbps mp3)
          -> Chunking if >25MB (18-min segments)
          -> Transcription (pluggable provider)
          -> Markdown generation (frontmatter + body)
          -> Vault indexing (_index.md + daily log)
```

## Layers

### CLI Layer (`cli/`)
- Typer app with `rich_markup_mode="rich"`
- Commands: `onboard`, `transcribe`, `config`, `providers`
- Global flags: `--json`, `--quiet`, `--verbose`

### Config Layer (`config/`)
- `paths.py`: all path constants via pathlib
- `settings.py`: Settings dataclass, YAML serialization, dotenv loading

### Download Layer (`downloaders/`)
- Abstract base with `download()` and `can_handle()` methods
- YouTube: yt-dlp subprocess with `--extract-audio --audio-format mp3`
- Instagram: instaloader Python API with session caching
- Registry dispatches URL to correct downloader

### Provider Layer (`providers/`)
- Abstract base with `transcribe(audio_path) -> TranscriptResult`
- OpenAI (default): Whisper API, verbose_json format
- Pluggable: OpenRouter, ElevenLabs, Sargam, future local models
- Provider selected via config, overridable per-run

### Vault Layer (`vault/`)
- Scaffold creates Obsidian vault with .obsidian/ config
- Writer generates markdown with YAML frontmatter
- Index maintains _index.md MOC and daily processing logs

### Core Layer (`core/`)
- Orchestrator ties the pipeline together
- Audio module handles chunking for files exceeding Whisper's 25MB limit

## Key Technical Decisions

- **yt-dlp via subprocess** (not Python API): CLI is stable and documented, Python API is not
- **httpx** over requests: async-capable for future batch processing
- **Dataclasses** over pydantic: fewer deps, sufficient for config/results
- **src/ layout**: prevents accidental imports from project root
- **Audio: 16kHz mono 64kbps**: proven optimal for Whisper from AnyScribe web app
