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
  unknown provider fails gracefully. Full suite green (25 in the two touched
  files); UI `tsc -b && vite build` clean; "Remove key" present in the bundle.
