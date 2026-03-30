# anyscribecli — AI Developer Instructions

## What This Is

A Python CLI tool (`ascli`) that downloads video/audio from YouTube/Instagram, transcribes it via API, and outputs structured markdown into an Obsidian vault at `~/anyscribe/` (configurable via `workspace_path` in config).

## Architecture

```
src/anyscribecli/
├── cli/           # Typer commands (main.py, onboard.py, transcribe.py, download.py, batch.py, config_cmd.py)
├── config/        # Paths + settings (paths.py, settings.py)
├── downloaders/   # Platform downloaders (base.py, youtube.py, instagram.py, registry.py)
├── providers/     # Transcription APIs (base.py, openai.py, openrouter.py, elevenlabs.py, sargam.py, local.py)
├── vault/         # Obsidian vault management (scaffold.py, writer.py, index.py)
└── core/          # Orchestration + audio + deps + updater (orchestrator.py, audio.py, deps.py, updater.py)
```

Flow: `CLI command -> orchestrator -> downloader + provider -> vault writer -> index update`

## Key Patterns

- **Providers** implement `TranscriptionProvider` ABC from `providers/base.py` (5 active: openai, elevenlabs, openrouter, sargam, local)
- **Downloaders** implement `AbstractDownloader` ABC from `downloaders/base.py` (youtube, instagram)
- **Config** at `~/.anyscribecli/config.yaml` — secrets in `.env` (API keys, Instagram password)
- **All paths** use `pathlib.Path` via `config/paths.py` — no hardcoded separators
- **CLI output** human-readable by default, `--json` flag for machine/agent consumption
- **Interactive prompts** use `beaupy` (arrow-key selectors) for onboarding, `typer.prompt` for text input
- **URL input** three methods: quoted argument (primary), interactive prompt (fallback), clipboard
- **Workspace** at `~/anyscribe/` (configurable) — pure markdown Obsidian vault, resolved via `get_workspace_dir()` in `config/paths.py`
- **Media outside vault** — audio in `~/.anyscribecli/media/audio/`, video in `media/video/`
- **Audio params** optimized for Whisper: 16kHz, mono, 64kbps mp3
- **Chunking** — 18-min segments for Whisper (25MB limit), 30s segments for Sarvam (REST API limit)

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

Version lives in **one place**: `src/anyscribecli/__init__.py`. The `pyproject.toml` also has a version field that must match — update both when bumping.

```bash
# After changing version in __init__.py AND pyproject.toml:
git add -A && git commit -m "Bump version to X.Y.Z"
git tag vX.Y.Z
```

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
