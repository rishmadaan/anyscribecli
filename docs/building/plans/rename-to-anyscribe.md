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
