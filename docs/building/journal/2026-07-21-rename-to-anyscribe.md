---
type: decision
tags: [rename, packaging, pypi, migration, config, cli, mcp, skill]
tldr: "v0.14.0 renames the project from `anyscribecli` to `anyscribe` across five independent identities: PyPI distribution, import package (`src/anyscribecli/` → `src/anyscribe/`), GitHub repo, command (`anyscribe` primary; `scribe`/`ascli` kept as PERMANENT aliases), and config dir (`~/.anyscribecli/` → `~/.anyscribe/`). Two proven blockers shaped the whole sequence: (1) pip resolves dependencies first, so `pip install --upgrade` installs the new package and THEN uninstalls the old one — whose RECORD still lists the shared `bin/scribe` — deleting the console script that was just written; the final `anyscribecli` shim therefore re-declares `scribe`/`ascli`/`scribe-mcp` and installs last. (2) The config-dir move strands keys if a first post-upgrade command (e.g. `anyscribe ui`) creates an EMPTY `~/.anyscribe` before migration runs, because a naive 'move only if target missing' guard then blocks forever; fixed by migrating at every app-home read choke point and tolerating an empty target."
---

# Rename `anyscribecli` → `anyscribe`

**Date:** 2026-07-21
**Branch:** rename/anyscribe
**Target release:** v0.14.0 (milestone — an identity change is a milestone)
**Plan:** `docs/building/plans/rename-to-anyscribe.md` (approved; adversarial review by Fable found 4 blockers + 3 serious, all folded into the plan)

## Why the rename

`anyscribecli` was always a placeholder shape — the `cli` suffix was there only
because a bare `anyscribe` wasn't claimed yet. The product now has three
surfaces (CLI, Web UI, MCP/agent), so a name that advertises "CLI" undersells
it and reads as an afterthought to new users and to the landing page. `anyscribe`
is the real brand: shorter, surface-neutral, and it matches the Vercel project,
the workspace folder (`~/anyscribe/`), and the config dir once migrated. The
command people actually type (`scribe`) stays as a permanent alias, so muscle
memory, the Claude skill, and existing scripts keep working — the rename is
additive at the command layer, not a break.

## Five identities, renamed independently

The rename is not one find-and-replace. Five things carry the name and each
breaks a different way if missed:

1. **PyPI distribution** `anyscribecli` → `anyscribe` (breaks `pip install` for existing users)
2. **Python import package** `src/anyscribecli/` → `src/anyscribe/` (every import)
3. **GitHub repo** `rishmadaan/anyscribecli` → `rishmadaan/anyscribe` (PyPI trusted publishing binding, `install.sh` URLs)
4. **Command** `scribe` → `anyscribe` primary, with `scribe` and `ascli` kept as **permanent** aliases (never deprecated)
5. **Config dir** `~/.anyscribecli/` → `~/.anyscribe/` (the user's API keys, history, downloads)

## The two proven blockers

Both were reproduced, not theorised — repro artifacts lived in the session
scratchpad. They are the reason the sequence is what it is.

### Blocker 1 — pip's uninstall order deletes the shared console scripts

`pip install --upgrade anyscribecli` does **not** uninstall-then-install. It
resolves dependencies first: it installs the new `anyscribe` (writing
`bin/scribe`), **then** uninstalls the old `anyscribecli`, whose `RECORD` file
still lists `bin/scribe` — so pip deletes the very file it just wrote — and only
then installs whatever the old name now points at.

Consequence: a shim for `anyscribecli` that declares **no** `[project.scripts]`
would leave every upgrading user with **no** `scribe`, `ascli`, or `scribe-mcp`
command. Worse, `core/updater.py`'s `_pip_update()` runs exactly that upgrade
command, so `scribe update` would destroy `scribe` mid-update; pipx users (the
`install.sh` fallback) would end up with zero commands.

**Fix:** the final `anyscribecli` shim release re-declares all three legacy
scripts (`scribe`, `ascli`, `scribe-mcp`) pointing at the **new** `anyscribe`
module. Because the shim installs **last** in the resolution order, it rewrites
the deleted files. This is why the plain fresh-install test cannot catch it —
only an upgrade from a real prior version does, so that upgrade path is a
first-class gate in the plan (Phase 4).

### Blocker 2 — the both-dirs config migration trap

`config.yaml` stores no absolute paths into the app home (`workspace_path`
points outside it at `~/anyscribe`; checkpoints are keyed by audio hash; the HF
model cache lives under `~/.cache`), so a correctly-timed move is content-safe.
The hazard is **timing**.

Migration used to run only inside a transcription (from the orchestrator). But
`config/settings.py`'s `load_config`/`load_env` read the config/env files
directly, and `ensure_app_dirs()` **creates** the new dir. So if a user's first
post-upgrade command is `anyscribe ui` or `anyscribe config` rather than a
transcription: an empty `~/.anyscribe` gets created and read → the tool decides
the user isn't onboarded → the wizard runs → new keys land in the new dir →
**both dirs now exist**, and a naive "move only if the target is missing" guard
blocks the migration **forever**. The old keys, sessions, and downloads are
stranded in `~/.anyscribecli/` with no automatic way back.

**Fix, two parts:**
- Migrate at **every** app-home read choke point, not just the orchestrator: the
  top of `ensure_app_dirs()`, `load_config()`, and `load_env()`. Run at most once
  per process (a module-level flag armed by *success*, not by the attempt).
- Make the guard tolerate an **empty** target: migrate when the legacy dir exists
  and the new dir is either missing **or** holds neither `config.yaml` nor `.env`.
  When the target already has real content, move entry-by-entry and skip any name
  already present — never clobber. A crude mtime guard on the legacy `tmp/` dir
  (skip if anything was written in the last 5 minutes) avoids racing a live
  transcription; a real lock only if that ever bites.

The user-facing safety net for anyone who already tripped the trap is
`anyscribe migrate` — a one-shot command that moves config/keys/sessions/
downloads across (never overwriting), refreshes the skill, re-keys the MCP
server registration, and verifies all three commands resolve. `--dry-run` writes
nothing at all, so the preview is trustworthy.

## Sequencing consequences

- **The GitHub repo rename must happen LAST.** PyPI trusted publishing binds to
  `(owner, repo name, workflow, environment)`; renaming the repo invalidates the
  binding, so the new project needs a *pending publisher* before the first tag,
  and the repo rename is deferred until after the first successful publish.
- **The shim is published by hand with twine, not by tagging** — tagging would
  run the publish workflow's pytest/npm steps against a gutted shim branch.

## What we deliberately did NOT do

- Not chasing `scribe` on PyPI (taken since 2006).
- Not rewriting historical journal/plan entries — they record what was true then.
- Not deleting the `anyscribecli` PyPI project (impossible) or yanking releases.
- Not renaming the MCP server's internal `FastMCP("scribe")` name or its
  `scribe://` resource URIs — consistent with the permanent-alias policy.
