# Voice Sweep + Polish Batch Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement task-by-task.

**Goal:** The CLI's spoken voice matches the docs (`anyscribe`-first everywhere a user reads output), plus three deferred quick wins: sarvam spelling alias, port-conflict auto-retry, README screenshot downscale.

**Context:** Follow-up to the 0.16.1 user-facing docs rebuild (journal: `docs/building/journal/2026-08-09-user-facing-docs-rebuild.md`). The docs now teach `anyscribe`; ~85 runtime strings across ~20 files still print `scribe`. Known trap from that effort: several tests assert these strings with substring matches that can never fail ("scribe X" ⊂ "anyscribe X") — every touched assertion must be proven capable of failing.

## Global Constraints

- Current version 0.16.1; no version bumps (release is separate and gated).
- NEVER change: filenames (`scribe.log`), asset names (`scribe-ui.png`), env prefixes (`ASCLI_`), model ids (`scribe_v2`), binary/entry-point names (`scribe`, `ascli`, `anyscribe-mcp` stay registered), `anyscribecli` migration references, ElevenLabs "Scribe" product name, log/pidfile paths.
- Skill files (`src/anyscribe/skill/`) update in the same commit as any behavior change (repo CLAUDE.md).
- A negative verification finding needs proof the tool ran (exit status), not empty output.
- Any assertion tightened or added on a swept string must be watched failing once (revert the string, see red, restore).
- Gates per task: `ruff check src tests scripts && pytest`; UI untouched this plan (no bundle rebuild needed).
- Commits end with `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`.

---

### Task 1: Runtime-string voice sweep + assertion hardening

**Files:** all of `src/anyscribe/**/*.py` where user-visible strings say `scribe` (inventory first: known sites include `core/errors.py`, `core/preflight.py`, `cli/onboard.py` closing block, `providers/openai.py` diarization suggestion, `cli/models_cmd.py`, `cli/transcribe.py`, `cli/local_cmd.py`, `cli/main.py` ui/banner strings, `web/routes/config.py:245` local-model hint). Tests: every file asserting swept strings.

- [ ] **Step 1: Inventory.** `grep -rnE "\bscribe\b" src/anyscribe --include="*.py"` then classify each hit: SWEEP (user-visible command references in printed/raised strings, help text, docstrings surfaced by --help) vs KEEP (exclusion list in Global Constraints, code comments may be swept or left — prefer sweeping for consistency, zero risk). Write the classified inventory into the task report before editing.
- [ ] **Step 2: Find the assertions.** `grep -rnE "\bscribe " tests/` — for each test pinning a swept string, tighten it to a form that fails when the source string regresses (full-line or anchored match, not substring-of-anyscribe). List them in the report.
- [ ] **Step 3: Sweep.** Apply replacements. The skill reference files under `src/anyscribe/skill/references/` already say `anyscribe` — verify no NEW mismatch is created (grep after).
- [ ] **Step 4: Prove the tests bite.** For each tightened/new assertion: revert one covered source string, run the covering test, see FAIL, restore, see PASS. Evidence (commands + tails) in the report.
- [ ] **Step 5: Full gates + live check.** `ruff check src tests scripts && pytest`; run `python3 -m anyscribe --help`, `python3 -m anyscribe config` and one induced error (e.g. `python3 -m anyscribe model info nonexistent`) — confirm output says `anyscribe`.
- [ ] **Step 6: Commit** `fix: runtime strings speak anyscribe, matching the docs; harden their assertions`.

### Task 2: sarvam/sargam alias + port-conflict auto-retry

**Files:** `src/anyscribe/providers/__init__.py`, wherever provider-name input is validated (trace callers of PROVIDER_REGISTRY lookups: cli transcribe/config/onboard, web routes, mcp server — alias at the LOWEST shared entry point, one place, not per-caller); `src/anyscribe/cli/main.py` (~lines 230-247 port check); tests.

- [ ] **Step 1 (alias): failing test** — canonicalization: input `sarvam` resolves to the `sargam` provider everywhere provider names enter (one shared normalize function; test the CLI path and one web path).
- [ ] **Step 2 (alias): implement** — a `normalize_provider_name()` (or equivalent at the existing shared choke point — inspect `core/config_set.py` and `providers/__init__.py` for where validation already lives) mapping `sarvam`→`sargam`; error messages for unknown providers list `sargam` (canonical) only.
- [ ] **Step 3 (retry): failing test** — when the requested port is busy, `ui` finds the next free port (scan up to +10), prints what it did (`Port 8457 busy — using 8458`), and starts there; only errors out if all attempts busy.
- [ ] **Step 4 (retry): implement** in `cli/main.py` ui command (socket-probe loop before `run()`); the "Try: anyscribe ui --port N" fallback message only on exhaustion.
- [ ] **Step 5:** gates; update `docs/user/commands.md` (ui section: auto-retry behavior) and `docs/user/providers.md` (one line: `sarvam` accepted as spelling) + skill references if they state otherwise; re-render docs (`python3 scripts/build-docs.py`), commit rendered HTML with it.
- [ ] **Step 6: Commit** `feat: sarvam spelling alias; ui auto-retries busy ports`.

### Task 3: Screenshot downscale + close-out

**Files:** `landing/assets/scribe-ui.png`, journal + `docs/building/_index.md` row.

- [ ] **Step 1:** `sips -Z 1400 landing/assets/scribe-ui.png` (in place — landing and README share it; 1400px is ample for both). Record before/after bytes. Verify README's raw.githubusercontent URL still resolves to this path (it does — same path).
- [ ] **Step 2:** Journal entry `docs/building/journal/2026-08-09-voice-sweep-and-polish.md` (frontmatter type/tags/tldr): sweep scope + the assertion-hardening evidence, alias, port retry, image; `_index.md` row (careful: file carries ANOTHER SESSION's uncommitted rows — stage surgically, never `git add -A`; see the 2026-08-09 rebuild journal's technique).
- [ ] **Step 3:** Final gate chain + commit `docs: journal for voice sweep + polish batch`.
