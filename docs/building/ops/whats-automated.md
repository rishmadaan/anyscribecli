---
type: reference
tags: [automation, updater, doctor, internals, maintenance]
tldr: "What the app already handles automatically — update detection, self-update, install type detection, doctor checks — and what remains manual."
---

# What's Automated vs Manual

This doc explains what anyscribe already does automatically behind the scenes, so you know what's handled and what needs your attention.

---

## Automated: Self-Update System

**File:** `src/anyscribe/core/updater.py`

The app has a built-in self-update system that users interact with via `scribe update`.

### Install Type Detection

The updater auto-detects how the user installed the app:

- **Git install** — if the package directory lives inside a `.git` repo (developer workflow, editable installs)
- **Pip install** — everything else (standard user installs from PyPI or `git+https://`)

Detection is fully automatic. No config needed.

### What `scribe update` Does

**For git installs:**
1. Checks for uncommitted changes (aborts if found, unless `--force`)
2. With `--force`: stashes local changes first
3. Runs `git fetch` → `git pull --rebase`
4. Reinstalls with `pip install -e .`
5. Reads new version from disk (Python caches the module, so re-import wouldn't work)
6. Reports old → new version

**For pip installs:**
1. Runs `pip install --upgrade anyscribe` (tries PyPI first)
2. If PyPI fails: falls back to `git+https://github.com/rishmadaan/anyscribe.git`
3. Spawns a subprocess to read the new version (avoids module cache)
4. Reports old → new version

### What `scribe update --check` Does

Checks for available updates **without installing**:

- **Git:** fetches remote, checks `git log HEAD..origin/main` for new commits, reads remote `__init__.py` for version
- **Pip:** runs `pip index versions anyscribe` to check PyPI for latest

### Timeouts

All operations have timeouts to prevent hanging:

| Operation | Timeout |
|-----------|---------|
| `git fetch` | 30s |
| `git log`, `git show`, `git status` | 10s |
| `git pull --rebase` | 60s |
| `pip install` / `pip upgrade` | 120s |
| Version read subprocess | 10s |

---

## Automated: Doctor Command

**File:** `src/anyscribe/cli/main.py`

`scribe doctor` runs a health check that includes:

- Dependency checks (yt-dlp, ffmpeg, etc.)
- Config validation
- Workspace integrity
- **Silent update check** — calls `check_for_updates(quiet=True)`, only prints if an update is available

This is the only place the app checks for updates without the user explicitly running `scribe update`.

---

## Automated: Version Display

`scribe --version` (or `scribe -v`) reads from `src/anyscribe/__init__.py:__version__` and prints it.

---

## Automated: PyPI Publishing

**File:** `.github/workflows/publish.yml`

When you push a tag matching `v*`, GitHub Actions automatically:
1. Builds the package (`python -m build`)
2. Verifies the tag matches `pyproject.toml` version (fails if mismatched)
3. Publishes to PyPI via trusted publishing (no API token in secrets needed after setup)

**Setup (one-time):** Configure trusted publishing on [pypi.org](https://pypi.org/manage/project/anyscribe/settings/publishing/) — add GitHub as a trusted publisher with repository `rishmadaan/anyscribe`, workflow `publish.yml`.

### Release Script

**File:** `scripts/release.sh`

One command to bump + commit + tag + push:
```bash
./scripts/release.sh 0.5.0 "description of changes"
```

Includes safety checks: clean working tree, semver format, no duplicate tags, branch warning.

---

## Automated: CI Checks

GitHub Actions runs lint, tests, and package build on pushes to `main` and pull requests. It also rebuilds the frontend and verifies the committed `src/anyscribe/web/static/` bundle is current.

---

## NOT Automated (You Do These Manually)

### GitHub Releases

No automation. Optionally create with:
```bash
gh release create vX.Y.Z --title "..." --notes "..."
```

### Documentation Updates

All docs are manual. No auto-generation for:
- User docs (`docs/user/`)
- Building docs (`docs/building/`)
- README
- Changelog

The `COMMIT_CHECKLIST.md` exists as a reminder, but it's your discipline that enforces it.

---

## What Users Experience

From a user's perspective, the update flow is:

```
scribe doctor          # Tells them if an update is available (passively)
scribe update --check  # Explicitly check
scribe update          # Install the update
scribe --version       # Verify
```

There are **no automatic updates**, **no background checks**, **no telemetry**, and **no phone-home behavior**. The user is always in control.

---

## Future Automation Candidates

Things that could be automated but aren't yet:

| What | How | Priority |
|------|-----|----------|
| Version sync check | Pre-commit hook comparing both files | Medium |
| Changelog generation | From git tags/commits | Low |
| Startup update notification | Opt-in check on `scribe` launch with TTL | Low |
