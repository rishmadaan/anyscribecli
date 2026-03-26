# anyscribecli — AI Developer Instructions

## What This Is

A Python CLI tool (`ascli`) that downloads video/audio from YouTube/Instagram, transcribes it via API, and outputs structured markdown into an Obsidian vault at `~/.anyscribecli/workspace/`.

## Architecture

```
src/anyscribecli/
├── cli/           # Typer commands (main.py, onboard.py, transcribe.py, config_cmd.py)
├── config/        # Paths + settings (paths.py, settings.py)
├── downloaders/   # Platform downloaders (base.py, youtube.py, instagram.py, registry.py)
├── providers/     # Transcription APIs (base.py, openai.py, openrouter.py, ...)
├── vault/         # Obsidian vault management (scaffold.py, writer.py, index.py)
└── core/          # Orchestration + audio processing (orchestrator.py, audio.py)
```

Flow: `CLI command -> orchestrator -> downloader + provider -> vault writer -> index update`

## Key Patterns

- **Providers** implement `TranscriptionProvider` ABC from `providers/base.py`
- **Downloaders** implement `AbstractDownloader` ABC from `downloaders/base.py`
- **Config** lives at `~/.anyscribecli/config.yaml`, API keys in `~/.anyscribecli/.env`
- **All paths** use `pathlib.Path` via `config/paths.py` — no hardcoded separators
- **CLI output** is human-readable by default, `--json` flag for machine/agent consumption
- **Audio params** optimized for Whisper: 16kHz, mono, 64kbps mp3
- **Files >25MB** are chunked into 18-min segments before transcription

## Documentation Ethic

This project maintains a developer memory layer at `docs/building/`. This is mandatory, not optional.

### When to write a building doc entry

- After completing a significant feature or change
- After making an architecture decision
- After debugging a non-trivial issue
- After researching alternatives and choosing one

### How to write one

1. Create `docs/building/journal/YYYY-MM-DD-<slug>.md` with frontmatter (type, tags, tldr)
2. Update `docs/building/_index.md` with a new row (newest first)
3. Update relevant living docs (`architecture.md`, `providers.md`, `downloaders.md`) if the change affects them

### Living docs vs journal entries

- **Living docs** (`architecture.md`, `providers.md`) reflect current state — update in place
- **Journal entries** preserve historical decisions — append only, never edit old entries

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
