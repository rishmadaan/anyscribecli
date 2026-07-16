---
type: refactor
tags: [providers, config, dead-code, ponytail]
tldr: Ponytail audit batch — canonical PROVIDER_KEY_ENV map (fixes groq drift in preflight+MCP), shared _transcribe_chunked on the provider base class (fixes original-file deletion for >25MB short files), dead-code sweep, websockets dep dropped.
---

# Ponytail simplification batch (v0.13.4)

A repo-wide over-engineering audit (2026-07-16) found the provider→env-var
map hand-copied in 7 places — two copies had already drifted (groq missing
from `core/preflight.py` and the MCP `test_provider` key check, so groq key
problems were silently unreported). It also found the chunk-transcribe loop
(checkpoint resume, overlap dedup, timestamp offsets) copy-pasted across
openai/deepgram/elevenlabs/sargam.

## What changed

1. **Canonical map** — `providers/__init__.py::PROVIDER_KEY_ENV` is now the
   single source of truth; web `PROVIDER_KEY_MAP`, cli `_API_KEY_MAP`,
   onboarding `API_PROVIDERS`/`ALL_PROVIDERS`, quality, preflight, and MCP
   all derive from it. A registry-sync test pins it
   (`test_key_env_map_covers_registry_exactly`).
2. **Shared chunk loop** — `TranscriptionProvider._transcribe_chunked()`
   holds the loop once; providers pass a `transcribe_chunk` closure returning
   chunk-local results. Checkpoint format unchanged — pre-0.13.4 checkpoints
   replay (regression test: `test_chunked_resume_skips_completed_chunks`).
   Sargam's `_parse_response` lost its `offset`/`start_id` params — the loop
   owns offsetting now. Two bugs died in the move: (a) **data loss** — a
   >25MB but ≤18min file entered the old loop with the *original* file as
   its only chunk (`chunk_audio` returns `[(audio_path, 0.0)]` for ≤18min)
   and the unconditional unlink deleted the user's source audio; the shared
   loop never unlinks `audio_path` (regression test:
   `test_large_short_file_is_not_deleted`); (b) sargam's old parse
   double-offset the `end` fallback when the API omitted it
   (`turn.get("end", start) + offset` where `start` already carried the
   offset).
3. **Dead-code sweep** — deleted zero-caller `get_languages`,
   `_queue_position`, `valid_model_sizes`, `local.py` back-compat aliases,
   `GET /api/version`, and the no-op `model pull --yes`. Fixed `config set`
   help still advertising `instagram.username` (removed in 0.8.3). Dropped
   the `websockets` dependency (`uvicorn[standard]` bundles it). The sweep
   also repointed `tests/test_local_setup.py` at the canonical
   `providers.local_models.MODEL_SIZES` instead of a module re-export.

## Deliberately NOT done (audit findings judged not worth the churn)

Deleting `model reinstall` (shipped UX), collapsing the four ScribeAPIError
subclasses (readable type names), and ~10 micro-shrinks of <15 lines each.
Rationale: only duplication that drifts and dead code carry real cost.

## Environment note

During implementation, the local `anyscribecli` install was found to be a
stale non-editable copy in site-packages, silently shadowing `src/` during
test runs. Fixed with `pip install -e . --no-deps`. If tests ever pass
despite obviously broken source edits, check `pip show anyscribecli` first.
