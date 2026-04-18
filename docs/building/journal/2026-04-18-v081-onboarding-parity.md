---
type: feature
date: 2026-04-18
version: 0.8.1
tags: [onboarding, web-ui, cli, agent, wizard, architecture]
tldr: >
  Closes the gaps from v0.8.0's local-transcription release. Three fully
  sufficient onboarding flows — Web UI wizard (modal on first run), TUI
  wizard (unchanged), headless CLI with ``scribe onboard --yes``. One
  shared backend (``core/onboard_headless.py``) all three converge on.
  Plus ``scribe model reinstall``, download queue, live pip-install log
  in the Web UI, focus-trapped modals, always-visible Diagnose button,
  and a new architecture-doc section making the shared-backend +
  asymmetric-surface model explicit.
---

# v0.8.1 — Three-surface onboarding parity + polish

## Why this release

v0.8.0 shipped local-transcription as a first-class opt-in, but only along two of the three surfaces we promised: CLI TUI + Web UI button. The Web UI still didn't have a coherent *first-run* flow that matched `scribe onboard`, and agents still had no headless path — both of which we explicitly planned for and trimmed silently during the v0.8.0 build. This release closes those gaps and makes the rule explicit:

> **Three surfaces, three fully-sufficient flows.** A human using the Web UI must be able to reach "ready to transcribe" without ever touching the CLI. A TUI user must reach the same state via `scribe onboard`. An agent must reach the same state via `scribe onboard --provider X --yes --json`. None of the three depends on the others existing.

## Architectural frame: shared backend, surface asymmetry

Before writing any code, we wrote down the mental model that governs how surfaces relate (see `docs/building/architecture.md` → "CLI ↔ Web UI: shared backend, asymmetric surfaces"):

- **Neither surface shells out to the other.** The CLI is Typer commands in `cli/*.py`; the Web UI is FastAPI routes in `web/routes/*.py`. Both call the same Python modules in `core/`, `providers/`, `config/`, `vault/`, `downloaders/`. Bug fixes in shared modules fix both surfaces; new providers land on both surfaces simultaneously.
- **Three-surface parity applies only where UX differs meaningfully.** Onboarding is the canonical case — a modal wizard, a TUI prompt sequence, and a flag parser are genuinely different surface experiences. For one-shot actions (`transcribe`, `config set`), both surfaces just call the shared backend; no multi-surface UX layer needed.
- **Feature coverage is intentionally asymmetric.** `scribe batch` is CLI-only (pipeline-friendly); the transcript browser is Web-UI-only (visual). The architecture doc now has a matrix that captures this and the principle for deciding surface placement.

The new `COMMIT_CHECKLIST.md` entry "After adding or changing a surface-facing feature" makes this discipline enforceable going forward.

## What shipped

### `core/onboard_headless.py` — shared onboarding backend

Single function `run_headless_onboard()` that all three flow controllers converge on. Validates inputs, writes config, writes env keys, creates vault, optionally installs the Claude Code skill, optionally runs local setup. Structured `OnboardValidationError` with a machine-readable `payload` so callers can turn missing-flag errors into whatever error shape their surface needs.

### `scribe onboard --yes ...` — headless agent path

Flag-driven mode for agents/CI/scripts. Required: `--yes --provider X`. For API providers, either `--api-key` or the corresponding env var. For `--provider local`, `--local-model` is additionally required. All other fields have sane defaults. `--json` emits a single structured object on stdout. Exit 2 for usage errors, 1 for setup failures (with pip/pipx command + captured stderr in the error payload), 0 for success.

The interactive TUI path is **unchanged** — no regression risk for existing users. Adding `--yes` turns on headless mode; omitting it keeps the v0.8.0 behaviour.

**Agent rule** in the skill: when asked to set up scribe, use the headless form — never suggest the interactive `scribe onboard`. Prefer env-var form for API keys (avoids leaking into shell history).

### Web UI wizard — first-run + re-runnable

New `OnboardingWizard.tsx` + 6 step components, full-screen modal over the app. Step semantics:

1. **Welcome** — "Let's set you up."
2. **Provider** — card grid of 5 API providers + a "local (offline)" card. Picking local branches the wizard to offline setup directly.
3. **API key** — masked input, inline Test button.
4. **Offline opt-in** — for API-provider branches: "Also enable offline transcription?" (default no). Required step for the local-provider branch. Size picker with recommended-size badge, triggers `POST /api/local/setup`, polls status, streams install log.
5. **Workspace** — prefilled default, editable.
6. **Done** — summary + single Finish button that fans out to `POST /api/onboarding/save`.

Trigger logic in `App.tsx`: on mount, call `GET /api/onboarding/status` → if `completed === false` AND localStorage flag `scribe_onboarding_dismissed` isn't set, render the wizard. "Skip for now" sets the flag; "Finish" also sets it. Settings has a **"Run setup wizard"** button that clears the flag and reopens it.

### `GET /api/onboarding/status` + `POST /api/onboarding/save`

New `web/routes/onboarding.py`. Status is a cheap threshold check: `completed = has_workspace AND (has_any_api_key OR local_ready)`. Save is a single round-trip that calls `run_headless_onboard()` — same backend as the CLI `--yes` path.

### Polish items — cleared the Category D debt

| # | Gap from prior accounting | This release |
|---|---------------------------|--------------|
| 11 | Concurrent download queue | FIFO queue in `web/routes/models.py` replaces the 409-on-second-click. `GET /api/models/local` exposes `downloading`, `queued`, `queue_position` per model; UI shows position pills. |
| 12 | Stderr display inconsistency | Both LocalSetupModal and Settings error banners render first 500 chars inline + `<details>` expander. |
| 13 | No live pip output in Web UI | Ring-buffer log on `app.state.local_setup.log`; new `GET /api/local/setup/log?since=N`. LocalSetupModal + OnboardingWizard's offline step both have a collapsible "Show install log" section streaming lines every 1.5s. |
| 14 | Test button hidden pre-setup | Always visible on the local card. Label is "Test" (set up) vs "Diagnose" (not set up). Both render the structured `checks` response — so pre-setup users can see exactly what's missing. |
| 15 | No focus trap on modals | New shared `Modal.tsx` with ARIA dialog role, `aria-labelledby`, tab cycling, focus restore on unmount. Both `LocalSetupModal` and `OnboardingWizard` use it. |
| 16 | No inline "download to enable" in default-model dropdown | (Kept the dropdown simple — disabled uncached options. Adding inline download buttons would duplicate the Models-table UX. Leaving as-is unless users report friction.) |

Plus: **`scribe model reinstall <size>`** and its Web UI counterpart (the 🔄 button on each cached row in the Models table, plus `POST /api/models/local/{size}/reinstall`). Delete + re-download in one step, useful when cached weights look corrupted. Returns `{status: "reinstalled", bytes_freed, bytes_downloaded}` or `{status: "downloaded_only"}` when the model wasn't cached to begin with.

## Files of note

- `src/anyscribecli/core/onboard_headless.py` — the shared backend function.
- `src/anyscribecli/web/routes/onboarding.py` — status + save router.
- `src/anyscribecli/cli/onboard.py` — `--yes` gate at the top of `onboard()`; delegates to `_run_headless()` which calls the shared backend.
- `src/anyscribecli/cli/models_cmd.py::model_reinstall` — new subcommand.
- `src/anyscribecli/web/routes/models.py` — FIFO queue state + `/reinstall` endpoint.
- `src/anyscribecli/web/routes/local.py` — ring-buffer log + `/setup/log` endpoint.
- `ui/src/components/OnboardingWizard.tsx` — 500-ish lines, all six steps inline.
- `ui/src/components/Modal.tsx` — shared a11y-clean modal primitive.
- `ui/src/App.tsx` — first-run detection + localStorage gate.
- `docs/building/architecture.md` — new "CLI ↔ Web UI" section with feature-coverage matrix.
- `docs/building/COMMIT_CHECKLIST.md` — new "surface-facing feature" checklist entry.

## Intentionally NOT done

- **TUI removal sweep.** Backlogged and explicitly deprioritised. `scribe onboard` keeps its full interactive TUI as a first-class path alongside `--yes`.
- **Inline "download to enable" in the Settings default-model dropdown.** Deferred — the Models-table already provides per-row download, and duplicating the CTA inside the dropdown didn't feel worth the code.
- **WebSocket streaming of pip output.** Polling the log ring buffer every 1.5s was simpler and matches the rest of the Web UI's patterns. Real-time byte-level tqdm output is the right v2 goal but wasn't worth the machinery for a diagnostic affordance.

## Version mechanics

- v0.8.0 was committed locally (marker release) but never pushed to PyPI. v0.8.1 supersedes it on PyPI. Git history preserves both commits so the architectural shift is dated correctly.
- BACKLOG.md merges 0.8.0 and 0.8.1 into a single "Current" row.

## Known risks (flagged but accepted)

- **Setup-log buffering.** pip subprocess output is sometimes line-buffered, sometimes block-buffered depending on the pip flavor. If block-buffered, users see all output at the end rather than streaming. Acceptable — the log is a diagnostic tool, not primary UX.
- **`app.state` queue state lost on server restart.** Restarting `scribe ui` mid-download abandons the queue; HuggingFace cache resumes partials on re-pull, so no data loss but the user has to click Download again.
- **LocalStorage flag behaviour.** Clearing browser data re-opens the wizard. Settings → Run setup wizard button remains as the manual re-entry path either way.
