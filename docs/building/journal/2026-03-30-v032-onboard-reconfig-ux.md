---
type: project-note
tags: [onboarding, ux, instagram, credentials, reconfigure]
tldr: "Two fixes: onboard --force now shows current settings and asks before overwriting each step. Instagram error message corrected to point to .env instead of config set."
---

# v0.3.2 — Onboard Reconfigure UX + Instagram Error Fix

## What changed

### 1. `ascli onboard --force` now shows existing config

Previously, re-running onboard with `--force` walked through every step from scratch, even if only one setting needed changing. Now it:

- Shows a "Reconfiguring" banner explaining the flow
- At each step, displays the current value (e.g., `Provider: openai`, `Language: auto`)
- API keys shown masked: `****abcd` (last 4 chars only)
- Instagram credentials shown: username + masked password
- Each step asks "Change X?" — skip to next if no
- Arrow-key selectors pre-select the current value when changing

This makes reconfiguration much faster — change one thing without re-entering everything.

### 2. Instagram error message fix

The error when Instagram credentials aren't configured used to say:

```
Run: ascli config set instagram.password YOUR_PASSWORD
```

This was wrong — `config set` writes to `config.yaml`, but the password should be in `.env`. Fixed to:

```
Add INSTAGRAM_PASSWORD=YOUR_PASSWORD to ~/.anyscribecli/.env
```

## Files changed

- `src/anyscribecli/cli/onboard.py` — reconfigure flow with `_mask_key()` helper, per-step skip/change logic
- `src/anyscribecli/downloaders/instagram.py` — corrected error message
