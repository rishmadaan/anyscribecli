---
type: feature
tags: [config, defaults, quality, resolve, config-set, web-ui, mcp, onboarding]
tldr: "v0.15.0. Config-defaults redesign: quality gains 'custom' sentinel (picking a provider anywhere sticks), one shared setter (core/config_set.py) + one shared resolver (core/resolve.py) behind every surface, bare `scribe config` defaults dashboard, visible run line + notes, extra_models.openrouter user extensions, OpenAI default → gpt-transcribe with auto whisper-1 timestamp routing."
---

# Configuration-defaults redesign (v0.15.0)

**Date:** 2026-07-29 · after the 0.14.x model picker shipped, Rish flagged that
the defaults experience wasn't designed — knobs existed but no coherent way to
see or set them. Built via ultracode: a 7-agent understand/design/judge
workflow produced the design; Rish made 4 product calls; a 7-agent
implementation workflow built it in reviewable chunks.

## The design (one sentence)

One knob picks the provider — a quality word or `custom`, and picking a
provider anywhere flips quality to `custom` so the choice always sticks; every
provider has a visible model list with a pinnable default; `scribe config`
(bare), the Web UI Settings page, and `scribe config --json` all lead with the
same computed sentence: "Next run: deepgram · nova-3 (quality: balanced)".

## Rish's product decisions (2026-07-29)

1. **extra_models is openrouter-only** — closed providers stay curated by
   scribe releases (Deepgram's list grows via our catalog, not user strings).
2. **Keyless quality tier: warn loudly, fall back** (never block a run).
3. **Ships as 0.15.0.**
4. **OpenAI default is `gpt-transcribe`**, with automatic whisper-1 routing
   when `output_format` needs timestamps and no explicit `-m` was given.

## Load-bearing pieces

- `core/config_set.py::set_value` — the single validated write path; CLI
  `config set`, web `PUT /api/config`, MCP `set_config` are thin wrappers.
  Enforces the provider→custom invariant, validates every enum, expands
  `workspace_path`, routes `<p>_api_key` to `.env`, parses
  `extra_models.openrouter` comma lists (empty value clears).
- `core/resolve.py::resolve_run -> RunPlan{provider, model, via, notes}` —
  replaces four divergent inline copies (CLI/batch/web/MCP). Emits notes for
  every previously-silent swap: diarize→deepgram, keyless-tier fallback,
  gpt-transcribe→whisper-1 timestamps, hi-Latn→nova, diarize model. Every run
  prints `→ provider · model (via)` + notes; `--json` gains `model`.
- Catalog: deepgram `[nova-3, nova-2]`, sargam `[saaras:v3]` only (v2.5
  legacy endpoint code deleted; pin migration in `core/migrate.py`),
  `OPENROUTER_MODEL` env removed (pins supersede it).
- `test_quality.py` retired into `test_resolve.py`; suite 308 → 406.

## Process notes

- Chunks 6/7/8 ran in parallel and each read a mid-race snapshot, so their
  "still missing" flags were mutually stale — everything landed; verify the
  tree, not the reports.
- **An implementation agent ran live `scribe config set` against the real
  `~/.anyscribecli/config.yaml` during testing** (wrote `quality: custom` +
  `provider: openai` into Rish's config). Restored to `quality: balanced`.
  Rule for future implementation agents: live CLI tests use an isolated
  `HOME`. Recorded in agent memory.
- Pre-existing bug found during acceptance: `scribe rm <absolute-path>` crashed
  with `NotImplementedError` after deletion (absolute pattern fed to `rglob`
  in `vault/index.py::find_transcript`). Fixed on this branch (guard + tests).
