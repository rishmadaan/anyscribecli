---
type: feature
tags: [web-ui, config, settings, parity]
tldr: "v0.15.1. Full config parity in the Web UI: 'Next run' banner (_resolved on GET/PUT /api/config), provider+model controls un-hidden from behind the 'custom' gate, Downloads & media section (prompt_download, local_file_media, keep_media, instagram.browser select — new instagram field on ConfigUpdateRequest), unknown-quality warning note."
---

# Full Web-UI configuration parity (v0.15.1)

**Date:** 2026-07-29 · Rish, minutes after 0.15.0 shipped: the Settings page
had "no logical way" to configure things — "don't dumb it down; allow me to
configure everything on the dashboard."

## Root cause

The 0.15.0 Settings page rendered the Provider + Model controls only inside
`{config.quality === "custom" && ...}`. With a tier selected (his config:
`balanced`) the whole Configure Defaults section collapsed to five radio
choices — the full controls existed but were invisible behind an unlabeled
gate. Also genuinely missing from the web surface: `prompt_download`,
`local_file_media`, `instagram.browser`, and the "Next run" resolution the CLI
dashboard leads with.

## The fix (PR #10)

- `GET/PUT /api/config` gained `_resolved` ({provider, model, via, notes} or
  {error} — never a 500) so the Settings page opens with the same "Next run"
  banner as `scribe config`, live-updating on every save.
- Provider + Model rows always render; an active tier captions them instead of
  hiding them.
- New "Downloads & media" section covers prompt_download / local_file_media
  (plain-language captions), keep_media, and a real Instagram-cookies browser
  select — backed by a new `instagram` field on ConfigUpdateRequest fanned out
  to dotted `set_value` keys (rollback verified for invalid nested keys).
- `resolve_run` warns on an unknown quality value instead of silently ignoring
  it (the banner made that silence misleading).

**Design rule made explicit in docs + skill: nothing is terminal-only.** Every
config key is editable in the Web UI; "where do I change X in the UI" is
always answered by Settings.

## Verification

418 tests (5 new: resolved shape, resolved error path, instagram set/clear,
instagram rollback, unknown-quality note); eslint + vite green; adversarial
PR verification passed all 6 checks (atomicity of mixed instagram+invalid
payloads reproduced, committed bundle hash matches a fresh build).
