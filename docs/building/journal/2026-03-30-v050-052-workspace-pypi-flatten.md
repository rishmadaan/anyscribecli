---
type: project-note
tags: [workspace, pypi, migration, structure, automation, release]
tldr: "v0.5.0–v0.5.2 — configurable workspace path, PyPI automation via GitHub Actions, media→downloads rename, flattened workspace structure (removed date folders). Three migrations, one release script."
---

# v0.5.0–v0.5.2: Workspace Path, PyPI Automation, Flatten Structure

## What Changed

Three rapid releases that cleaned up the project's file organization and distribution:

### v0.5.0 — Configurable workspace + PyPI automation

**Workspace path:** Moved default from hidden `~/.anyscribecli/workspace/` to visible `~/anyscribe/`. Added `workspace_path` config option for custom locations. Auto-migrates legacy path on first run via `maybe_migrate_workspace()`.

**PyPI automation:** Added `.github/workflows/publish.yml` — trusted publishing triggered by `v*` tag push. Created `scripts/release.sh` for one-command releases (validates semver, checks clean tree, bumps version in both `__init__.py` and `pyproject.toml`, commits, tags, pushes). Version mismatch between tag and pyproject.toml fails the build.

### v0.5.1 — Rename media/ to downloads/

User feedback: `~/.anyscribecli/media/` is counterintuitive when the workspace is elsewhere. Renamed to `~/.anyscribecli/downloads/` with `DOWNLOADS_DIR`, `AUDIO_DIR`, `VIDEO_DIR` constants. Migration via `maybe_migrate_media_to_downloads()`.

### v0.5.2 — Flatten workspace structure

Removed `YYYY-MM-DD` date folders from all paths:
- Before: `sources/youtube/2026-03-30/slug.md`
- After: `sources/youtube/slug.md`

Flattened workspace sources, downloads/audio, and downloads/video. Migration via `maybe_flatten_date_folders()` + `_flatten_dir()` helper — scans for date-pattern subdirs, moves files up with collision handling, removes empty dirs. `rebuild_master_index()` regenerates `_index.md` by scanning all transcript frontmatter.

## Migration Architecture

All three migrations follow the same pattern:
1. Check precondition (legacy path exists, target doesn't)
2. Move files atomically
3. Return a count/bool so orchestrator can print a notice
4. Called at startup in `orchestrator.py` before any processing

Migrations are idempotent — safe to run repeatedly. Once migrated, the precondition check short-circuits.

## Files Modified

| File | What |
|------|------|
| `config/paths.py` | `DEFAULT_WORKSPACE`, `DOWNLOADS_DIR`, `LEGACY_*` constants |
| `core/migrate.py` | 3 migration functions + `_flatten_dir()` helper |
| `core/orchestrator.py` | Calls all migrations at startup |
| `vault/writer.py` | Removed `/ today` from 3 path constructions |
| `vault/index.py` | Added `rebuild_master_index()` |
| `cli/download.py` | Removed `/ today` from 2 path constructions |
| `.github/workflows/publish.yml` | New — trusted publishing workflow |
| `scripts/release.sh` | New — one-command release script |
| 7 doc/skill files | Updated paths, directory trees, examples |

## Key Decision

Chose GitHub Actions over git hooks for PyPI publishing:
- Hooks are local-only (don't transfer to clones or GitHub Desktop)
- Every push would trigger a publish attempt (not just version bumps)
- Actions are visible, auditable, and run in CI

## Verification

Tested all three migrations against real workspace data (4 transcripts, 4 audio files). All files moved correctly, index rebuilt with correct links, lint passes clean.
