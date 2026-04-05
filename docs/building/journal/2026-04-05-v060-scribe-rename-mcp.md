---
type: project-note
tags: [v0.6.0, scribe, mcp, cli-rename, skill-auto-update, ai-first]
tldr: "v0.6.0 — Renamed CLI to `scribe` with bare-URL routing, added MCP server (9 tools, 3 resources), skill auto-install/update via .version marker, published to PyPI."
---

# v0.6.0 — scribe Rename, MCP Server, Skill Auto-Update

## What Changed

### CLI Rename: `ascli` -> `scribe`

- Primary entry point is now `scribe` (PyPI package remains `anyscribecli`)
- `ascli` kept as backward-compatible alias in `pyproject.toml`
- Renamed all user-facing strings across CLI source, error messages, help text
- Skill files updated to reference `scribe` throughout

### Bare URL Routing

`scribe "https://..."` now works directly — no `transcribe` subcommand needed.

Implementation: `DefaultToTranscribe(TyperGroup)` class in `main.py`. If the first argument isn't a known subcommand or flag, prepends `transcribe` to the args list. Must subclass `typer.core.TyperGroup` (not `click.Group`) — Typer asserts this at startup.

All subcommands (`config`, `batch`, `download`, etc.) work unchanged. Explicit `scribe transcribe "url"` still works too.

### Skill Auto-Install (AI-First)

If `~/.claude/` exists (Claude Code is installed), the skill is automatically installed on first CLI invocation. No opt-in, no prompt. Removed the onboarding opt-in question.

Rationale: anyscribe is an AI-first app — most users interact via Claude Code, not CLI directly. The skill should always be present.

### Skill Auto-Update (.version marker)

Borrowed from gitstow's `_auto_update_skill()` pattern:

1. `copy_skill_files()` writes a `.version` marker to `~/.claude/skills/scribe/.version`
2. On every CLI invocation, `_auto_update_skill()` reads the marker
3. If version mismatch → silently re-copies all skill files
4. If skill directory doesn't exist but `~/.claude/` does → auto-install
5. One-time migration: removes old `~/.claude/skills/ascli/` and installs to `~/.claude/skills/scribe/`

Cost: one file read + string compare per invocation. Never blocks CLI on failure (wrapped in try/except).

### `scribe doctor` Skill Health Check

New section 4 in doctor output reports:
- Skill installed status and version
- Whether it's current, outdated, or unknown (pre-0.5.5)
- Suggests `scribe install-skill --force` if stale

### MCP Server

New `src/anyscribecli/mcp/server.py` with `scribe-mcp` entry point.

**9 tools:** transcribe, batch_transcribe, download, list_transcripts, get_config, set_config, list_providers, test_provider, doctor

**3 resources:** scribe://config, scribe://providers, scribe://workspace

Install: `pip install anyscribecli[mcp]` (adds `mcp>=1.0` dependency)

Pattern follows gitstow: MCP calls core modules directly (orchestrator, settings, providers), not CLI commands. All tools return JSON. Consistent error handling (`{"success": false, "error": "..."}`).

### TyperGroup Fix

`DefaultToTranscribe` originally subclassed `click.Group`. Typer v0.9+ asserts `cls` must be a `TyperGroup` subclass. Fixed by importing `from typer.core import TyperGroup`.

## Files Changed

- `src/anyscribecli/cli/main.py` — DefaultToTranscribe, _auto_update_skill, doctor skill check
- `src/anyscribecli/cli/skill_cmd.py` — .version marker write, quiet param
- `src/anyscribecli/cli/onboard.py` — removed skill opt-in, auto-install instead
- `src/anyscribecli/config/paths.py` — skill target path updated to scribe
- `src/anyscribecli/mcp/server.py` — new MCP server (9 tools, 3 resources)
- `src/anyscribecli/skill/` — all skill docs renamed ascli → scribe
- `pyproject.toml` — scribe + scribe-mcp entry points, mcp optional dep
- All CLI source files — user-facing ascli → scribe
