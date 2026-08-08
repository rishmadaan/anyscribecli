# Architecture

**Last updated:** 2026-07-04 (v0.13.0 — menu-bar tray companion + launchd auto-start, GitHub Releases automation)

## Overview

anyscribe has three entry surfaces but one shared core. The CLI, the Web UI,
and the Claude Code skill (via MCP) all funnel into the same orchestrator, which
runs a fixed pipeline:

```
   three ways in            ┌─────────┐ ┌────────┐  ┌──────────────┐
                            │   CLI   │ │ Web UI │  │  Claude Code │
                            │anyscribe│ │ React+ │  │   skill/MCP  │
                            │         │ │FastAPI │  │              │
                            └────┬────┘ └───┬────┘  └──────┬───────┘
                                 └──────────┼──────────────┘
                                            ▼
                              ┌───────────────────────────┐
   one shared core            │  core/orchestrator.process │
                              └─────────────┬─────────────┘
                                            ▼
   0. dedup       ┌────────────────────────────────────────────────┐
    (unless       │ scan vault frontmatter for a matching `source:` │
     --force)     │ hit → return existing file, cached=True, stop   │
                  └───────────────────────┬────────────────────────┘
                                          ▼
   1. download    ┌────────────────────────────────────────────────┐
                  │ registry picks downloader (first match wins):   │
                  │   local file → YouTube + Instagram (both yt-dlp) │
                  └───────────────────────┬────────────────────────┘
                                          ▼
   2. prepare     ┌────────────────────────────────────────────────┐
      audio       │ 16 kHz · mono · 64 kbps mp3                     │
                  │ chunk if >25 MB or >30 min (18-min parts, 5s ov)│
                  └───────────────────────┬────────────────────────┘
                                          ▼
   3. transcribe  ┌────────────────────────────────────────────────┐
                  │ one of 7 providers (cloud API or local Whisper) │
                  │ openai · deepgram · elevenlabs · sargam · ...    │
                  └───────────────────────┬────────────────────────┘
                                          ▼
   4. write       ┌────────────────────────────────────────────────┐
                  │ markdown → ~/anyscribe vault                    │
                  │ frontmatter + body (clean/timestamped/diarized) │
                  └───────────────────────┬────────────────────────┘
                                          ▼
   5. index       ┌────────────────────────────────────────────────┐
                  │ update _index.md MOC + daily log                │
                  └────────────────────────────────────────────────┘
```

Downloaded media lands *outside* the vault (in `~/.anyscribe/downloads/`) so
the Obsidian vault at `~/anyscribe/` stays pure markdown.

## Layers

### CLI Layer (`cli/`)
- Typer app with `rich_markup_mode="rich"`, custom `DefaultToTranscribe(TyperGroup)` class for bare-URL routing
- Primary command: `anyscribe` (aliases: `scribe`, `ascli` for backward compat)
- Commands: `onboard`, `transcribe`, `download`, `batch`, `rm`, `logs`, `config`, `providers`, `local`, `model`, `ui`, `tray`, `install-service`, `uninstall-service`, `update`, `doctor`, `install-skill`
- **Tray supervision model** (`cli/tray_cmd.py` + `core/tray.py`): `anyscribe tray` is a `pystray` menu-bar icon that supervises `anyscribe ui` as a subprocess — attaches to an already-running server instead of colliding (TCP connect-probe), guards against double-launch with a pidfile at `~/.anyscribe/tray.pid`, and tears down via a `signal.pthread_sigmask` + `signal.sigwait` watcher thread rather than a plain `signal.signal` handler (pystray's macOS Cocoa event loop can block Python bytecode from running, so a normal handler can miss SIGTERM/SIGINT). `core/service.py` registers a macOS launchd LaunchAgent (`anyscribe install-service`) that runs `{python} -m anyscribe tray` at login.
- Bare URL: `anyscribe "url"` auto-routes to transcribe (first arg not a known subcommand → prepend `transcribe`)
- `--json` and `--quiet` available on main commands (transcribe, download, batch, config show, providers list)
- `--json` for AI agent and scripting integration
- `__main__.py` enables `python -m anyscribe` as alternative entry point (Windows PATH fallback)
- On Windows, app callback checks if `anyscribe` is on PATH; if not, prints the exact PowerShell command to fix it (one-time, uses `.path_warned` marker)

### MCP Layer (`mcp/`)
- FastMCP server with `scribe-mcp` entry point (stdio transport)
- 10 tools: transcribe, batch_transcribe, download, list_transcripts, delete_transcript, get_config, set_config, list_providers, test_provider, doctor
  - `transcribe` / `batch_transcribe` accept `quality` (accuracy|balanced|cost|free) and `force`; `force` bypasses the dedup check
- 3 resources: scribe://config, scribe://providers, scribe://workspace
- Calls core modules directly (orchestrator, settings, providers) — not CLI commands
- All tools return JSON, consistent error format
- Optional dependency: `pip install anyscribe[mcp]` (adds `mcp>=1.0`)

### Web UI Layer (`web/` + `ui/`)
- FastAPI backend serving a built React SPA at `127.0.0.1:8457`
- Launched via `anyscribe ui` — core dependency, not optional
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
- Claude Code skill files bundled in package, auto-installed to `~/.claude/skills/anyscribe/`
- AI-first: auto-installs if `~/.claude/` exists (no opt-in), auto-updates via `.version` marker
- On every CLI invocation: compare `.version` to `__version__`, re-copy if mismatched
- One-time cleanup of the stale `ascli`/`scribe` skill directories (superseded by `anyscribe`)
- Skill files: SKILL.md (operator guide), references/ (commands, providers, config, troubleshooting)

### Config Layer (`config/`)
- `paths.py`: all path constants via pathlib
- `settings.py`: Settings dataclass, YAML serialization, dotenv loading

### Download Layer (`downloaders/`)
- Abstract base with `download()` and `can_handle()` methods
- YouTube: yt-dlp subprocess with `--extract-audio --audio-format mp3`
- Instagram: yt-dlp subprocess with `--extract-audio`; cookies optional via `--cookies-from-browser` (config field `instagram.browser`). Same pattern as YouTube.
- Registry dispatches URL to correct downloader

### Provider Layer (`providers/`)
- Abstract base with `transcribe(audio_path, language, diarize) -> TranscriptResult`
- `TranscriptSegment` includes optional `speaker` field for diarization
- 7 providers implemented:
  - **OpenAI** (default): `gpt-transcribe`, or `whisper-1` when timestamps are needed, or `gpt-4o-transcribe-diarize` with `--diarize`. `MODEL` class attr so Groq can subclass it.
  - **Deepgram**: Nova-3 (nova-2 also pickable), native diarization, `hi-Latn` support
  - **ElevenLabs**: Scribe v2, word-level timestamps, 90+ languages
  - **OpenRouter**: Audio-via-chat (`openai/gpt-audio-mini`), no timestamps, freeform model slugs
  - **Sargam/Sarvam**: Indic languages, `saaras:v3` only, auto-chunks to 30s REST API limit
  - **Groq**: `whisper-large-v3-turbo`, OpenAI-compatible — thin subclass of `OpenAIProvider`. Cheapest + fastest.
  - **Local**: faster-whisper, offline, CPU/GPU, no API key
- Lazy-import registry — each provider only loaded when requested
- Provider selected via config, overridable per-run with `--provider`
- **One resolution point**: `core/resolve.py::resolve_run(settings, cli_provider=, cli_model=, diarize=)` returns `RunPlan(provider, model, via, notes)` and is the only implementation of the ladder — explicit `--provider` → `--diarize` → `quality` tier → configured provider. All four run surfaces (CLI transcribe, batch, web, MCP) call it; none may reimplement it. `via` explains the choice; `notes` carry every automatic decision (keyless-tier fallback, whisper-1 timestamp switch, hi-Latn, diarize reroute) so no surface can silently swallow one.
- **Quality routing**: `quality` ∈ accuracy/balanced/cost/free (tier → provider, `core/quality.py::QUALITY_TIERS`) or `custom` (use `settings.provider`). Every write that sets a provider also writes `quality="custom"` — see `core/config_set.py::set_value` and `core/onboard_headless.py`.
- **Model resolution**: per-run `--model` (validated) > `settings.provider_models[provider]` > `get_models(provider, settings.extra_models)[0]` > `None` (local only).
- Diarization enabled per-run with `--diarize` flag or `diarize: true` in config

### Vault Layer (`vault/`)
- Scaffold creates Obsidian vault with .obsidian/ config
- Writer generates markdown with YAML frontmatter
- Supports `clean` (default), `timestamped`, and `diarized` output formats
- Diarized format groups consecutive same-speaker segments into blocks: `**Speaker** *[ts]*: text`
- Index maintains _index.md MOC and daily processing logs

### Core Layer (`core/`)
- Orchestrator ties the pipeline together; runs the dedup check (step 0) before any download, skippable with `force=True`
- Dedup (`core/dedup.py`) — `find_existing_transcript(source)` scans `sources/*/*.md` frontmatter for a matching `source:` line; no cache file, the vault is the source of truth
- Audio module handles chunking (18-min for Whisper 25MB limit, 30s for Sarvam)
- Dependency checker detects OS (macOS, Linux, Windows), checks/installs yt-dlp, ffmpeg, Python; auto-updates stale yt-dlp (>60 days) before download. Uses module-based detection for pip-installed tools (`python -m module --version`) and `shutil.which` for system binaries
- Updater supports both git-based (dev) and pip-based (user) installs
- Migrations run at startup: workspace path rename, media→downloads, date folder flattening

## Key Technical Decisions

- **Python** over JS/TS: pipeline tools (yt-dlp, whisper) are Python-native
- **yt-dlp via `python -m yt_dlp`** (not bare `yt-dlp` binary): invoked as a Python module via `sys.executable` to avoid PATH issues on Windows. Auto-updated when stale — YouTube changes streaming formats frequently, causing 403s with old extractors. `get_command("yt-dlp")` in `core/deps.py` centralizes invocation for all call sites
- **yt-dlp for Instagram (0.8.3+)**: replaced instaloader to eliminate the rate-limit-prone `test_login()` GraphQL probe and the password-on-disk requirement. Cookies come from the user's existing browser via `--cookies-from-browser`. See `docs/building/journal/2026-04-29-instagram-yt-dlp-migration.md` for the decision record.
- **httpx** over requests: async-capable for batch processing
- **Dataclasses** over pydantic: fewer deps, sufficient for config/results
- **src/ layout**: prevents accidental imports from project root
- **Audio: 16kHz mono 64kbps**: proven optimal for Whisper from AnyScribe web app
- **Lazy imports**: optional deps (faster-whisper for local provider) only imported when needed
- **Three install paths**: install.sh (users), pip from PyPI (recommended), git clone (devs)
- **SemVer**: 0.x for pre-stable, 1.0.0 when all platforms + providers stable
- **Auto-migration**: Startup migrations handle legacy paths transparently (workspace rename, media→downloads, date folder flattening)
- **CI + PyPI automation**: GitHub Actions runs lint, tests, package build, and frontend bundle freshness checks on pushes/PRs. Tag pushes publish to PyPI via trusted publishing; `scripts/release.sh` handles one-command releases. The same workflow also runs `gh release create --generate-notes` after publish, so every tag gets a GitHub Release automatically.
- **Tray as a supervisor, not a rewrite**: `anyscribe tray` spawns/attaches to the existing `anyscribe ui` server rather than embedding a webview or rewriting the UI as a native app — the browser stays the UI surface, the tray only adds discoverability and process supervision.
- **AI-first skill management**: Claude Code skill auto-installs and auto-updates on every CLI invocation. `.version` marker pattern borrowed from gitstow — one file read + string compare, never blocks CLI
- **MCP server**: Thin wrapper around core modules. Both CLI and MCP use same orchestrator/providers/settings — only output format differs (Rich console vs JSON)
- **Web UI as core dependency**: FastAPI/uvicorn ship with `pip install anyscribe` (not optional). One app, one install. Same pattern as gitstow. React SPA builds to `web/static/`, committed to repo — end users don't need Node.js
- **Progress callback over async rewrite**: `on_progress` callback on `process()` avoids rewriting all providers/downloaders as async. ThreadPoolExecutor bridges sync→async cleanly
- **WebSocket over polling**: Real-time transcription progress (download→transcribe→write→index) needs instant feedback, not 30s HTMX polls. Event replay on late-connecting clients prevents missed events

## Configurability surface: tunable vs hard-coded

anyscribe draws a deliberate line: **user-facing behaviour is configurable; the
audio and transcription mechanics are constants in source.** This keeps
`config.yaml` short for a semi-technical audience, at the cost of power-user
tunability. The user-facing version of this boundary is in
`docs/user/configuration.md`; this section is the developer map.

```
   set at runtime (knobs)                fixed in source (constants)
   ┌───────────────────────────┐        ┌────────────────────────────────┐
   │ config/settings.py         │        │ core/audio.py   — chunk sizes  │
   │   → config.yaml            │        │ providers/*.py  — model IDs    │
   │ .env             (secrets) │        │ downloaders/*   — 16k/mono/64k │
   │ CLI flags · Web UI · MCP   │        │ config/paths.py — ~/.anyscribe │
   └───────────────────────────┘        │ web/app.py      — host 127.0.. │
   change anytime, no code              └────────────────────────────────┘
                                        change = edit source + reinstall
```

Hard-coded constants and where they live:

| Constant | Value | Source | Why fixed |
|----------|-------|--------|-----------|
| Audio profile | 16 kHz · mono · 64 kbps mp3 | `downloaders/youtube.py:58`, `instagram.py:149`, `local_file.py:52`, `core/audio.py:97` | Proven optimal for Whisper accuracy-per-byte. Duplicated across 4 files — no shared constant yet. |
| Whisper size trigger | 25 MB (`WHISPER_MAX_BYTES`) | `core/audio.py:9` | OpenAI upload cap |
| Whisper duration trigger | 30 min (`WHISPER_MAX_DURATION_SECONDS`) | `core/audio.py:16` | HTTP timeout ceiling |
| Chunk length / overlap | 18 min / 5 s | `core/audio.py:20,23` | Stays under 25 MB at 64 kbps |
| Sarvam chunk | 30 s (`SARVAM_MAX_DURATION`) | `providers/sargam.py:27` | Sarvam sync REST cap |
| Provider model catalogs | `PROVIDER_MODELS` in `providers/__init__.py` (defaults: `gpt-transcribe`, `nova-3`/`nova`, `scribe_v2`, `saaras:v3`, `openai/gpt-audio-mini`, `whisper-large-v3-turbo`); diarize pins `gpt-4o-transcribe-diarize` | `providers/__init__.py` + each `providers/*.py` | Pickable since 0.14.0 via `settings.provider_models` / `--model`; the `quality` tier still picks the provider, the pin rides on top. **Closed catalogs are release-managed** — each entry needs response-parsing code, so users can't extend them. `settings.extra_models` is the one escape hatch and is openrouter-only (0.15.0), because an open-model provider forwards any slug. Read catalogs via `get_models(name, extra_models)`, never `PROVIDER_MODELS` directly |
| App home | `~/.anyscribe` | `config/paths.py:6` | Fixed root for config + state |
| Web bind host | `127.0.0.1` (port is configurable via `--port`) | `web/app.py:63` | Localhost-only by design; server has no auth |
| Registries | provider & downloader plugin tables | `providers/__init__.py`, `downloaders/registry.py` | Code-level extension points |

> **Why this split?** Config covers "what do I want out"; the hard-coded layer
> covers "how the transcription sausage gets made." See the
> [2026-06-27 audit](journal/2026-06-27-transcription-landscape-and-config-audit.md)
> for which of these constants are worth promoting to config and which should
> stay fixed.

## CLI ↔ Web UI: shared backend, asymmetric surfaces

### Rule: neither surface shells out to the other

CLI commands (`cli/*.py`) and Web UI routes (`web/routes/*.py`) are both **thin adapters** over the same Python modules:

```
CLI (Typer) ─┐
              ├──→ core/ · providers/ · config/ · vault/ · downloaders/
Web UI ─────┘     (shared backend — single implementation)
(FastAPI)
```

`anyscribe "url"` and `POST /api/transcribe` both call `core/orchestrator.py::process()` directly. No subprocess layer. Add a provider in `providers/` and both surfaces pick it up; fix a bug in the orchestrator and both surfaces are fixed. Same applies to the MCP server (see decision above).

For flows where UX differs meaningfully across surfaces (onboarding being the main one), we extract a shared backend function into `core/` that all surfaces' flow controllers converge on — e.g. `core/onboard_headless.py::run_headless_onboard()` powers the CLI `--yes` path and the Web UI wizard save-phase.

### Feature-coverage matrix

Not every feature lives on every surface. The asymmetry is intentional per-feature; this matrix captures the current state.

| Feature | CLI | Web UI | Notes |
|---------|-----|--------|-------|
| Transcribe URL/file | ✓ | ✓ | Same `orchestrator.process()` on both |
| Duplicate detection (`cached`) + `--force` | ✓ (`--force`/`-f`) | ✓ ("Re-transcribe" on cached state) | Enforced in `orchestrator.process()` (dedup step 0), so all surfaces + MCP inherit it |
| Delete transcript | ✓ (`anyscribe rm`) | ✓ (delete in History) | Same `vault/index.py::delete_transcript`; also MCP `delete_transcript` tool |
| Cancel a running job | — | ✓ (`POST /api/jobs/{id}/cancel`, cooperative) | UI-only — a CLI run is cancelled with Ctrl+C |
| Onboard (first-run setup) | ✓ (TUI + `--yes` headless) | ✓ (wizard) | Both call `run_headless_onboard()` |
| Config read/write | ✓ (`anyscribe config`) | ✓ (Settings page) | Same `settings.load_config` / `save_config` |
| Provider test | ✓ (`anyscribe providers test`) | ✓ (Test/Diagnose buttons) | Same `/providers/{name}/test` logic |
| Local model mgmt | ✓ (`anyscribe model`) | ✓ (Models table) | Same `providers/local_models.py` |
| Local setup/teardown | ✓ (`anyscribe local`) | ✓ (Setup modal, Teardown button) | Same `core/local_setup.py` |
| History browse | Obsidian vault directly | ✓ (History page with search) | Web UI has richer UX; CLI leans on Obsidian |
| Progress | Terminal progress | ✓ (WebSocket) | Same `on_progress` callback |
| Batch processing | ✓ (`anyscribe batch`, `--timeout` per URL) | — | CLI-only. Add to UI if users ask |
| Download-only | ✓ (`anyscribe download`) | — | CLI-only |
| View recent activity | ✓ (`anyscribe logs`) | — | Reads workspace `daily/*.md` + recovery dir directly; UI already has richer History browsing |
| Local model download progress | — | ✓ (byte-level bar, `setup_progress`/`progress` on status polls) | UI-only — CLI shows NDJSON phase events, no byte counter |
| System diagnostics | ✓ (`anyscribe doctor`) | ✓ (Settings → System section, lighter) | UI surfaces a subset |
| Self-update | ✓ (`anyscribe update`) | — | CLI-only. Updating a running server is weird |
| Claude Code skill install | ✓ (`anyscribe install-skill`) | — | CLI-only; runs automatically anyway |
| Menu-bar tray + login auto-start | ✓ (`anyscribe tray`, `install-service`/`uninstall-service`) | — | CLI-only by nature — a tray icon and a launchd registration aren't Web UI concepts; the tray supervises the Web UI server, it doesn't compete with it |
| Drag-and-drop upload | — | ✓ | UI-only |
| API key management | ✓ (`anyscribe config set <prov>_api_key`) | ✓ (inline per-provider with Test) | UI has richer UX |

### When to place a feature on which surface

- **Both surfaces, default for core user-facing actions.** Transcribing, config changes, provider testing, onboarding — anything a human does often enough to want both a click and a script should live on both. The backend is shared; the cost of a second surface is just UX work.
- **CLI-only when it's operational/agentic by nature.** Batch processing, self-update, install scripts, CI-friendly doctor checks. These are things agents run or that belong in shell pipelines.
- **Web-UI-only when it's a visual interaction.** Drag-and-drop, rich history browsing with search/filter, inline masked-key management with visual feedback. CLI equivalents would be clunky.
- **Deliberate gaps are fine.** Not every CLI command needs a UI button; not every UI action needs a CLI equivalent. The rule is that the **primary flow for a given user archetype** (human / agent) should be fully sufficient on its native surface — we don't force humans into the CLI or agents into a browser.

When adding a new feature, decide surface coverage up front and note it in the commit message or PR description. If you're uncertain, default to building backend logic first (in `core/` or wherever fits) and adding the adapter(s) above — that way the other surface can get it later without refactoring.
