---
type: project-note
tags: [deepgram, hi-latn, hindi, nova, nova-3, model-fallback, bug-fix]
tldr: "Deepgram Nova 3 doesn't support hi-Latn — auto-falls back to Nova model. Deepgram's error message ('try 2-general') is misleading; tested all model variants to find the correct one."
---

# v0.7.2.2–v0.7.2.3 — Deepgram hi-Latn Nova Fallback + Skill Defaults

## Context

User transcribed a Hindi meeting with `scribe --diarize --language hi-Latn`. Deepgram returned 400: "No such model/language/tier combination found. You could try the '2-general' model."

The error message was misleading — `2-general` also doesn't work with hi-Latn.

## Problem

`_build_params()` in `providers/deepgram.py` hardcoded `model=nova-3`. Nova 3 doesn't support the `hi-Latn` language code.

## Root Cause

Deepgram's `nova-3` model doesn't include Hindi Latin script (`hi-Latn`) in its supported languages. This language code only works with the original `nova` model.

## Approach Taken

1. First tried `2-general` (as Deepgram's error suggested) — still 400
2. Then tried `nova-2` based on web research — still 400
3. Made a real API call testing all model variants (`nova`, `nova-general`, `general`, `2-general`, `nova-2`, `nova-2-general`) with a test audio file
4. Results: `nova`, `nova-general`, `general`, `nova-2`, `nova-2-general` all returned 200. Only `2-general` failed.
5. Chose `nova` as the fallback — the simplest name that works

## Obstacles & Resolutions

| Obstacle | Cause | Resolution |
|----------|-------|------------|
| Deepgram error suggests `2-general` | Misleading error message in Deepgram's API | Tested all variants directly against the API |
| Fix didn't take effect in venv | Global `scribe` binary was on PATH before venv's | `pip install -e .` in the venv to create venv-local entry point |
| Fix still didn't take effect after venv activation | Stale installed package (v0.5.1) in venv | `pip install -e .` replaced it with editable v0.7.2.1 |

## Fix

`providers/deepgram.py` `_build_params()`:
```python
model = "nova" if language.lower() in {"hi-latn"} else "nova-3"
```

Case-insensitive check on the language code. Falls back to the original `nova` model for hi-Latn, uses `nova-3` for everything else.

## v0.7.2.3 — Skill + Docs Update

Updated the Claude Code skill to make `--diarize --language hi-Latn` the **default recommendation** for Hindi multi-speaker content (not just an option). Updated all user docs, building docs, and skill references with the Nova fallback behavior and version strings.

## Notes

- Deepgram's error messages for unsupported model/language combos are not reliable — always test against the actual API
- The `nova` model is older than `nova-3` but still functional and maintained
- `hi-Latn` may eventually be added to `nova-3`, at which point the fallback can be removed
