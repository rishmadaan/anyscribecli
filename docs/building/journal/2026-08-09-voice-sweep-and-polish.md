---
type: feature
tags: [voice, docs, providers, web-ui, cli, landing]
tldr: "Follow-up to the user-facing docs rebuild: swept ~104 user-visible `scribe` strings to `anyscribe` across ~24 files with red/green proof the tightened assertions can actually fail, added a `sarvam`→`sargam` provider-name alias at a single normalize function (three review-found false-green surfaces fixed by binding the canonical name once at assignment, not per-lookup — alias-aware sibling maps parked as real debt), gave `anyscribe ui` auto-retry on a busy port (clamped at 65535, its first ceiling test was vacuous and had to be rebuilt to actually exercise the bug), fixed a grammar survivor across four surfaces, and downscaled the landing/README screenshot 2880x1800 to 1400x875. Also records an incident: a live check overwrote the real ~/.anyscribe/config.yaml; provider/quality were reconstructed from transcript evidence, not recovered, and still need Rishabh's confirmation."
---

# Voice sweep + polish batch (branch `voice-and-polish`)

**Date:** 2026-08-09 · Plan: `docs/superpowers/plans/2026-08-09-voice-sweep-and-polish.md` ·
Commits: `a93d917..a22436c` (Tasks 1–2), this entry closes Task 3.

## Why

The 0.16.1 docs rebuild taught `anyscribe` everywhere a user reads
documentation, but the CLI's own runtime output — error hints, `--help` text,
banners, onboarding prose — was still ~85-104 sites behind, still saying
`scribe`. A known trap from that earlier effort made this risky to just
"fix": several tests pin these strings with substring matches that can never
fail (`"scribe X"` is a substring of `"anyscribe X"`, so the assertion passes
identically before and after a regression). Any touched assertion had to be
proven capable of failing, not just left green.

## Task 1 — runtime-string sweep + assertion hardening

Baseline `grep -rnE "\bscribe\b" src/anyscribe --include="*.py"` found 125
hits, classified before any edit: 22 KEEP (binary/entry-point names,
`scribe.log`, `scribe_v2` model id, MCP protocol identifiers like
`FastMCP("scribe")` and the `scribe://` resource scheme, on-disk legacy skill
dir names, migration source-key references — all on the plan's exclusion
list), 103 SWEEP (user-visible printed/raised strings, `--help` docstrings,
module docstrings) across 24 files.

Two assertions pinning swept strings were substring-vacuous and rewritten to
anchor on the full line or the `anyscribe`-prefixed phrase:
`tests/test_errors.py:24` and `tests/test_config_set.py:152`. A third,
already hardened by the prior effort (`tests/test_config_dashboard.py:44`),
was proved rather than assumed. All three were watched red under a targeted
source revert (not `git checkout` — an early file-level checkout wiped an
uncommitted sweep and had to be redone) and green again after restore.

Gates: `ruff check` clean, `pytest` 459 passed/1 skipped. Live checks
(`--help`, `config`, an induced `model info nonexistent` error) confirmed
`anyscribe`-voiced output; the only remaining bare `scribe` in live output is
`scribe_v2`, the ElevenLabs model id (correctly on the KEEP list).

One grammar break the mechanical sweep introduced (`mcp/server.py:396`,
"Change a anyscribe configuration setting") was hand-fixed inline. A second
one — `"A anyscribe tray is already running."` in `cli/tray_cmd.py:114` —
was deliberately left for Task 2, because the identical wrong article also
existed in three doc surfaces (`skill/references/troubleshooting.md`,
`docs/user/troubleshooting.md`, the rendered
`landing/docs/troubleshooting.html`, whose heading anchor would shift too);
fixing the Python alone would have created a new mismatch this task was
forbidden to create.

## Task 2 — sarvam/sargam alias + `ui` port auto-retry

**Alias.** Traced every site where a provider name enters the system
(`get_provider()`, `resolve_run()`, `config_set.py`'s enum/model setters,
`web/routes/config.py`'s test-provider route) and found no single lower
choke point — five peers, not a chain. Added one shared function instead of
five ad-hoc checks:

```python
PROVIDER_ALIASES: dict[str, str] = {"sarvam": "sargam"}

def normalize_provider_name(name: str) -> str:
    return PROVIDER_ALIASES.get(name, name)
```

`PROVIDER_REGISTRY` and every error message stay canonical-only — `sarvam`
is an accepted input spelling, never a name echoed back or offered as a
choice.

**Round-1 review caught the alias leaking on three surfaces the "one shared
function" framing missed** — the real failure mode wasn't missing
validation, it was call sites pairing `get_provider(x)` (which normalizes
internally) with a raw-`x` lookup into a *sibling* map:

1. **False-green key check (CLI + MCP `providers test`).** Both did
   `provider_name = name or settings.provider` → `get_provider()` (normalizes,
   succeeds) → `PROVIDER_KEY_ENV.get(provider_name)` (raw `sarvam`, returns
   `None`, meaning "needs no key") — so the entire API-key check silently
   skipped and CLI exited 0 / MCP reported `api_key_set: true` for a provider
   with **no key configured at all**. A credential check reporting success on
   a missing credential.
2. **Onboarding rejected the alias outright** — `_validate` compared against
   `ALL_PROVIDERS` unnormalized, so `onboard --yes --provider sarvam` errored
   `unknown provider 'sarvam'` while `docs/user/providers.md` promised it
   worked everywhere.
3. A grammar survivor (`a \`anyscribe ui\` server` in two more doc files) and
   stale busy-port advice (`--port 9000` coached as *the* fix, now wrong
   given auto-retry) — minor, fixed alongside.

Fix: **bind the canonical name once, at the point the string is first
assigned**, so everything downstream in that function body is already
canonical — not "normalize at each lookup". Each of the three fixes was
watched red under a targeted revert (dropping `normalize_provider_name` from
`cli/config_cmd.py`, `mcp/server.py`, `core/onboard_headless.py` reds one
test each), then green.

**Parked as real debt, not fixed here:** the alias is still enforced
per-call-site, now across eight sites. This round proved that shape leaks —
nothing structural stops a ninth caller from indexing
`PROVIDER_KEY_ENV[raw_name]` directly and reintroducing the same false-green
bug. The durable fix is alias-aware sibling maps (one `dict` subclass shared
by `PROVIDER_KEY_ENV`/`PROVIDER_MODELS`/`PROVIDER_REGISTRY`), deliberately
deferred as its own red/green round rather than folded in here.

**Port auto-retry.** `cli/main.py` gained `PORT_SCAN_SPAN = 10`; the `ui`
command probes `range(port, min(port + PORT_SCAN_SPAN, 65535) + 1)` and
starts on the first port that isn't already listening, printing `Port 8457
busy — using 8458.`; the `--port <free port>` hint now only fires on full
exhaustion. **Vacuous-test catch:** the first version of the ceiling test
asserted behavior at port 65536 but passed even with the bug present, because
65535 was free in the test environment and the scan broke on the first probe
without ever reaching the overflow. Rebuilt to stub `socket.socket` with an
all-busy fake that raises `OverflowError` outside 0–65535 and assert the
probed range is exactly `range(65530, 65536)` — this version reds on the
real unclamped code and catches the `connect_ex(65536)` `OverflowError` the
original test never could.

Docs updated on both sides: `docs/user/commands.md` (`ui` auto-retry
behavior, busy-port advice rewritten to lead with retry), `docs/user/providers.md`
(`sarvam` accepted as an input spelling, stored as `sargam`), matching skill
references, re-rendered via `scripts/build-docs.py` and committed.

Gates: `ruff` clean, `pytest` 473 passed/1 skipped (round 1) → 477 passed/1
skipped (round 2), `build-docs.py` + `check-docs.py` both exit 0 and were
proven to actually bite (injected bad anchor → `build-docs.py` fails;
injected `v9.9.9` → `check-docs.py` fails).

## Incident — real config.yaml overwritten during a live check

The first live verification of the alias ran `anyscribe config set provider
sarvam` against the implementer's **real** `~/.anyscribe/config.yaml`
(not an isolated `HOME`), which overwrote the `provider` and `quality`
fields. No backup existed — the file is untracked, no TM snapshot covers it.

Recovery: reconstructed from the only hard evidence available — the last 8
vault transcripts (2026-07-29, all recording `provider: elevenlabs`) point at
`provider: elevenlabs`; `accuracy` is the quality tier that resolves there,
so it was set to reproduce the observed real-world routing. **The `quality`
value is a reconstruction, not a recovery — it needs Rishabh's confirmation**
via a glance at `anyscribe config`. One counter-signal on record: the
restored config's untouched `language: hi-Latn` field is a Deepgram-only
route per `docs/user/providers.md`, which is the one piece of evidence that
argues the real pinned provider might have been `deepgram` instead. Nothing
else in the file (`diarize`, `output_format`, `local_model`, workspace,
instagram settings) was touched or is in question.

**Lesson, enforced starting round 2:** every subsequent live check in this
plan ran under an isolated `HOME`, so nothing after the incident touched the
real config again.

## Task 3 — screenshot downscale + close-out

`sips -Z 1400 landing/assets/scribe-ui.png`: 2,005,516 bytes / 2880×1800 →
1,079,578 bytes / 1400×875 (46% smaller, aspect ratio preserved — `-Z`
constrains the long edge). Same file, same path — `landing/index.html` and
the README's `raw.githubusercontent.com` URL both reference it unchanged, no
reference edits needed. Checked whether the size drop could break layout:
`landing/index.html:1563` hardcodes `width="2880" height="1800"` on the
`<img>`, but `.browser-shot { width: 100%; height: auto; }` means those
attributes only reserve the aspect ratio for layout, never the actual
rendered size — and 2880:1800 and 1400:875 are the same 16:10 ratio, so no
HTML change was required or made.

## Process note

This is the third journal in a row on this branch lineage to record a
staging-hygiene requirement: `docs/building/_index.md` on this working tree
carries another session's two uncommitted 2026-07-31 rows, and two matching
journal files sit untracked alongside them. Every commit in this plan
(including this one) staged `_index.md` surgically — rebuilding the blob
from `git show HEAD:docs/building/_index.md` plus only this task's new row,
via `git hash-object -w` + `git update-index --cacheinfo` — rather than
`git add`, so the foreign rows and journals stay out of every commit and
remain visible in `git status` afterward.

## Gate at close-out

`ruff check src tests scripts` clean · `pytest` 477 passed, 1 skipped ·
`build-docs.py` rendered 6 pages + index · `git diff --exit-code landing/docs`
clean · `check-docs.py` clean. The PNG downscale is not part of the docs
render, so no HTML changed in this task.
