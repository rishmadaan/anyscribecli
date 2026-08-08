---
type: feature
tags: [docs, landing, install, web-ui, ci, agents]
tldr: "User-facing docs rebuilt as three doors (agent / dashboard / CLI) with docs/user/*.md as the single source of truth, rendered to landing/docs at commit time by scripts/build-docs.py and gated in CI by scripts/check-docs.py (version drift + MCP-table drift + stale HTML). Ships the product fixes the docs needed to stop lying: install.sh should survive a fresh Apple Silicon Mac (dry-run verified; clean-VM leg outstanding), install.ps1 gets the [tray] extra, keys/status counts local (kills the permanent setup banner), Groq card in the wizard, honest post-Shutdown copy, and a macOS open-at-login toggle guarded on the tray extra."
---

# User-facing documentation rebuild (branch `user-facing-docs`)

**Date:** 2026-08-09 · Spec: `docs/superpowers/specs/2026-07-31-user-facing-docs-design.md` ·
Plan: `docs/superpowers/plans/2026-07-31-user-facing-docs-rebuild.md` ·
Commits: `7f9228d..d25720f` (20 commits, 38 files, +5900/-569)

## Why

The docs were dev-tool docs for a product whose real audience is AI-tool power
users — people who live in Claude/ChatGPT, will happily run a one-line install
and paste an API key, and arrive expecting the *agent* integration to be the
headline. They were also, in places, wrong: the docs promised things the
product didn't do, and the product had rough edges that made the docs read as
lies (a "Setup needed" banner that never went away for local-only users, an
installer that died on a fresh Apple Silicon Mac).

## What shipped

**Three doors.** `docs/user/` is now organised by journey, not by topic:

- **Door 1 — `agents.md`** (new): the headline path. Skill vs MCP explained as
  a capability split rather than two ways to do the same thing, with an honest
  capability map of what each surface can actually do.
- **Door 2 — `getting-started.md`** (restructured): installer first, manual
  install demoted to an appendix, and a new "keep it running" chapter — tray,
  autostart, and how to get back into the dashboard after you close the
  terminal or reboot.
- **Door 3 — `commands.md`** (restructured): every command with a "Where in the
  Web UI?" column, agent-oriented material split into its own section, and a
  new `troubleshooting.md` page carved out of it.

Plus `providers.md` gets an honest cost-to-start table (tiers first), and the
README shrinks to a short pitch that links to the docs site.

**Docs pipeline.** `docs/user/*.md` is the single source of truth. Rendering
happens at **commit time**, not deploy time: `scripts/build-docs.py` (stdlib +
pinned renderer) writes `landing/docs/*.html`, which is committed. CI runs
`build-docs.py` then `git diff --exit-code landing/docs`, so stale or
hand-edited HTML fails the build. `scripts/check-docs.py` adds two honesty
gates: any `vX.Y.Z` in `docs/user/`, `landing/`, `README.md`, or
`src/anyscribe/skill/` must equal `pyproject.toml`'s version (or carry an
explicit `<!-- version-pin-ok -->` marker on the same line, for genuine
historical references), and every `@mcp.tool()` in `mcp/server.py` must appear
in `agents.md`. Both gate on the *invariant*, so they fire on the next drift
too, not just today's.

**Product fixes** (shipped so the docs stop contradicting the product):

- `install.sh` should survive a fresh Apple Silicon Mac — dry-run verified;
  clean-VM leg outstanding — `brew shellenv` activation,
  pip invoked through the resolved `$PY`, pipx installed via brew, and the
  `[tray]` extra included.
- `install.ps1` gains the same `[tray]` extra (parity; read-through review
  only — no Windows VM run).
- `keys/status` counts `local` as configured, which kills the permanent
  "Setup needed" banner for local-only users.
- Groq card in the onboarding wizard; the post-Shutdown screen now names the
  way back in instead of leaving a dead tab.
- "Open at login" toggle in Settings (macOS only, hidden elsewhere), wired to
  the existing launchd service and **refused when the `[tray]` extra isn't
  installed** — a toggle that silently does nothing is worse than no toggle.

## Opus-review corrections that shaped the spec

The design was approved, then revised after an independent Opus 5 review
(approve-with-changes, all findings folded in). Two corrections changed the
shape of the work:

1. **MCP as a capability split, not a duplicate.** The draft described the
   skill and the MCP server as two interchangeable entry points. They aren't —
   they cover different capability sets, and documenting them as equivalents
   would have sent readers down the wrong door. `agents.md` documents the split.
2. **Commit-time render, not deploy-time.** The draft had the landing build
   render docs at deploy. Rendering at commit time makes the HTML reviewable in
   the diff and lets CI catch staleness with `git diff --exit-code` — a gate
   that is impossible if rendering happens after the merge.

## Deliberately out of scope (spec §4)

Recorded here so nobody re-litigates them mid-review: signed `.dmg`/`.exe`
installers (a real fix, but for a different audience), an ffmpeg dependency
step inside the web wizard (we fixed the false claim instead), flipping the
default quality tier to `free`/local (a product-behaviour change deserving its
own decision), a landing-page pitch/style redesign (facts corrected only),
auto-retry on port conflict and the sarvam/sargam spelling alias, deleting
`dist/` (gitignored, never committed), and Windows *functional* install testing
— the `install.ps1` work in this branch is a code review, not a VM run.

## Fresh-environment install verification (spec §6)

Required before release. Two of the three legs ran at the time of writing; the
Docker/Ubuntu leg landed after (see below). Recorded verbatim.

**Docker/Ubuntu leg — PASS** (run later, once a Docker daemon was available;
the original note here read "NOT RUN — `docker info` reports the daemon
unavailable"). A clean `docker run ubuntu:24.04` container with curl, sudo,
python3, pip and ffmpeg preinstalled, prompts answered through a pty:
`install.sh` detected an externally-managed pip, fell back to pipx via the apt
branch, printed the success box and exited 0. `scribe --version` then printed
`anyscribe v0.16.0`.

Two honest caveats:

- The installed package came **from PyPI, not from this branch** — so what this
  leg verifies is the *script logic* (OS detection, externally-managed-pip
  detection, the pipx fallback, the prompt flow), not this branch's package
  contents.
- The container needed **`sudo` preinstalled**. `install.sh` hardcodes `sudo`
  in front of `apt`/`dnf`/`pacman`, so in a bare root container without sudo it
  dies with exit 127. Harmless on normal desktop Linux, where sudo is always
  present — recorded as a known limitation, not fixed here.

**PATH-stripped dry run — PASS (Homebrew branch fires).**
`env PATH=/usr/bin:/bin HOME="$HOME" bash install.sh --dry-run` with stdin
closed reproduces the fresh-Mac condition (no brew, no user `bin` dirs). Note
the script reads answers from `/dev/tty` by design, so with `< /dev/null` it
dies at the first prompt — honest behaviour, worth knowing before anyone tries
to pipe it in CI:

```
==> Detected OS: macos
  ! Homebrew not found. It's needed to install dependencies.
    Install from: https://brew.sh
install.sh: line 129: /dev/tty: Device not configured
```

Re-run under a pty (`script -q /dev/null`, answers defaulted) to get past the
prompts:

```
==> Detected OS: macos
  ! Homebrew not found. It's needed to install dependencies.
    Install from: https://brew.sh
    Install Homebrew now? [Y/n]
==> Installing Homebrew...
  ! Homebrew will ask for your Mac password and can take 10-20 minutes — this is normal.
    [dry-run] Would install Homebrew

==> Checking Python...
  ! Python 3.10+ not found
    Install Python? [Y/n]
  ✗ Could not auto-install Python. Please install it manually.
```

Both the Homebrew-missing branch and its warnings fire as intended, and the
Python fallback fails loudly (correct — dry-run never actually installed brew,
so there is nothing to install Python with).

**macOS clean-VM leg — NOT RUN.** Needs Rishabh's hardware (UTM VM or a spare
Mac without Homebrew). Flagged, not faked.

## Process findings worth keeping

- **The stale-venv trap.** The repo `.venv` and the system Python were still
  pointing at the pre-rename (`anyscribecli`) paths, so `pytest` was exercising
  a ghost install. Fixed mid-run with `pip3 install -e .`. If tests pass but
  behave like an older build, suspect the editable install before the code.
- **A zsh glob can eat your evidence.** A verification step ran a `grep` whose
  unquoted glob zsh aborted before execution; the empty output was read as "no
  matches — finding confirmed negative". It wasn't a result, it was a command
  that never ran. Empty output is only evidence when you have confirmed the
  command executed — check the exit status, not the blank screen.

## Backlog item found on the way — and fixed

`src/anyscribe/cli/onboard.py:847` — the onboarding success message printed a
stale skill path, `~/.claude/skills/scribe/`. The real path is
`~/.claude/skills/anyscribe/` (`config/paths.py:47`). Found during review and
initially carried into BACKLOG.md as out of scope, then **fixed on this branch
after all** in commit `0728585`, along with the same stale path in
`docs/user/commands.md`. No test covers the success message, before or after.

## Gate at close-out

`ruff check src tests` clean · `pytest` 459 passed, 1 skipped ·
`ui` lint + build clean · `build-docs.py` rendered 6 pages + index ·
`git diff --exit-code landing/docs` clean · `check-docs.py` clean.
