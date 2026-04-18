# anyscribecli — AI Developer Instructions

## What This Is

A Python CLI tool (`scribe`) that downloads video/audio from YouTube/Instagram, transcribes it via API, and outputs structured markdown into an Obsidian vault at `~/anyscribe/` (configurable via `workspace_path` in config). The PyPI package is `anyscribecli`; the CLI command is `scribe` (with `ascli` as a backward-compatible alias).

## Architecture

```
src/anyscribecli/
├── cli/           # Typer commands (main.py, onboard.py, transcribe.py, download.py, batch.py, config_cmd.py)
├── config/        # Paths + settings (paths.py, settings.py)
├── downloaders/   # Platform downloaders (base.py, youtube.py, instagram.py, registry.py)
├── providers/     # Transcription APIs (base.py, openai.py, openrouter.py, elevenlabs.py, sargam.py, local.py)
├── vault/         # Obsidian vault management (scaffold.py, writer.py, index.py)
├── core/          # Orchestration + audio + deps + updater + migrations (orchestrator.py, audio.py, deps.py, updater.py, migrate.py)
└── web/           # Web UI — FastAPI backend + built React SPA (app.py, jobs.py, routes/, static/)

ui/                # Frontend source (React + TypeScript + Vite + Tailwind) — builds to web/static/
```

Flow: `CLI command -> orchestrator -> downloader + provider -> vault writer -> index update`
Web flow: `Browser (React SPA) <-> FastAPI REST + WebSocket <-> orchestrator (same core logic)`

## Claude Code Skill — Primary Usage Path

The Claude Code skill (`src/anyscribecli/skill/`) is the **primary way users interact with anyscribe**. Most users invoke scribe through Claude Code rather than typing CLI commands directly. This means:

- **The skill files are first-class artifacts**, not an afterthought. Treat them with the same rigor as the CLI source code.
- **Keep the skill in sync with every CLI change.** If you add/change a command, flag, provider, or behavior, update the corresponding skill files in the same commit:
  - `skill/SKILL.md` — operator guide (command table, safety rules, decision tree)
  - `skill/references/commands.md` — full command reference with examples
  - `skill/references/providers.md` — provider comparison and switching
  - `skill/references/config.md` — configuration and workspace details
  - `skill/references/troubleshooting.md` — common errors and fixes
- **Stale skill docs = broken product.** If Claude Code gives users outdated commands or wrong flags because the skill wasn't updated, that's a bug — same severity as a broken CLI command.

## Key Patterns

- **Providers** implement `TranscriptionProvider` ABC from `providers/base.py` (5 active: openai, elevenlabs, openrouter, sargam, local)
- **Downloaders** implement `AbstractDownloader` ABC from `downloaders/base.py` (youtube, instagram)
- **Config** at `~/.anyscribecli/config.yaml` — secrets in `.env` (API keys, Instagram password)
- **All paths** use `pathlib.Path` via `config/paths.py` — no hardcoded separators
- **CLI output** human-readable by default, `--json` flag for machine/agent consumption
- **Interactive prompts** use `beaupy` (arrow-key selectors) for onboarding, `typer.prompt` for text input
- **URL input** three methods: quoted argument (primary), interactive prompt (fallback), clipboard
- **Workspace** at `~/anyscribe/` (configurable) — pure markdown Obsidian vault, resolved via `get_workspace_dir()` in `config/paths.py`
- **Downloads outside vault** — audio in `~/.anyscribecli/downloads/audio/`, video in `downloads/video/`
- **Audio params** optimized for Whisper: 16kHz, mono, 64kbps mp3
- **Chunking** — 18-min segments for Whisper (25MB limit), 30s segments for Sarvam (REST API limit)
- **Web UI** — `scribe ui` launches FastAPI + built React SPA at `127.0.0.1:8457`. REST API for config/history, WebSocket for real-time transcription progress. Frontend source in `ui/`, builds to `src/anyscribecli/web/static/`. Server stashed on `app.state` for graceful `/shutdown`. Orchestrator accepts optional `on_progress` callback — web layer bridges sync→async via ThreadPoolExecutor + asyncio.Queue

## Documentation Ethic

This project maintains TWO documentation layers. Both are mandatory, not optional.

### 1. Developer memory layer (`docs/building/`)

For developers and AI agents working on the codebase.

**When to write a building doc entry:**
- After completing a significant feature or change
- After making an architecture decision
- After debugging a non-trivial issue
- After researching alternatives and choosing one

**How to write one:**
1. Create `docs/building/journal/YYYY-MM-DD-<slug>.md` with frontmatter (type, tags, tldr)
2. Update `docs/building/_index.md` with a new row (newest first)
3. Update relevant living docs (`architecture.md`, `providers.md`, `downloaders.md`) if the change affects them

**Living docs vs journal entries:**
- **Living docs** (`architecture.md`, `providers.md`) reflect current state — update in place
- **Journal entries** preserve historical decisions — append only, never edit old entries

### 2. User documentation (`docs/user/`)

For end users — assume a **semi-technical audience who may be new to CLI tools**. This is critical.

**Files:**
- `getting-started.md` — 5-minute install-to-first-transcription guide
- `commands.md` — complete command reference with examples
- `configuration.md` — all settings explained with context
- `providers.md` — provider comparison: features, pricing, languages, when to use each

**User doc standards:**
- Every doc has YAML frontmatter: `summary`, `read_when` (list of when to read this), `title`
- Lead with the command, explain after — show what to type before explaining why
- Use `>` blockquotes for tips, warnings, and "new to this?" asides
- Include copy-paste-ready examples for every command and flag
- Explain jargon when first used (e.g., "slug", "frontmatter", "editable install")
- Troubleshooting section with common errors and plain-English fixes
- Write for someone who can follow instructions but doesn't know CLI conventions

**When to update user docs:**
- Adding a new command → update `commands.md`, add to overview table
- Adding a new flag → update the flags table in `commands.md`
- Changing config options → update `configuration.md`
- Changing onboarding flow → update `getting-started.md`
- Adding a new platform/provider → update `providers.md` and relevant sections in other docs

**Never skip user docs.** If you add a feature users interact with, the user docs must be updated in the same commit.

## Adding a New Provider

1. Create `src/anyscribecli/providers/<name>.py` implementing `TranscriptionProvider`
2. Register it in `providers/__init__.py` PROVIDER_REGISTRY
3. Add any new env vars to the onboarding wizard
4. Update `docs/building/providers.md`
5. Write a journal entry explaining the decision

## Adding a New Downloader

1. Create `src/anyscribecli/downloaders/<name>.py` implementing `AbstractDownloader`
2. Register it in `downloaders/registry.py` DOWNLOADERS list
3. Update URL detection regex in `registry.py`
4. Update `docs/building/downloaders.md`

## Post-Commit Checklist

**After every significant commit**, follow `docs/building/COMMIT_CHECKLIST.md`. It ensures README, user docs, building docs, and version references stay in sync with code. This is mandatory — stale docs are bugs.

## Versioning

SemVer: `MAJOR.MINOR.PATCH`. See `BACKLOG.md` for the full version roadmap.

Version lives in TWO places that must match: `src/anyscribecli/__init__.py` and `pyproject.toml`.

```bash
# One-command release (bumps both files, commits, tags, pushes → triggers PyPI publish):
./scripts/release.sh X.Y.Z "description"
```

### Version Tag Checklist

**Every time a git tag is created (any version bump), you MUST also update:**

1. `src/anyscribecli/__init__.py` — `__version__` matches the tag
2. `pyproject.toml` — `version` field matches the tag
3. `BACKLOG.md` — version table updated, release section added/updated
4. `docs/building/_index.md` — new row if there's a building journal entry
5. `docs/building/journal/` — new entry for significant changes
6. All docs with hardcoded version strings (grep for the old version)
7. Skill files if behavior changed

**Do not create a tag without updating these files.** Stale version metadata is a bug.

## Testing

```bash
pytest                    # run all tests
ruff check src/           # lint
ruff format src/          # format
```

## Do Not

- Import from project root — use `from anyscribecli.x.y import z`
- Hardcode paths — use `config/paths.py`
- Skip documentation — every significant change gets a building doc entry
- Add features beyond what was asked — lean first, expand later
