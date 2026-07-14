---
type: feature
tags: [web-ui, settings, api-keys, providers, env]
tldr: "Web UI Settings → Providers can now REMOVE a saved API key, not just add/replace it. New backend delete_env() rewrites .env without the named vars; new DELETE /api/keys/{provider} strips it from .env and os.environ. Frontend adds a two-step 'Remove key' → 'Remove?' confirm inside the expanded provider panel (shown only when a key exists), matching the existing Replace/teardown confirm pattern. No CLI change."
---

# Delete a saved provider API key from the Web UI

**Date:** 2026-07-14
**Branch:** feat/delete-provider-key

## What & why

The provider panel in Settings could add or replace an API key but never
remove one — `save_env()` only ever wrote/updated. So a key, once saved, was
permanent (short of hand-editing `~/.anyscribecli/.env`). This adds a real
delete path across the stack.

## Changes

- **`config/settings.py`** — new `delete_env(names)`, the counterpart to
  `save_env()`. Same line-parsing, rewrites `.env` without the named keys.
  No-op if the file is absent.
- **`web/routes/config.py`** — new `DELETE /api/keys/{provider_name}`. Looks
  up the env var via `PROVIDER_KEY_MAP`, calls `delete_env([var])`, and
  `os.environ.pop(var, None)` so the running process forgets it too. Unknown
  provider → `{success: false}` (mirrors the PUT handler).
- **`ui` (SettingsPage + client)** — `deleteKey()` in the API client; a
  two-step "Remove key" → "Remove?" button in the expanded provider panel,
  rendered only when `has_key`. On success it collapses the panel and
  refreshes `/api/providers` (dot flips to grey). Chose the inline two-step
  confirm to match the existing "Replace?" and local-teardown patterns in the
  same view — no new modal.

## Tests / verification

- `test_settings.py`: `delete_env` removes only the named key and is a no-op
  on a missing file.
- End-to-end (isolated tmp `.env`): `DELETE /api/keys/openai` → 200
  `{success: true}`, `.env` retains other keys, `os.environ` drops the var,
  unknown provider fails gracefully. Full suite green; UI `tsc -b && vite
  build` clean; "Remove key" present in the bundle.

## Codex review follow-ups (gpt-5.6-sol, high)

An independent read by Codex (different model family, blind to this session's
reasoning) surfaced two real edge cases, both fixed here:

1. **`export`-prefixed keys survived deletion.** `.env` accepts valid dotenv
   `export KEY=...` syntax; the old split-on-`=` parse read the key name as
   `"export KEY"`, so `delete_env` kept the line and python-dotenv's next
   `load_env()` restored it — the removal silently no-oped. Root-cause fix:
   both `save_env` and `delete_env` now parse through a shared
   `_read_env_pairs()` that strips an optional `export ` prefix, so rewrites
   normalize such lines to plain `KEY=value`. Our own writer never emits the
   `export` form, so this only bit hand-edited files — but it's now robust.
   Regression test: `test_delete_env_handles_export_prefixed_keys`.

2. **"Remove key" was misleading for inherited keys.** `has_key` is true for a
   key exported in the parent shell (not saved by us); the button implied a
   permanent removal we can't deliver (delete only pops the child process +
   rewrites `.env`, so a restart re-inherits it). Fix: new `env_file_keys()`
   backs a `key_in_env_file` flag on `GET /api/providers`; the UI gates the
   Remove button on it, so we only offer removal for keys actually persisted in
   `.env`. Inherited keys still show green/Test (they work) — just no Remove.

Both verified end-to-end against the live app in an isolated `.env`. Full suite
289 passed, 1 skipped; ruff + eslint clean.
