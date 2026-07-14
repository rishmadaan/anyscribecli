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

Two independent Codex passes (different model family, blind to this session's
reasoning) drove the deletion path to robustness.

**Pass 1 — two behavioural gaps:**

1. **`export`-prefixed keys survived deletion.** `.env` accepts valid dotenv
   `export KEY=...` syntax; our line parse read the key as `"export KEY"`, so
   `delete_env` kept the line and the next `load_env()` restored it — a silent
   no-op.
2. **"Remove key" was misleading for inherited keys.** `has_key` is true for a
   key exported in the parent shell (not saved by us); the button implied a
   permanent removal we can't deliver. Fix: new `env_file_keys()` backs a
   `key_in_env_file` flag on `GET /api/providers`; the UI gates the Remove
   button on it, so we only offer removal for keys actually persisted in
   `.env`. Inherited keys still show green/Test (they work) — just no Remove.

**Pass 2 — the root cause behind #1.** The first fix hand-rolled an
`export`-stripping parser, which Codex correctly flagged as still short of the
full dotenv grammar `load_env()` accepts: `export` + a *tab* (not just a
space), quoted keys, and multiline quoted values — the last of which our
line-based rewrite would corrupt while dropping comments. Rather than keep
chasing the grammar, the parser was **deleted** and `save_env` / `delete_env` /
`env_file_keys` now delegate to python-dotenv's own `set_key` / `unset_key` /
`dotenv_values` (a dependency we already use for reading). These write
atomically (temp file + `os.replace`) and preserve every *other* binding's
original text — comments, multiline values, unrelated keys — verbatim.
`set_key(..., quote_mode="never")` keeps our plain `KEY=value` format for the
single-line tokens we store. Read, write, delete, and load now share one
parser, so they can't disagree. Regression tests cover export-tab deletion,
comment/multiline preservation, and the `key_in_env_file` signal.

All verified end-to-end against the live app in an isolated `.env` (including a
file with a comment, a multiline value, an `export\t`-prefixed key, and an
inherited-only key). Full suite 291 passed, 1 skipped; ruff + eslint clean.
