---
type: project-note
tags: [web-ui, settings, ux, diarization]
tldr: "v0.7.4.1 — web UI gains inline provider API key setup; Settings UX polished; Diarization toggle removed in favor of auto-coupling with output format (matches CLI)."
---

# v0.7.4.1 — Web UI Settings Polish

**Date:** 2026-04-18

## What changed

Follow-up polish release for v0.7.4's web UI, focused on the Settings page and diarization UX consistency.

- **Inline provider API key setup** — each provider row in Settings now has a key icon that expands an input to paste/save/replace an API key directly from the GUI. No more "go run `scribe config set openai_api_key ...` in a terminal" mid-flow.
- **"General" → "Configure Defaults"** — the generic section label didn't convey what it was for; new label makes it clear these are the defaults used when the user doesn't specify on a per-job basis.
- **Diarization toggle removed** — previously the UI had a standalone Diarization checkbox *and* an output-format selector, which let users create inconsistent states (e.g. diarize on, output format `plain`). Now the output format selector is the single source of truth: picking `diarized` enables diarization, anything else disables it. This mirrors CLI behavior where `--diarize` implies diarized output.
- **Backend match** — `routes/transcribe.py` now promotes `output_format` to `"diarized"` whenever `diarize=true` is submitted, so API clients passing the old shape get the correct result instead of silently dropping speaker info.

## Why

v0.7.4 shipped the web UI but Settings still pushed users back to the terminal for API key setup — the one step that matters most for onboarding. And the standalone diarize toggle was a footgun inherited from an early sketch: it let the UI promise "diarized output" without actually requesting diarized format from the backend.

## Files touched

- `ui/src/pages/SettingsPage.tsx` — expandable per-provider key input, relabel
- `src/anyscribecli/web/routes/transcribe.py` — auto-promote output_format when diarize=true
- `src/anyscribecli/web/static/` — rebuilt bundle
- Version bump in `__init__.py` + `pyproject.toml`

## Release note

Tag `v0.7.4.1` was initially missed on push — pushed manually afterwards, which triggered the PyPI publish workflow. Reminder: `scripts/release.sh` pushes the tag; if you bump version manually, `git push --tags` separately.
