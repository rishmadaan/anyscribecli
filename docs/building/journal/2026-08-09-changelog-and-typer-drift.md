---
type: decision
tags: [changelog, docs, ci, dependencies, drift]
tldr: "Added a user-facing CHANGELOG.md covering every release, hand-written rather than generated from BACKLOG.md's version table — a generator turns developer-facing table cells into mangled user prose and creates a second silent source of truth. Instead a ten-line `check_changelog()` gate in scripts/check-docs.py fails CI when the shipped version has no entry, so the changelog can only rot loudly. Also fixed `typer[all]>=0.9` → `typer>=0.12,<1`: typer no longer declares an `all` extra so every install printed a warning, and plain typer has bundled rich + shellingham since 0.12. Same latent-drift shape as the 0.16.3 mcp break, and found by that release's clean-install check."
---

# CHANGELOG.md, and why it isn't generated

**Date:** 2026-08-09 · Ships in v0.16.4

## The ask

"Since we are actively updating it and using it, we should have one." Fair —
the repo had no `CHANGELOG.md` and never had. `BACKLOG.md` carried a version
table and per-release sections, and GitHub Releases auto-generate notes from
commits, but there was nothing at the root where people actually look, and
nothing PyPI could link to.

## The decision: hand-written, machine-gated

The obvious move was a generator: parse `BACKLOG.md`'s version table, emit
`CHANGELOG.md`, wire it into the existing render-then-`git diff --exit-code`
pipeline that already keeps `landing/docs/*.html` honest. The repo has that
pattern; reusing it looked like the lazy answer.

Rejected, for two reasons:

1. **The content is wrong for the audience.** BACKLOG's cells are written for
   developers — `PROVIDER_KEY_ENV` drift, `_transcribe_chunked`, importorskip.
   Mechanically reprinting them under a user-facing heading produces something
   that looks like a changelog and helps nobody. A changelog entry answers "what
   changed for me, do I need to act", which is a different sentence than the one
   in the table.
2. **It creates a second silent source of truth.** Two files describing the same
   releases will drift; the question is only whether the drift is loud.

So: the file is written by hand, and a gate makes omission loud.

```python
def check_changelog() -> list[str]:
    version = real_version()
    text = (ROOT / "CHANGELOG.md").read_text()
    if re.search(rf"^## {re.escape(version)}(\s|$)", text, re.M):
        return []
    return [f"CHANGELOG.md: no '## {version}' entry for the version being released"]
```

Ten lines in `scripts/check-docs.py`, alongside the existing version-drift and
MCP-table gates. The version in `pyproject.toml` must have a matching heading or
CI is red. Because `release.sh` bumps the version in its own commit, the entry
has to be written *before* the release runs — the discipline is enforced at the
one moment anyone is paying attention.

**Watched it fail before trusting it**, per the standing rule that a test which
has never failed has not been shown to test anything:

```
gate, version present  : PASS (no problems)
gate, version missing  : ["CHANGELOG.md: no '## 0.99.0' entry for the version being released"]
```

Note the gate deliberately checks only the *current* version, and `CHANGELOG.md`
is deliberately **not** in `check_versions()`'s target list — a changelog is
supposed to be full of old version numbers, and scanning it would make the
version-drift gate fire on every historical entry.

Wired into all three checklists (`COMMIT_CHECKLIST.md`,
`ops/release-checklist.md`, `CLAUDE.md`) so the red build is an expected step,
not a mystery.

## The typer fix

`pyproject.toml` asked for `typer[all]>=0.9`. typer no longer declares an `all`
extra, so every install ended with:

```
WARNING: typer 0.27.1 does not provide the extra 'all'
```

Harmless — pip warns and installs the base package — but it is the same shape as
the bug v0.16.3 just fixed: a dependency declaration that quietly stopped
matching reality. Checked what `[all]` was actually buying us rather than
assuming:

| typer | base dependencies |
|---|---|
| 0.11.1 | `click`, `typing-extensions` |
| 0.12.0 | `typer-slim[standard]`, `typer-cli` |
| 0.15.0+ | `click`, `typing-extensions`, `shellingham`, `rich` |

Plain `typer` has bundled `rich` and `shellingham` since **0.12** — that is the
split where `typer-slim` became the minimal package and `typer` the batteries-
included one. So `typer[all]` buys nothing today, and `>=0.12` is the honest
floor rather than a guess.

Added `<1` for the same reason `mcp` got `<3`: 0.x minors are typer's
breaking-change lane, and an unbounded range on a dependency is a scheduled
outage on the maintainer's release day rather than a date we choose.

## Worth noting

This was found by the post-release clean-install verification at the end of
v0.16.3 — installing the published package into an empty virtualenv and reading
the output, rather than trusting a green CI badge. That step existed in
`ops/release-checklist.md` all along; running it properly surfaced a real, if
small, defect within minutes. Cheap check, keep doing it.
