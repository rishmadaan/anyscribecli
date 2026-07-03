---
type: feature
tags: [audit, dedup, cache, delete, orchestrator, mcp, web-ui, testing, groq]
tldr: "v0.11.0 lifecycle release. Audit caught a download-command crash (shipped because untested) and a Groq provider-test that never checked its key. Adds duplicate detection (frontmatter scan, no cache file, enforced in the orchestrator so every surface inherits it) with a --force override, a scribe rm delete command with index resync across CLI/Web UI/MCP, and a cooperative Web UI job-cancel. Plus the first orchestrator integration test."
---

# Audit fixes + transcript lifecycle (dedup, delete)

**Date:** 2026-07-03
**Version:** 0.11.0
**Follows:** the [2026-06-29 quality picker](2026-06-29-quality-picker.md)

## The audit that started it

A pass over the CLI surface turned up two bugs that had shipped silently:

- **`scribe download` crashed on every invocation** — a broken import in `cli/download.py`. It crashed on the *first line of every run*, which means it was never exercised after the regression landed. Root cause is not the import typo; it's that `download` had no test. Fixed the import and added `tests/test_download_cli.py` so the command can't crash-on-load again unnoticed.
- **`scribe providers test groq` never checked `GROQ_API_KEY`** — the `key_map` in `cli/config_cmd.py` had no `groq` entry, so the test fell through to a default and reported a misleading result. Added the entry (`"groq": "GROQ_API_KEY"`).

Both are the same failure mode: a feature (Groq provider in 0.9.0, download command earlier) landed without the small test that would have caught the drift. The rest of this release leans the other way — every new behavior below ships with a runnable check.

Docs had drifted too: the Groq provider (0.9.0) was missing from a few command/config tables in the skill and user docs. Swept in this pass.

## Duplicate detection + `--force`

The recurring annoyance: re-run scribe on a URL you already transcribed and it re-downloads and re-transcribes from scratch — wasted time, wasted API spend.

**Design — the vault is the source of truth, no cache file.** `core/dedup.py::find_existing_transcript(source)` scans `sources/*/*.md` in the workspace and reads only each note's frontmatter, matching the `source:` line exactly. If one matches, that file already *is* the record — there's nothing to keep in sync. We deliberately did **not** add a cache/index-file lookup: a separate cache is a second source of truth that rots the moment someone moves or deletes a note by hand. Reading frontmatter is O(files) but the scan stops at the first `---` per file, so it's cheap for realistic vault sizes.

**Enforced in the orchestrator, not the CLI.** The check lives in `orchestrator.process()` as step 0, before any download. This is the load-bearing decision: because every surface (CLI, Web UI, MCP) routes through `process()`, they *all* inherit dedup for free. A hit returns a `ProcessResult(cached=True)` populated from the existing file's frontmatter and stops the pipeline. `--force` / `force=True` skips the check.

Surface wiring:
- CLI: `--force` / `-f` on `scribe` and `scribe batch`; prints `Already transcribed: <path> — use --force to re-transcribe.`; batch table shows `CACHED`.
- JSON: every transcribe/batch result carries `"cached"`.
- Web UI + MCP: `force` param plumbed through; MCP `transcribe`/`batch_transcribe` also gained `quality`.

## `scribe rm` — delete with index resync

The counterpart to dedup: once you can detect an existing transcript, you need a clean way to remove one (not least to clear the way for a fresh `--force` when the source changed).

`vault/index.py` gained `find_transcript(target)` (accepts a full path or a bare slug; returns all matches) and `delete_transcript(path)` (deletes the file **and** removes its row from the master `_index.md`). The **daily logs are left intact** — they're an append-only historical record of what was processed each day, not a live index, so deleting a transcript shouldn't rewrite history.

Surfaces:
- CLI: `scribe rm <path-or-slug>` with `--yes`/`-y` (skip prompt) and `--json`/`-j`. Ambiguous slug → lists matches and exits without deleting.
- Web UI: `DELETE /api/transcripts/{id}` + a delete button in History.
- MCP: `delete_transcript` tool (brings the MCP total to 10).

## Cooperative Web UI cancel (+ retry)

`POST /api/jobs/{job_id}/cancel` cancels a running job **cooperatively** — it sets a flag the running pipeline checks at its next `on_progress` step and bails there, rather than hard-killing a thread mid-download (which would leave temp files and half-written vault state). It lands at the next checkpoint, not instantly, and that's the right tradeoff. Paired with a "Try again" affordance on errors, an "Already transcribed → Re-transcribe" cached state, and a 4 GB upload cap.

## Testing — first orchestrator integration test

Until now the orchestrator (the thing every surface depends on) had no direct test. `tests/test_orchestrator.py::test_process_dedup_and_force` now exercises the real wiring end to end with a stubbed downloader/provider: first run writes and returns `cached=False`; second run on the same URL returns `cached=True` with no download; `force=True` re-transcribes. Plus `test_dedup.py`, `test_delete.py`, and `test_download_cli.py` for the units.

## Files

- `core/dedup.py` (new), `core/orchestrator.py` (dedup step + `force`)
- `cli/rm.py` (new), `cli/transcribe.py` + `cli/batch.py` (`--force`), `cli/download.py` (import fix), `cli/config_cmd.py` (groq key_map), `cli/main.py` (register `rm`)
- `vault/index.py` (`find_transcript`, `delete_transcript`)
- `mcp/server.py` (`quality`/`force` params, `delete_transcript` tool)
- `web/` (cancel endpoint, delete endpoint, upload cap)
- `tests/test_orchestrator.py`, `test_dedup.py`, `test_delete.py`, `test_download_cli.py`
