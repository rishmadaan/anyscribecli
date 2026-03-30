---
type: plan
tags: [workspace, structure, vault, obsidian, migration]
tldr: "Remove YYYY-MM-DD date folders from workspace and downloads — flatten to sources/<platform>/<slug>.md. Auto-migrate existing files on first run."
status: planned
---

# Plan: Flatten Workspace Structure — Remove Date Folders

## Context

Transcripts are currently stored as `sources/<platform>/YYYY-MM-DD/<slug>.md`. The date folder adds depth for no value — the transcription date isn't meaningful for organizing transcripts (it's already in frontmatter, the daily log, and the index). Removing it makes the Obsidian file tree cleaner and easier to browse.

**Before:** `~/anyscribe/sources/youtube/2026-03-30/i-spent-2-weeks-with-openclaw.md`
**After:** `~/anyscribe/sources/youtube/i-spent-2-weeks-with-openclaw.md`

Also flatten `~/.anyscribecli/downloads/` (audio/video) for consistency. Auto-migrate existing files out of date folders on first run.

## Implementation Steps

### Step 1: Flatten transcript paths in writer.py

**File:** `src/anyscribecli/vault/writer.py`

Remove `/ today` from the output directory construction (line 61):

```python
# Before:
out_dir = ws / "sources" / download.platform / today

# After:
out_dir = ws / "sources" / download.platform
```

The `today` variable is still needed for frontmatter (`date_processed`) — just not for the directory path.

Slug collision handling (lines 65-69) already works — it checks `out_path.exists()` in the same dir. Now scoped to the whole platform folder instead of just a date folder. The `-2`, `-3` suffix handles any collisions.

Also flatten the media retention paths:
- Line 128: `AUDIO_DIR / download.platform / today` → `AUDIO_DIR / download.platform`
- Line 171: `AUDIO_DIR / "local" / today` → `AUDIO_DIR / "local"`

### Step 2: Flatten download paths in download.py

**File:** `src/anyscribecli/cli/download.py`

- Line 80: `AUDIO_DIR / platform / today` → `AUDIO_DIR / platform`
- Line 154: `VIDEO_DIR / platform / today` → `VIDEO_DIR / platform`

### Step 3: Add migration to flatten existing date folders

**File:** `src/anyscribecli/core/migrate.py`

Add `maybe_flatten_date_folders()` — scans `sources/<platform>/` for YYYY-MM-DD subdirectories, moves files up, removes empty date dirs. Also flattens `downloads/audio/` and `downloads/video/`.

```python
def maybe_flatten_date_folders() -> int:
    """Move files from date subdirs up to platform level. Returns count moved."""
```

Helper `_flatten_dir(parent)` iterates platform dirs, finds date-pattern subdirs (`^\d{4}-\d{2}-\d{2}$`), moves files up with collision handling, removes empty date dirs.

### Step 4: Hook migration into orchestrator

**File:** `src/anyscribecli/core/orchestrator.py`

Call `maybe_flatten_date_folders()` alongside existing migrations. Print notice if files were moved.

### Step 5: Regenerate _index.md after migration

**File:** `src/anyscribecli/vault/index.py`

Add `rebuild_master_index()` — scans all `.md` files in `sources/`, reads frontmatter from each, rebuilds `_index.md` with correct relative links.

Call this from orchestrator after `maybe_flatten_date_folders()` returns > 0, so Obsidian wiki-links don't break.

**Note:** `update_master_index()` and `update_daily_log()` use `entry_path.relative_to(ws)` for links — these automatically work with the new flat paths, no changes needed for ongoing use.

### Step 6: Update documentation

Remove `YYYY-MM-DD/` from directory trees and path examples in:

| File | What to change |
|------|---------------|
| `README.md` | Workspace structure tree |
| `docs/user/configuration.md` | Workspace structure tree, file naming section |
| `docs/user/getting-started.md` | Example output path |
| `docs/user/commands.md` | Download output locations, JSON example |
| `src/anyscribecli/skill/references/config.md` | Workspace structure, organization text |
| `src/anyscribecli/skill/references/commands.md` | Download output locations |
| `docs/building/architecture.md` | Workspace structure diagram |

Do NOT update building journal entries (historical records).

## Files to Create/Modify

| Action | File | What |
|--------|------|------|
| **Edit** | `src/anyscribecli/vault/writer.py` | Remove `/today` from 3 path constructions |
| **Edit** | `src/anyscribecli/cli/download.py` | Remove `/today` from 2 path constructions |
| **Edit** | `src/anyscribecli/core/migrate.py` | Add `maybe_flatten_date_folders()` + `_flatten_dir()` |
| **Edit** | `src/anyscribecli/core/orchestrator.py` | Call flatten migration + index rebuild |
| **Edit** | `src/anyscribecli/vault/index.py` | Add `rebuild_master_index()` |
| **Edit** | 7 doc/skill files | Remove YYYY-MM-DD from directory trees and paths |

## Verification

1. **Fresh transcription:** `ascli transcribe "<url>"` → file at `sources/youtube/<slug>.md` (no date folder)
2. **Migration:** Existing `sources/youtube/2026-03-30/*.md` files move to `sources/youtube/`, date folder deleted
3. **Index rebuild:** `_index.md` links point to correct flat paths after migration
4. **Slug collision:** Two videos with similar titles → second gets `-2` suffix
5. **Downloads:** `ascli download "<url>"` → `downloads/video/youtube/<slug>.mp4` (no date folder)
6. **Daily log:** Still at `daily/YYYY-MM-DD.md` (unchanged — daily logs are independent)
