# Plan — rename `anyscribecli` → `anyscribe`

**Date:** 2026-07-21
**Status:** approved, not started
**Target release:** `0.14.0` (milestone bump — identity change is a milestone)
**Adversarial review:** Fable, 2026-07-21 — 4 blockers + 3 serious found, all folded in below.
Repro artifacts for B2/B3 lived in the session scratchpad under `repro/`.

## Decisions already made

| Question | Answer |
|---|---|
| Command name | `anyscribe` primary, `scribe` kept as permanent alias, `ascli` kept |
| Old private repo `rishmadaan/anyscribe` | Rename to `anyscribe-web-archive`, archive it |
| Old PyPI project `anyscribecli` | Final shim release with **working legacy scripts**; never deleted (PyPI can't) |

## Five identities, renamed independently

| # | Identity | From | To | Breaks if wrong |
|---|---|---|---|---|
| 1 | PyPI distribution | `anyscribecli` | `anyscribe` | `pip install` for existing users |
| 2 | Python import package | `src/anyscribecli/` | `src/anyscribe/` | every import, 146 files |
| 3 | GitHub repo | `rishmadaan/anyscribecli` | `rishmadaan/anyscribe` | PyPI trusted publishing, install.sh URLs |
| 4 | Command | `scribe` | `anyscribe` (+`scribe`, +`ascli`) | muscle memory, Claude skill, MCP registration |
| 5 | Config dir | `~/.anyscribecli/` | `~/.anyscribe/` | user's API keys, history, downloads |

## Three hazards that shape the whole sequence

### H1 — PyPI trusted publishing binds to the repo *name*

`.github/workflows/publish.yml` uses `pypa/gh-action-pypi-publish` with `id-token: write`.
PyPI stores `(owner, repo name, workflow filename, environment)` per project. So:

1. Project `anyscribe` has no publisher yet → needs a **pending publisher** before the first tag.
2. Renaming the repo **invalidates** the existing binding for `anyscribecli`.

**The GitHub repo rename must happen LAST.** Confirmed against current PyPI docs.
Note: a pending publisher does **not** reserve the name — it only converts on first
publish. Keep the Phase 0 → Phase 3 window to hours, and re-check the 404 right before
releasing. `publish.yml` declares no `environment:`, so leave that field **blank** on the
pending-publisher form or minting fails.

### H2 — pip's uninstall order deletes the old console scripts

Proven with a repro, not theory. `pip install --upgrade anyscribecli` resolves
dependencies first: it installs `anyscribe` (writing `bin/scribe`), **then** uninstalls
old `anyscribecli`, whose RECORD still lists `bin/scribe` — deleting the file that was
just written — then installs the shim.

A shim with no `[project.scripts]` therefore **deletes `scribe`, `ascli`, and `scribe-mcp`
for every upgrading user.** Worse: `core/updater.py:186 _pip_update()` runs exactly that
command, so `scribe update` would destroy the `scribe` command mid-update. pipx users
(the `install.sh` fallback path) would end up with **zero** commands.

**Fix:** the shim re-declares all three legacy scripts pointing at the *new* module. It
installs last, so it rewrites the deleted files. Verified working in the repro.

### H3 — the config-dir move is the only irreversible step

Good news first: `config.yaml` stores no absolute paths into the app home
(`workspace_path` points at `~/anyscribe`, outside it; checkpoints are keyed by audio
hash; the HF model cache lives in `~/.cache/huggingface`). A correctly-timed move is
content-safe.

The danger is *timing*. Today `maybe_migrate_*` is only called from
`core/orchestrator.py:67` (inside a transcription) and the two onboard paths. But
`config/settings.py` `load_config`/`load_env` read `CONFIG_FILE`/`ENV_FILE` directly, and
`ensure_app_dirs()` **creates** the new dir. So if a user's first post-upgrade command is
`scribe ui` or `scribe config` rather than a transcription: empty `~/.anyscribe` gets
created and read → "not onboarded" → wizard runs → keys written to the new dir → **both
dirs exist → a "move only if target missing" guard blocks migration forever** and the old
keys, sessions, and downloads are stranded.

**Fix:** migrate at a true choke point, before any app-home read, and make the guard
tolerate an empty target. Detailed in Phase 1.

## Sequence

### Phase 0 — clear the runway (no code, ~10 min)

- [ ] `gh repo rename anyscribe-web-archive --repo rishmadaan/anyscribe`
- [ ] `gh repo archive rishmadaan/anyscribe-web-archive`
- [ ] Confirm `https://pypi.org/pypi/anyscribe/json` still 404s
- [ ] PyPI → Account → Publishing → add **pending publisher**:
      owner `rishmadaan`, repo **`anyscribecli`** (not yet renamed), workflow `publish.yml`,
      environment **blank**, project name `anyscribe`

**Gate:** `gh api repos/rishmadaan/anyscribe --jq .full_name` returns
`rishmadaan/anyscribe-web-archive`. (It will not 404 — GitHub keeps a redirect. That's
fine; Phase 5 legitimately reclaims the name.)

### Phase 1 — rename inside the code (branch `rename/anyscribe`)

**Mechanical rename**

- [ ] `git mv src/anyscribecli src/anyscribe`
- [ ] Sweep imports: `anyscribecli.` → `anyscribe.`, `import anyscribecli` → `import anyscribe`
      across `src/` and `tests/`
- [ ] `pyproject.toml`: `name`, `[project.urls]`, `packages = ["src/anyscribe"]`, and:
  ```toml
  [project.scripts]
  anyscribe     = "anyscribe.cli.main:app"
  scribe        = "anyscribe.cli.main:app"     # permanent alias
  ascli         = "anyscribe.cli.main:app"     # legacy alias
  anyscribe-mcp = "anyscribe.mcp.server:main"
  scribe-mcp    = "anyscribe.mcp.server:main"  # permanent alias
  ```

**Config dir migration — the careful part (fixes H3)**

- [ ] `config/paths.py`: `APP_HOME = Path.home() / ".anyscribe"`,
      add `LEGACY_APP_HOME = Path.home() / ".anyscribecli"`
- [ ] `core/migrate.py`: add `maybe_migrate_app_home()`:
  - migrate when legacy exists **and** (target missing **or** target holds neither
    `config.yaml` nor `.env`) — the empty-target case is what breaks people
  - when the target already exists, move **per entry**, skipping any name that already
    exists in the target. Never clobber.
  - skip entirely if anything under legacy `tmp/` was modified in the last 5 minutes
    (`ponytail:` crude mid-flight guard — a real lock only if this ever bites)
- [ ] Call it from **all three** read choke points, not just the orchestrator:
      top of `ensure_app_dirs()`, `load_config()`, and `load_env()` in `config/settings.py`.
      Three one-line calls. This is the fix for H3 — do not skip any of them.

**Hardcoded paths the plan would otherwise miss (fixes B4, S1)**

- [ ] `scripts/release.sh:62` — `INIT_FILE="src/anyscribecli/__init__.py"` (release fails
      outright without this), plus the Actions URL echo near line 148
- [ ] `ui/vite.config.ts:17` — `outDir: '../src/anyscribe/web/static'`. Without this,
      `npm run build` resurrects an untracked `src/anyscribecli/` and the real bundle
      never updates.
- [ ] `.github/workflows/ci.yml:60` **and** `publish.yml` — `git diff --exit-code --
      src/anyscribe/web/static`. On a nonexistent path `git diff` exits 0, so the
      stale-bundle guard silently becomes a no-op instead of failing loudly.
- [ ] `core/updater.py` — `PYPI_PACKAGE`, `GITHUB_REPO`, **and** the two git paths:
      `origin/main:src/anyscribecli/__init__.py` in `_git_check_latest`, and `version_file`
      in `_git_update`
- [ ] `install.sh` (incl. `python3 -m anyscribecli` near line 325) and `install.ps1`

**Skill plumbing (fixes S2)**

- [ ] `config/paths.py:49` — `ASCLI_SKILL_TARGET` → `~/.claude/skills/anyscribe/`
      (the constant lives here, not in `skill_cmd.py`)
- [ ] Remove any stale `~/.claude/skills/scribe/` from **inside `copy_skill_files()`**
      (`cli/main.py:54-100`), not from the install command. That function is the silent
      auto-install/auto-update path every existing user hits — putting the cleanup only in
      the explicit command leaves two competing scribe skills on every other machine.

**Gate:** `pytest` green · `ruff check src tests` clean ·
`grep -ri anyscribecli src/ tests/ scripts/ ui/ .github/` returns only the deliberate
`LEGACY_APP_HOME` constant.

### Phase 2 — docs, skill content, landing (same branch)

- [ ] `src/anyscribe/skill/SKILL.md` — frontmatter `name: anyscribe`, and
      `allowed-tools` must gain `Bash(anyscribe *)` alongside `Bash(scribe *)`, or a skill
      that leads with `anyscribe` triggers a permission prompt on every single call
- [ ] `skill/references/{commands,providers,config,troubleshooting}.md` — lead with
      `anyscribe`, note `scribe` as the short alias
- [ ] `ui/src/components/OnboardingWizard.tsx:365` — tells users their keys live in
      `~/.anyscribecli/.env`. That's the primary onboarding surface; it would ship a lie.
- [ ] Rebuild and commit the frontend bundle (`npm run build`) — the current committed
      bundle contains `.anyscribecli` and CI's guard won't catch it
- [ ] `README.md`, `CLAUDE.md`, `AGENTS.md`, `BACKLOG.md`
- [ ] `docs/user/*.md`, `docs/building/architecture.md`, `_index.md` row
- [ ] `landing/index.html` — GitHub links, PyPI link, install one-liners, `scribe` examples
- [ ] Journal entry `docs/building/journal/2026-07-21-rename-to-anyscribe.md`

Vercel project is **already** named `anyscribe` — no change needed there.

**Gate:** `grep -ril anyscribecli .` returns only historical journal/plan entries
(append-only, must NOT be rewritten) and `LEGACY_APP_HOME`.

### Phase 3 — ship the new name

- [ ] Re-check `pypi.org/pypi/anyscribe/json` is still 404 (the pending publisher did not
      reserve it)
- [ ] Merge to `main`
- [ ] `./scripts/release.sh 0.14.0 "rename to anyscribe"`
- [ ] Watch the Action; confirm the pending publisher converted to active

**Gate:** clean venv → `pip install anyscribe` → `anyscribe --version` = `0.14.0`,
`scribe --version` = same.

### Phase 4 — ship the shim for the old name

From a throwaway branch off `main`, **before** the repo rename, while the existing
`anyscribecli` trusted publisher still matches.

- [ ] Branch `shim/anyscribecli-final`, strip `pyproject.toml` to:
  ```toml
  [project]
  name = "anyscribecli"
  version = "0.13.5"
  description = "Renamed to `anyscribe`. Install that instead."
  dependencies = ["anyscribe>=0.14.0"]

  [project.scripts]          # MUST stay — see H2
  scribe     = "anyscribe.cli.main:app"
  ascli      = "anyscribe.cli.main:app"
  scribe-mcp = "anyscribe.mcp.server:main"

  [tool.hatch.build.targets.wheel]
  bypass-selection = true     # metadata-only wheel; hatchling errors without it
  ```
- [ ] Publish **by hand with twine**, not by tagging. Tagging `v0.13.5` would run
      publish.yml's pytest/npm steps against a gutted branch and fail. Twine needs a
      **project-scoped API token for `anyscribecli`** — create it first; trusted
      publishing only works from the Action.
- [ ] Delete the branch

**Gate (this is S3 — the clean-venv test cannot catch H2):**
```bash
python -m venv /tmp/up && source /tmp/up/bin/activate
pip install anyscribecli==0.13.4       # simulate a real existing user
pip install --upgrade anyscribecli
scribe --version && ascli --version && scribe-mcp --help   # must all still resolve
```
Repeat once via `pipx` if cheap.

### Phase 5 — rename the repo, repair the plumbing

Run Phases 3 → 4 → 5 **in one sitting.** Between 3 and 5, the shipped `pyproject.toml`
URLs and `updater.py`'s `GITHUB_REPO` point at `github.com/rishmadaan/anyscribe`, which
still redirects to the archived *web* repo — the updater's git fallback would clone a
non-Python project and fail.

- [ ] `gh repo rename anyscribe --repo rishmadaan/anyscribecli`
- [ ] `git remote set-url origin https://github.com/rishmadaan/anyscribe.git`
- [ ] PyPI → project `anyscribe` → Publishing → update trusted publisher repo to `anyscribe`
- [ ] PyPI → project `anyscribecli` → same
- [ ] Rename local dir `~/labs/projects/anyscribecli` → `~/labs/projects/anyscribe`
- [ ] Vercel: confirm the deploy still builds from the renamed repo

**Gate:** a no-op tagged release (`0.14.1`) publishes green. Do not skip — it is the only
real proof the trusted-publisher rebinding worked.

### Phase 6 — Rish's own machine

- [ ] `pip install --upgrade --force-reinstall anyscribe`
- [ ] `anyscribe skill install`
- [ ] Re-register the MCP server under the new name in `~/.claude.json` (current key: `scribe`)
- [ ] Confirm `~/.anyscribecli/` auto-migrated to `~/.anyscribe/` with keys and history intact

Stale-skill cleanup is handled in code (Phase 1) — no manual step needed.

## Acceptance test (run end to end, once)

```bash
# 1. Fresh install
python -m venv /tmp/rn && source /tmp/rn/bin/activate
pip install anyscribe
anyscribe --version && scribe --version && ascli --version
anyscribe transcribe "https://www.youtube.com/watch?v=<short clip>" --json
ls ~/anyscribe/ && ls ~/.anyscribe/

# 2. Upgrade path (catches H2 — the fresh install above cannot)
python -m venv /tmp/up && source /tmp/up/bin/activate
pip install anyscribecli==0.13.4 && pip install --upgrade anyscribecli
scribe --version && ascli --version

# 3. Config migration, both-dirs case (catches H3)
#    seed ~/.anyscribecli with a .env, create an EMPTY ~/.anyscribe, then run
#    `anyscribe config` — keys must survive.
```

## Explicitly NOT doing

- Not chasing `scribe` on PyPI (taken since 2006; PEP 541 is months and uncertain)
- Not rewriting historical journal entries
- Not deleting the `anyscribecli` PyPI project (impossible) or yanking its releases
- Not renaming the MCP server's internal `FastMCP("scribe")` name or `scribe://` resource
  URIs — consistent with the permanent-alias policy

## Rollback

- **Phases 1–2** are a branch — discard it.
- **Phase 0** is not branch-scoped: the repo rename/archive and the pending publisher both
  need manual reversal (both are trivially reversible).
- **Phase 3**, if publish fails *after* tagging: `v0.14.0` is burned (`release.sh` refuses
  tag reuse). Delete the tag locally and on origin, or bump to `0.14.1`.
- **After Phase 3 succeeds** the new PyPI release is permanent but purely additive — the
  old package keeps working untouched until Phase 4.
- **Phase 5** is the only one-way door, and GitHub redirects the old repo URL indefinitely.

---

# Execution — Subagent-Driven Development

Tasks below cover **Phases 1 and 2 only** (code + docs), plus the user-machine
updater and its rehearsal harness. Phases 0, 3, 4, 5, 6 are manual steps Rish runs
against PyPI, GitHub, and his own machine — **no subagent performs them.**

## Global Constraints (bind every task)

1. **Five commands must resolve after every task:** `anyscribe`, `scribe`, `ascli`,
   `anyscribe-mcp`, `scribe-mcp`. `scribe` and `ascli` are permanent aliases, not
   deprecations — never print a deprecation warning for them.
2. **Never clobber user data.** Any file move skips a destination that already exists.
   No `shutil.rmtree` on anything under the user's home except a stale
   `~/.claude/skills/scribe/` directory that this project itself wrote.
3. **`LEGACY_APP_HOME` in `config/paths.py` is the only place the string
   `.anyscribecli` may survive under `src/`** after Task 2.
4. **Historical records are append-only.** Never rewrite any existing file under
   `docs/building/journal/` or `docs/superpowers/plans/`. They record what was true then.
5. **No new runtime dependencies.** Stdlib first. `shutil`, `pathlib`, `json`, `os`.
6. **Gates for every task:** `pytest` passes and `ruff check src tests` is clean.
   Run them; paste the output in your report.
7. **Ponytail:** smallest diff that works. No speculative abstraction, no config for a
   value that never changes, no interface with one implementation.
8. Work happens in the worktree at `/Users/rish/labs/projects/anyscribe-rename` on
   branch `rename/anyscribe`. Commit your own work.

## Task 1: App-home migration logic

**Why this is first and why it is the riskiest task in the plan.** This is the only
irreversible step in the whole rename — it moves the user's API keys. It is
deliberately done *before* the package rename so the diff stays small and reviewable.

**Files:** `src/anyscribecli/config/paths.py`, `src/anyscribecli/core/migrate.py`,
`src/anyscribecli/config/settings.py`, new `tests/test_migrate_app_home.py`.
Note the package is still named `anyscribecli` at this point — that is correct, do not
rename it in this task.

**Change 1 — `config/paths.py`:**
```python
APP_HOME = Path.home() / ".anyscribe"
LEGACY_APP_HOME = Path.home() / ".anyscribecli"
```
Everything else derived from `APP_HOME` follows automatically. Do not add other constants.

**Change 2 — `core/migrate.py`, add `maybe_migrate_app_home() -> bool`.**
Follow the shape of the existing `maybe_migrate_media_to_downloads()` in the same file.
Return `True` only if something was actually moved. Exact decision table:

| Legacy dir | New dir | Action |
|---|---|---|
| missing / not a dir | any | return False |
| exists | missing | `shutil.move` the whole dir, return True |
| exists | exists, holds **neither** `config.yaml` nor `.env` | move entries one by one; skip any name already present in the target; return True if ≥1 moved |
| exists | exists, holds `config.yaml` or `.env` | return False — already migrated, or the user has a real new-style config |

The third row is the case that matters: a user whose first post-upgrade command created
an empty `~/.anyscribe`. Without it their keys are stranded forever.

**Mid-flight guard:** before doing anything, if any file under `LEGACY_APP_HOME/tmp/`
has an mtime within the last 300 seconds, return False — another process may be
transcribing. One `if`, not a lock file. Mark it with a `ponytail:` comment naming the
ceiling ("crude mtime guard; a real lock only if this ever bites").

Must be idempotent — safe to call any number of times.

**Change 3 — call it from the three real choke points**, in `config/settings.py`:
the top of `load_config()`, `load_env()`, and `ensure_app_dirs()`. Read those functions
first — they currently touch `CONFIG_FILE` / `ENV_FILE` / `mkdir` directly, which is
exactly why the orchestrator-only call site was insufficient.

Run at most **once per process** — a module-level `_migrated = False` flag flipped on
first call. These functions are called repeatedly and must not stat the filesystem every
time. Watch for import cycles: `settings.py` importing `migrate` which imports `paths`.
Import inside the function if needed, matching how `orchestrator.py` already does it.

**Change 4 — `tests/test_migrate_app_home.py`.** Use `monkeypatch` to point
`Path.home()` at a `tmp_path`. One test per row of the decision table, plus:
- collision case: legacy and target both hold `config.yaml`, target is otherwise empty →
  target's copy wins, legacy's copy is **not** lost (assert it still exists on disk)
- mid-flight case: a fresh file in `legacy/tmp/` → returns False, nothing moved
- idempotency: calling twice is a no-op the second time

Do not modify the existing migration tests.

**Done when:** `pytest` green, `ruff check src tests` clean, and the new test file fails
if you revert any single branch of the decision table.

## Task 2: Mechanical package rename

Rename the import package and fix every hardcoded path. Pure mechanics — no behavior
changes. Do not touch anything under `docs/` (that is Task 5).

**The rename itself:**
- `git mv src/anyscribecli src/anyscribe`
- Rewrite imports across `src/` and `tests/`: `anyscribecli.` → `anyscribe.`,
  `import anyscribecli` → `import anyscribe`, `pkg_files("anyscribecli")` → `"anyscribe"`
- `pyproject.toml`: `name = "anyscribe"`, `packages = ["src/anyscribe"]`,
  `[project.urls]` → `github.com/rishmadaan/anyscribe`, and exactly these scripts:
  ```toml
  [project.scripts]
  anyscribe     = "anyscribe.cli.main:app"
  scribe        = "anyscribe.cli.main:app"
  ascli         = "anyscribe.cli.main:app"
  anyscribe-mcp = "anyscribe.mcp.server:main"
  scribe-mcp    = "anyscribe.mcp.server:main"
  ```

**Hardcoded paths that break silently if missed — verify each one by opening the file:**
- `scripts/release.sh` — `INIT_FILE` at ~line 62 (release dies outright without this),
  and the GitHub Actions URL echo near line 148
- `ui/vite.config.ts` line 17 — `outDir: '../src/anyscribe/web/static'`. Without this
  `npm run build` recreates an untracked `src/anyscribecli/` and the real bundle never updates.
- `.github/workflows/ci.yml` line 60 **and** `.github/workflows/publish.yml` — the
  `git diff --exit-code -- src/anyscribe/web/static` guard. On a path that does not
  exist `git diff` exits 0, so a missed rename turns the guard into a silent no-op.
- `src/anyscribe/core/updater.py` — `PYPI_PACKAGE`, `GITHUB_REPO`, **and** two more:
  the `origin/main:src/anyscribecli/__init__.py` ref in `_git_check_latest`, and the
  `version_file` path in `_git_update`
- `install.sh` (including `python3 -m anyscribecli` near line 325) and `install.ps1`
- `src/anyscribe/config/paths.py` line ~49 — `ASCLI_SKILL_TARGET` →
  `~/.claude/skills/anyscribe/`. The constant lives here, not in `skill_cmd.py`.

**One behavior change, deliberately in this task:** in `copy_skill_files()`
(`src/anyscribe/cli/main.py`, ~lines 54-100), remove a stale
`~/.claude/skills/scribe/` directory if present. It must go in *this* function, not in
the `skill install` command — this is the silent auto-install path every existing user
hits, and without it they end up with two competing scribe skills, the old one serving
outdated commands. Only remove that exact directory, and only if it exists.

**Do not** rename the MCP server's internal `FastMCP("scribe")` name or its `scribe://`
resource URIs — consistent with the permanent-alias policy.

**Done when:** `pytest` green, `ruff check src tests` clean, and
`grep -rn anyscribecli src/ tests/ scripts/ ui/ .github/ install.sh install.ps1`
returns exactly one hit: `LEGACY_APP_HOME` in `config/paths.py`.

## Task 3: The `anyscribe migrate` command

A shipped command every existing user runs once. It makes a machine that has
`anyscribecli` into a machine that has `anyscribe`, and reports honestly.

**Files:** new `src/anyscribe/cli/migrate_cmd.py`, registered in
`src/anyscribe/cli/main.py` alongside the other subcommands. New
`tests/test_migrate_cmd.py`.

**Signature:** `anyscribe migrate [--dry-run] [--json]`

**The five steps it performs, in order:**
1. **Config dir** — call `maybe_migrate_app_home()` from Task 1. Do not reimplement it.
2. **Stale skill dir** — remove `~/.claude/skills/scribe/` if present.
3. **Skill install** — install the bundled skill to `~/.claude/skills/anyscribe/` by
   calling the existing `copy_skill_files()`. Do not duplicate its logic.
4. **MCP registration** — in `~/.claude.json`, if `mcpServers` has a `scribe` key whose
   command references `scribe-mcp` or `anyscribecli`, re-key it to `anyscribe` and point
   the command at `anyscribe-mcp`. Rules: back up to `~/.claude.json.bak` first; write
   via temp file + `os.replace` so a crash cannot truncate it; if the file is missing or
   does not parse as JSON, print a warning and skip — never raise, never write.
   `mcpServers` may be nested per-project in this file — find every occurrence, not just
   a top-level one.
5. **Verification** — check `anyscribe`, `scribe`, `ascli` each resolve via
   `shutil.which`. Report each. Do not attempt to repair them; if one is missing, tell
   the user to run `pip install --force-reinstall anyscribe`.

**`--dry-run` writes nothing at all** — not the backup, not the skill files, nothing.
It prints the same report with a closing `nothing written (--dry-run)` line. This is the
flag Rish will actually use first, so it must be trustworthy: if dry-run says a file
moves, the real run must move that exact file.

**Output shape** (this was reviewed and approved — match it):
```
  ~/.anyscribecli  →  ~/.anyscribe        12 files, 4.2 MB
    config.yaml, .env (3 keys), sessions/, downloads/
  ~/.claude/skills/scribe/  →  remove (stale)
  ~/.claude/skills/anyscribe/  →  install
  ~/.claude.json  mcp "scribe" → "anyscribe"
  commands: anyscribe ✓  scribe ✓  ascli ✓
```
Report `.env` as a **count of keys, never the keys themselves** — this output will be
pasted into issues. Use `rich` as the rest of the CLI does. `--json` emits the same
facts as a machine-readable object, per this project's `--json` convention.

**Idempotent.** Running it twice must be safe and the second run should report that
there was nothing to do.

**Tests:** monkeypatch `Path.home()` to `tmp_path`. Cover: full migration from a
realistic old layout; a second run is a no-op; `--dry-run` leaves the filesystem
byte-identical (assert by comparing a recursive file listing before and after); missing
`~/.claude.json`; malformed `~/.claude.json`; nested per-project `mcpServers`.

## Task 4: Rehearsal harness

`scripts/rehearse-migration.sh` — builds a realistic fake user, runs the real migration
against it, asserts nothing was lost. This is how we earn the right to trust Task 3.

**Hard requirement: it must never touch the real `$HOME`.** Override `HOME` (and
`XDG_*` if the code reads them) to a `mktemp -d` directory. Assert near the top that
`$HOME` is inside the temp dir before writing anything, and abort otherwise. A bug here
destroys Rish's actual API keys — this guard is not optional.

**What it builds in the fake home:**
- `~/.anyscribecli/.env` with 3 recognizable fake keys
- `~/.anyscribecli/config.yaml` with a non-default `workspace_path`
- `~/.anyscribecli/sessions/` with 8 files, `~/.anyscribecli/downloads/audio/` with one
- `~/.claude/skills/scribe/` with a stale `SKILL.md`
- `~/.claude.json` with an `mcpServers.scribe` entry
- the package installed into a throwaway venv

**What it asserts after running `anyscribe migrate`:**
all 3 keys present in `~/.anyscribe/.env` with identical values; `workspace_path`
preserved; all 8 session files present; stale skill dir gone; new skill dir present;
`~/.claude.json` has `anyscribe` and not `scribe` under `mcpServers`, and is still valid
JSON; `anyscribe`, `scribe`, `ascli` all resolve.

**Also rehearse the both-dirs case** — the one that strands keys: seed an *empty*
`~/.anyscribe` alongside the populated legacy dir, run, assert the keys still arrive.

Print one line per assertion, `PASS`/`FAIL` at the end, exit non-zero on any failure.
Clean up the temp dir on exit including on failure (`trap`). Plain bash, `set -euo
pipefail`, no new tooling. Keep it readable — Rish will read this script to decide
whether he trusts the migration.

Wire it into `.github/workflows/ci.yml` as its own step so it runs on every push.

## Task 5: Skill, docs, frontend copy

Everything a user reads. Per this project's CLAUDE.md, stale skill docs are a bug of the
same severity as a broken command — this task is not cosmetic.

**Claude Code skill** (`src/anyscribe/skill/`):
- `SKILL.md` frontmatter: `name: anyscribe`, and `allowed-tools` must gain
  `Bash(anyscribe *)` alongside the existing `Bash(scribe *)`. Without this every single
  skill invocation triggers a permission prompt.
- `SKILL.md` body and `references/{commands,providers,config,troubleshooting}.md`:
  lead with `anyscribe`, mention `scribe` once as the shorter permanent alias.
- Add a short troubleshooting entry for "I upgraded and my keys are gone" pointing at
  `anyscribe migrate`.

**Frontend:**
- `ui/src/components/OnboardingWizard.tsx` line ~365 tells users their keys live in
  `~/.anyscribecli/.env`. Fix the copy. Grep the rest of `ui/src/` for other occurrences.
- Run `npm run build` in `ui/` and **commit the regenerated bundle** under
  `src/anyscribe/web/static`. The committed bundle currently contains `.anyscribecli`;
  CI's guard cannot catch this because Task 2 changed the path it watches.

**Docs:** `README.md`, `CLAUDE.md`, `AGENTS.md`, `BACKLOG.md` (add the 0.14.0 row),
`docs/user/{getting-started,commands,configuration,providers}.md` (document
`anyscribe migrate` in `commands.md` including the flags table),
`docs/building/architecture.md`, and a new row in `docs/building/_index.md`.

**Landing:** `landing/index.html` — GitHub links, the PyPI link, both install one-liners,
and the `scribe "https://..."` example.

**Journal:** new `docs/building/journal/2026-07-21-rename-to-anyscribe.md` with
frontmatter (type, tags, tldr) covering why the rename happened, the two proven blockers
(pip's uninstall order deleting console scripts; the both-dirs migration trap), and how
each was solved.

**Do not rewrite any existing journal or plan file** — including this plan's own history.
Only add the new entry and the new `_index.md` row.

**Done when:** `pytest` green, `ruff check src tests` clean, `npm run lint` in `ui/`
clean, and `grep -ril anyscribecli .` returns only `LEGACY_APP_HOME`, historical
journal/plan entries, and this plan file.
