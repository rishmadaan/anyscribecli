---
type: project-note
tags: [documentation, accuracy, audit]
tldr: Full documentation audit and fix — 16 issues across README, user docs, and building docs corrected for accuracy against actual code
---

# v0.3.1 — Documentation Accuracy Audit

## What happened

Audited all documentation (README, 4 user docs, 3 building docs) against the actual codebase. Found 16 discrepancies ranging from fabricated terminal output to wrong file paths.

## Issues fixed

### High priority
1. **getting-started.md** — Sample terminal output was completely fabricated. Replaced with actual CLI output format (`Transcription saved: <path>` + Title/Duration/Language/Words)
2. **configuration.md** — `keep_media` path was wrong: said `workspace/media/YYYY-MM-DD/`, actually `media/audio/<platform>/YYYY-MM-DD/`
3. **getting-started.md** — "alongside your transcripts" misleadingly implied audio saved in the vault

### Medium priority
4. **getting-started.md** — Provider order in wizard had ElevenLabs/OpenRouter swapped vs actual `PROVIDER_INFO` dict order
5. **providers.md** (user + building) — ElevenLabs "3 GB file limit" was misleading; ascli chunks at 25 MB via `WHISPER_MAX_BYTES`
6. **configuration.md** — Workspace structure diagram issue (workspace/media/ created by scaffold but unused). Diagram was actually correct; the scaffold creates a dead dir.
7. **architecture.md** — `--json`/`--quiet` described as "global flags" but they're per-command options
8. **downloaders.md** — Instagram URL patterns omitted username-prefixed variants (`instagram.com/<user>/reel/`)

### Low priority
9. **commands.md** — `ascli config path` subcommand missing from overview table
10. **commands.md** — `--json` flag on `providers list` and `config show` undocumented; added flags tables
11. **commands.md** — `doctor` check list omitted "Workspace index" check
12. **commands.md** — `download` save path missing `<platform>/YYYY-MM-DD/` structure
13. **providers.md** — ElevenLabs "Scribe v2 also available" removed (no mechanism to select it)
14. **providers.md** — OpenRouter file limit described as "context window" but it uses same 25 MB chunking
15. **building/providers.md** — Sargam `saaras:v2` model name added
16. **README.md** — Added download options, batch options (including `--stop-on-error`), `config path` to commands table, fixed "--json on every command" claim

## Version bump

0.3.0 → 0.3.1 (patch: documentation-only fixes, no code changes)

## Lesson

Documentation written before the code is finalized drifts. Terminal output examples especially — they should be copy-pasted from actual runs, not written from memory. File paths should cross-reference `paths.py` directly.
