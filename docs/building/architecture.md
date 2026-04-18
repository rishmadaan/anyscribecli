# Architecture

**Last updated:** 2026-04-18 (v0.7.2.3-ui)

## Overview

anyscribecli is a Python CLI tool with a layered pipeline architecture:

```
URL input -> Platform detection -> Download (yt-dlp / instaloader)
          -> Audio optimization (16kHz, mono, 64kbps mp3)
          -> Chunking if needed (18-min for Whisper, 30s for Sarvam)
          -> Transcription (pluggable provider)
          -> Markdown generation (frontmatter + body, clean/timestamped/diarized)
          -> Vault indexing (_index.md + daily log)
```

## Layers

### CLI Layer (`cli/`)
- Typer app with `rich_markup_mode="rich"`, custom `DefaultToTranscribe(TyperGroup)` class for bare-URL routing
- Primary command: `scribe` (alias: `ascli` for backward compat)
- Commands: `onboard`, `transcribe`, `download`, `batch`, `config`, `providers`, `ui`, `update`, `doctor`, `install-skill`
- Bare URL: `scribe "url"` auto-routes to transcribe (first arg not a known subcommand → prepend `transcribe`)
- `--json` and `--quiet` available on main commands (transcribe, download, batch, config show, providers list)
- `--json` for AI agent and scripting integration
- `__main__.py` enables `python -m anyscribecli` as alternative entry point (Windows PATH fallback)
- On Windows, app callback checks if `scribe` is on PATH; if not, prints the exact PowerShell command to fix it (one-time, uses `.path_warned` marker)

### MCP Layer (`mcp/`)
- FastMCP server with `scribe-mcp` entry point (stdio transport)
- 9 tools: transcribe, batch_transcribe, download, list_transcripts, get_config, set_config, list_providers, test_provider, doctor
- 3 resources: scribe://config, scribe://providers, scribe://workspace
- Calls core modules directly (orchestrator, settings, providers) — not CLI commands
- All tools return JSON, consistent error format
- Optional dependency: `pip install anyscribecli[mcp]` (adds `mcp>=1.0`)

### Web UI Layer (`web/` + `ui/`)
- FastAPI backend serving a built React SPA at `127.0.0.1:8457`
- Launched via `scribe ui` — core dependency, not optional
- REST API: `/api/config`, `/api/providers`, `/api/transcripts`, `/api/transcribe`, `/api/health`, `/api/shutdown`
- WebSocket: `/api/ws/jobs/{job_id}` for real-time transcription progress
- JobManager runs `process()` in ThreadPoolExecutor, bridges to async via `asyncio.Queue` + `call_soon_threadsafe`
- Orchestrator's `on_progress` callback emits `ProgressEvent` at each pipeline step (download, transcribe, write, index)
- Frontend: React 19 + TypeScript + Vite + Tailwind CSS v4, builds to `web/static/`
- SPA routing: catch-all `/{full_path:path}` serves `index.html` for non-API paths
- Server stashed on `app.state.server` for graceful `/shutdown` via `server.should_exit = True`
- Port conflict detection before starting uvicorn
- 17 smoke tests via FastAPI TestClient

### Skill Layer (`skill/`)
- Claude Code skill files bundled in package, auto-installed to `~/.claude/skills/scribe/`
- AI-first: auto-installs if `~/.claude/` exists (no opt-in), auto-updates via `.version` marker
- On every CLI invocation: compare `.version` to `__version__`, re-copy if mismatched
- One-time migration from old `ascli` skill directory to `scribe`
- Skill files: SKILL.md (operator guide), references/ (commands, providers, config, troubleshooting)

### Config Layer (`config/`)
- `paths.py`: all path constants via pathlib
- `settings.py`: Settings dataclass, YAML serialization, dotenv loading

### Download Layer (`downloaders/`)
- Abstract base with `download()` and `can_handle()` methods
- YouTube: yt-dlp subprocess with `--extract-audio --audio-format mp3`
- Instagram: instaloader Python API with session caching, direct video download
- Registry dispatches URL to correct downloader

### Provider Layer (`providers/`)
- Abstract base with `transcribe(audio_path, language, diarize) -> TranscriptResult`
- `TranscriptSegment` includes optional `speaker` field for diarization
- 6 providers implemented:
  - **OpenAI** (default): Whisper API or `gpt-4o-transcribe-diarize` with `--diarize`
  - **Deepgram**: Nova-3, native diarization, `hi-Latn` support
  - **ElevenLabs**: Scribe v1, word-level timestamps, 99 languages
  - **OpenRouter**: Audio-via-chat (GPT-4o-audio-preview), no timestamps
  - **Sargam/Sarvam**: Indic languages, auto-chunks to 30s REST API limit, diarization support
  - **Local**: faster-whisper, offline, CPU/GPU, no API key
- Lazy-import registry — each provider only loaded when requested
- Provider selected via config, overridable per-run with `--provider`
- Diarization enabled per-run with `--diarize` flag or `diarize: true` in config

### Vault Layer (`vault/`)
- Scaffold creates Obsidian vault with .obsidian/ config
- Writer generates markdown with YAML frontmatter
- Supports `clean` (default), `timestamped`, and `diarized` output formats
- Diarized format groups consecutive same-speaker segments into blocks: `**Speaker** *[ts]*: text`
- Index maintains _index.md MOC and daily processing logs

### Core Layer (`core/`)
- Orchestrator ties the pipeline together
- Audio module handles chunking (18-min for Whisper 25MB limit, 30s for Sarvam)
- Dependency checker detects OS (macOS, Linux, Windows), checks/installs yt-dlp, ffmpeg, Python; auto-updates stale yt-dlp (>60 days) before download. Uses module-based detection for pip-installed tools (`python -m module --version`) and `shutil.which` for system binaries
- Updater supports both git-based (dev) and pip-based (user) installs
- Migrations run at startup: workspace path rename, media→downloads, date folder flattening

## Key Technical Decisions

- **Python** over JS/TS: pipeline tools (yt-dlp, instaloader, whisper) are Python-native
- **yt-dlp via `python -m yt_dlp`** (not bare `yt-dlp` binary): invoked as a Python module via `sys.executable` to avoid PATH issues on Windows. Auto-updated when stale — YouTube changes streaming formats frequently, causing 403s with old extractors. `get_command("yt-dlp")` in `core/deps.py` centralizes invocation for all call sites
- **instaloader via Python API**: need session management for auth
- **httpx** over requests: async-capable for batch processing
- **Dataclasses** over pydantic: fewer deps, sufficient for config/results
- **src/ layout**: prevents accidental imports from project root
- **Audio: 16kHz mono 64kbps**: proven optimal for Whisper from AnyScribe web app
- **Lazy imports**: optional deps (faster-whisper for local provider) only imported when needed
- **Three install paths**: install.sh (users), pip from PyPI (recommended), git clone (devs)
- **SemVer**: 0.x for pre-stable, 1.0.0 when all platforms + providers stable
- **Auto-migration**: Startup migrations handle legacy paths transparently (workspace rename, media→downloads, date folder flattening)
- **PyPI automation**: GitHub Actions publishes on tag push via trusted publishing; `scripts/release.sh` for one-command releases
- **AI-first skill management**: Claude Code skill auto-installs and auto-updates on every CLI invocation. `.version` marker pattern borrowed from gitstow — one file read + string compare, never blocks CLI
- **MCP server**: Thin wrapper around core modules. Both CLI and MCP use same orchestrator/providers/settings — only output format differs (Rich console vs JSON)
- **Web UI as core dependency**: FastAPI/uvicorn ship with `pip install anyscribecli` (not optional). One app, one install. Same pattern as gitstow. React SPA builds to `web/static/`, committed to repo — end users don't need Node.js
- **Progress callback over async rewrite**: `on_progress` callback on `process()` avoids rewriting all providers/downloaders as async. ThreadPoolExecutor bridges sync→async cleanly
- **WebSocket over polling**: Real-time transcription progress (download→transcribe→write→index) needs instant feedback, not 30s HTMX polls. Event replay on late-connecting clients prevents missed events
