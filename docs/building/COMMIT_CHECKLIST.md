# Post-Commit Checklist

**Required after every significant commit.** This ensures documentation stays in sync with code. Agents and developers must follow this checklist before considering work complete.

> Referenced from `CLAUDE.md` and `AGENTS.md`. This is the canonical source.

## After every commit that changes user-facing behavior

User-facing = new command, new flag, changed output, changed config option, new provider, new platform.

- [ ] **README.md** — Does it still accurately describe the tool?
  - Commands table matches actual commands
  - Providers table matches actual providers (no "planned" for built features)
  - Install instructions are current
  - Config example matches actual config.yaml defaults
  - Version references match `__init__.py`

- [ ] **docs/user/commands.md** — Does the Quick Overview table list all commands?
  - Every command has a section with flags table and examples
  - JSON output examples are accurate
  - Supported Platforms table reflects actual downloaders
  - Version references match

- [ ] **docs/user/configuration.md** — Do all settings match the `Settings` dataclass?
  - Provider table lists all registered providers as active
  - No "(planned)" for implemented features
  - Workspace structure diagram is accurate

- [ ] **docs/user/getting-started.md** — Does the flow match the actual onboarding?
  - Install methods are current
  - Version references match
  - Troubleshooting section covers common errors

- [ ] **docs/user/providers.md** — Does the comparison table reflect reality?
  - All providers listed with correct status
  - Pricing, limits, and language counts are accurate
  - Setup instructions work

## After every commit that changes architecture or internals

- [ ] **docs/building/architecture.md** — Does it reflect the current layer structure?
  - All commands listed in CLI Layer section
  - All providers listed in Provider Layer section
  - Key Technical Decisions up to date

- [ ] **docs/building/providers.md** — Provider-specific notes accurate?
  - API endpoints, auth headers, limits
  - New providers added to the table and "Adding a Provider" steps

- [ ] **docs/building/downloaders.md** — Downloader notes accurate?
  - Registry pattern description matches code
  - New downloaders documented

- [ ] **docs/building/_index.md** — New journal entry for significant changes?
  - Row added to the table (newest first)

- [ ] **CLAUDE.md** — File tree in Architecture section matches actual files?
  - New files listed
  - User doc file list includes any new docs

- [ ] **AGENTS.md** — Quick Context section lists all key files?

## After version bumps

- [ ] `src/anyscribecli/__init__.py` — `__version__` updated
- [ ] `pyproject.toml` — `version` field matches
- [ ] All docs referencing version number updated (search for old version)
- [ ] `BACKLOG.md` — version section marked complete, new section added
- [ ] Git tag created: `git tag vX.Y.Z`

## After adding a new provider

1. [ ] `src/anyscribecli/providers/<name>.py` — implements TranscriptionProvider
2. [ ] `providers/__init__.py` — added to PROVIDER_REGISTRY
3. [ ] `cli/onboard.py` — added to PROVIDER_INFO dict
4. [ ] `docs/building/providers.md` — added to table + provider-specific notes
5. [ ] `docs/user/providers.md` — added to comparison table + setup section
6. [ ] `docs/user/commands.md` — added to Available Providers table
7. [ ] `docs/user/configuration.md` — added to provider table
8. [ ] `README.md` — added to providers table

## After adding a new downloader

1. [ ] `src/anyscribecli/downloaders/<name>.py` — implements AbstractDownloader
2. [ ] `downloaders/registry.py` — added to `_load_downloaders()`
3. [ ] `docs/building/downloaders.md` — added to table + notes
4. [ ] `docs/user/commands.md` — added to Supported Platforms table
5. [ ] `README.md` — updated description if it mentions supported platforms

## After adding a new command

1. [ ] `src/anyscribecli/cli/<name>.py` — command implemented
2. [ ] `cli/main.py` — command registered
3. [ ] `docs/user/commands.md` — added to Quick Overview + full section with flags/examples
4. [ ] `README.md` — added to Commands table
5. [ ] `docs/building/architecture.md` — added to CLI Layer commands list + **feature-coverage matrix row** in the "CLI ↔ Web UI: shared backend, asymmetric surfaces" section
6. [ ] `AGENTS.md` — added to Quick Context if it's a key entry point

## After adding or changing a surface-facing feature

A "surface-facing feature" is anything a user can see or trigger from either the CLI or the Web UI — a new command, a new UI action, a new provider, a new flag.

1. [ ] Decide explicitly which surfaces it lives on (CLI, Web UI, both) and note that in the commit message or PR
2. [ ] `docs/building/architecture.md` — update the **feature-coverage matrix** in the "CLI ↔ Web UI: shared backend, asymmetric surfaces" section
3. [ ] If it's on both surfaces, confirm both call the same shared backend module (not via subprocess) — this is architecturally load-bearing
4. [ ] If it's CLI-only or UI-only by design, state the reason in the matrix row's Notes column so future readers know it wasn't a gap

## Quick grep checks

Run these to catch stale references:

```bash
# Find any "planned" or "coming soon" that should be "active"
grep -ri "planned\|coming soon" docs/ README.md

# Find old version numbers
grep -r "v0\.1\.0\|0\.1\.0" docs/ README.md src/

# Find placeholder URLs
grep -r "yourusername" .

# Find TODO/FIXME
grep -ri "todo\|fixme\|hack\|xxx" src/
```
