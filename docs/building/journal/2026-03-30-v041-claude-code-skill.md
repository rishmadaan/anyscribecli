---
type: project-note
tags: [claude-code, skill, distribution, pypi, onboarding]
tldr: "Built a Claude Code skill that teaches Claude how to use ascli for end users. Bundled in package, distributed via install-skill command and onboard integration."
---

# v0.4.1 — Claude Code Skill

## What It Is

A Claude Code skill that makes Claude an expert ascli operator — able to transcribe URLs, configure providers, troubleshoot issues, and manage the tool on behalf of end users.

## What Was Built

### Skill files (source of truth: `src/anyscribecli/skill/`)

- **SKILL.md** — Core instructions: command decision tree, `--json --quiet` pattern for machine-readable output, provider selection guidance, safety rules (never expose API keys), pre-flight checks
- **references/commands.md** — Complete command reference with all flags, syntax, examples, JSON output format
- **references/providers.md** — Provider comparison table (pricing, languages, limits, when to recommend each)
- **references/troubleshooting.md** — Common errors and fixes, diagnostic-first approach
- **references/config.md** — All settings, file locations, workspace structure, transcript format

### Distribution mechanism

- **`ascli install-skill`** — New CLI command that copies bundled skill files to `~/.claude/skills/ascli/` using `importlib.resources`. Checks for Claude Code installation, handles already-installed (with `--force` override).
- **Onboard integration** — Step 11 in `ascli onboard` auto-detects `~/.claude/` and offers skill installation. Shows "installed" status if already present.
- **Package bundling** — Skill files live in `src/anyscribecli/skill/` as a Python subpackage (with `__init__.py`), included in the wheel automatically by hatchling.

## Design Decisions

**Why progressive disclosure?** SKILL.md stays under 200 lines with the core behavior. Reference files (commands, providers, troubleshooting, config) are loaded on-demand when Claude needs specifics. Follows Claude Code skill best practices (<500 lines for SKILL.md).

**Why `--json --quiet` as the default pattern?** When Claude runs ascli commands, it should parse structured output, not scrape human-readable text. The skill instructs Claude to always use these flags, then present a clean summary to the user.

**Why bundled in the package, not just in the repo?** `.claude/skills/` in the repo only helps developers who clone. PyPI users (`pip install anyscribecli`) need the skill files distributed inside the wheel, with a command to install them to the right location.

**Why `importlib.resources` instead of `__file__`?** `importlib.resources` is the modern way to access package data files in Python 3.10+. Works correctly regardless of where pip installs the package (virtualenv, system site-packages, etc.).

## Files Changed

| File | Change |
|------|--------|
| `src/anyscribecli/skill/` (new) | Skill files — SKILL.md + references/ |
| `src/anyscribecli/cli/skill_cmd.py` (new) | install-skill command + copy_skill_files() |
| `src/anyscribecli/cli/main.py` | Register install-skill command |
| `src/anyscribecli/config/paths.py` | Claude path constants + get_skill_source_dir() |
| `src/anyscribecli/cli/onboard.py` | Step 11 — Claude Code detection + skill install |
| `.gitignore` | Ignore `.claude/skills/` (installed, not committed) |
