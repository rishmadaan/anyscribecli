---
type: decision
tags: [architecture, mvp, phase-1]
tldr: "Initial architecture for anyscribecli MVP — layered pipeline with pluggable providers and downloaders"
---

# Initial Architecture — Phase 1 MVP

## Context

Building anyscribecli from scratch as a Python CLI tool. Needed to make foundational architecture decisions that would support the MVP (YouTube + OpenAI) while leaving room for Instagram, additional providers, local models, batch processing, and a future GUI.

## Decisions Made

### Language: Python
- yt-dlp and instaloader are both Python-native — no shelling out for Instagram
- Whisper, local model bindings, audio processing are Python-first ecosystem
- httpx gives us async capability for future batch processing
- Cross-platform CLI tools are rock-solid in Python

### CLI Framework: Typer
- Type-hint based, minimal boilerplate
- Rich integration for formatted help panels
- Shell completion built-in
- Good growth path for adding subcommands

### Provider Architecture: ABC + Registry
- `TranscriptionProvider` abstract base class with `transcribe()` method
- Lazy-import registry in `providers/__init__.py` to avoid loading unused deps
- Each provider is a single file implementing the interface
- Easy to add local models later without changing the interface

### Downloader Architecture: ABC + URL Detection
- `AbstractDownloader` with `can_handle()` and `download()` methods
- `registry.py` tries each downloader in order, first match wins
- YouTube uses subprocess (yt-dlp CLI is stable, Python API isn't)
- Instagram will use Python API (need session management)

### Audio Optimization: 16kHz mono 64kbps mp3
- Proven optimal for Whisper from the AnyScribe web app
- 16kHz = Whisper's native processing rate
- Mono = 50% size reduction, optimal for speech
- 64kbps = safety margin above Whisper's 12kHz threshold

### Chunking: 18-minute segments for >25MB files
- Whisper API has a 25MB file limit
- 18 min at 64kbps mono = ~8.6MB per chunk (well under limit)
- Pattern taken from AnyScribe web app where it's been battle-tested

### Vault Structure: Platform/date hierarchy with MOC indexes
- Inspired by The Foundry's category/date/slug pattern
- `sources/<platform>/YYYY-MM-DD/<slug>.md`
- Master `_index.md` with newest-first table
- Daily processing logs for quick date-based browsing
- YAML frontmatter for Obsidian properties

## What Was Built

- Project scaffold with pyproject.toml, hatchling build
- Config layer (paths.py, settings.py)
- Vault scaffold with .obsidian/ configuration
- CLI with Typer (ascli onboard, ascli transcribe)
- YouTube downloader (yt-dlp subprocess)
- OpenAI Whisper provider with chunking support
- Vault writer with frontmatter generation
- Index management (master MOC + daily logs)
- Documentation foundation (CLAUDE.md, AGENTS.md, building docs, user docs)
