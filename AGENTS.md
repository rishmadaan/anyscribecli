# anyscribecli — Agent Directives

## Before Starting Work

1. Read `CLAUDE.md` for architecture and patterns
2. Read `docs/building/_index.md` for recent project history
3. If your task touches providers or downloaders, read the relevant living doc
4. Check `docs/building/journal/` for any recent entries related to your task area

## Memory Layer

`docs/building/journal/` is the project memory. It exists so that agents in future sessions have context about past decisions, bugs, and research.

### Reading memory (before work)

- Scan `docs/building/_index.md` — it's a newest-first table of all entries
- Read any entries tagged with your task area
- This prevents re-investigating solved problems or re-debating settled decisions

### Writing memory (after work)

After completing significant work, create a journal entry:

```
docs/building/journal/YYYY-MM-DD-<descriptive-slug>.md
```

With frontmatter:
```yaml
---
type: decision|research|troubleshooting|learning
tags: [relevant, tags]
tldr: "One-line summary"
---
```

Then prepend a row to `docs/building/_index.md`.

## Post-Commit Checklist

**After every significant commit**, follow `docs/building/COMMIT_CHECKLIST.md`. It has per-scenario checklists (new command, new provider, new downloader, version bump) and grep commands to catch stale references. This is mandatory.

## Documentation Requirements

### Developer docs (`docs/building/`)
- Every PR or significant change MUST include a building doc update
- If you changed architecture: update `docs/building/architecture.md`
- If you added/changed a provider: update `docs/building/providers.md`
- If you added/changed a downloader: update `docs/building/downloaders.md`
- If you made a non-trivial decision: write a journal entry explaining why

### User docs (`docs/user/`)
- If you added/changed a user-facing command or flag: update `docs/user/commands.md`
- If you changed config options: update `docs/user/configuration.md`
- If you changed the onboarding flow: update `docs/user/getting-started.md`
- User docs target semi-technical users new to CLI — explain jargon, show examples, include troubleshooting
- Every user doc has frontmatter: `summary`, `read_when`, `title`

## Quick Context

- CLI entry point: `src/anyscribecli/cli/main.py`
- Onboarding + provider info: `src/anyscribecli/cli/onboard.py`
- Config/providers commands: `src/anyscribecli/cli/config_cmd.py`
- Download command: `src/anyscribecli/cli/download.py`
- Batch processing: `src/anyscribecli/cli/batch.py`
- Config loading: `src/anyscribecli/config/settings.py`
- Path constants: `src/anyscribecli/config/paths.py`
- Provider ABC + registry: `src/anyscribecli/providers/base.py`, `providers/__init__.py`
- Downloader ABC + registry: `src/anyscribecli/downloaders/base.py`, `downloaders/registry.py`
- Core flow: `src/anyscribecli/core/orchestrator.py`
- Dependency checker: `src/anyscribecli/core/deps.py`
- Update system: `src/anyscribecli/core/updater.py`
- Web UI backend: `src/anyscribecli/web/app.py` (FastAPI factory + static serving)
- Web UI routes: `src/anyscribecli/web/routes/` (transcribe, history, config, health, system)
- Web UI job manager: `src/anyscribecli/web/jobs.py` (ThreadPoolExecutor + asyncio bridge)
- Frontend source: `ui/` (React + TypeScript + Vite, builds to `web/static/`)

## Key Dependencies

- `beaupy` — arrow-key selectors in onboarding wizard
- `yt-dlp` — YouTube + Instagram downloader (subprocess; cookies via `--cookies-from-browser` for IG)
- `faster-whisper` — local transcription (optional, only for `local` provider)

## Cross-Platform

All code must work on macOS and Linux. Use `pathlib.Path` everywhere. No platform-specific assumptions.
