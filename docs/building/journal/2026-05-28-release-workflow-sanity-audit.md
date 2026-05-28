---
type: troubleshooting
tags: [release, ci, publishing, audit]
tldr: "Release audit found stale release docs, a macOS-only version bump in release.sh, no pre-publish CI, and a stray v0.8.3 tag on an unmerged branch."
---

# Release Workflow Sanity Audit

Goal: harden the path to a stable anyscribecli release.

## Findings

- `scripts/release.sh` used BSD `sed -i ''`, which works on macOS but fails on Linux release machines.
- The release script checked only local tags before creating a new tag; it now also checks `origin`.
- There was no CI workflow to run lint, tests, package build, or frontend bundle freshness checks before a release tag.
- The PyPI publish workflow built the package but did not run lint/tests before upload.
- Release docs still used the old `ascli` command in several operational examples even though `scribe` is now the primary command.
- Local verification can be misleading if the checkout is not installed editable: plain `python -m anyscribecli --version` may resolve an older installed package instead of `src/`.
- A `v0.8.3` tag exists on `origin/instagram-yt-dlp-migration`, while `main` was still at `0.8.2` during the initial audit. Do not attempt to release `0.8.3` from `main`; use `0.8.4+` or reconcile/delete the tag intentionally.
- Running the full suite on Windows exposed a real no-op file lock fallback and preflight ordering issue.
- Frontend lint had not been exercised locally; React Compiler lint surfaced synchronous effect state updates and a reconnect callback self-reference.

## Changes Made

- Rewrote `scripts/release.sh` version editing in Python for GNU/Linux and macOS portability.
- Added `.github/workflows/ci.yml` with Python lint/test/build and frontend lint/build/static-bundle checks.
- Added lint/test gates to `.github/workflows/publish.yml` before package upload.
- Refreshed release/publishing docs to prefer `scribe`.
- Updated the architecture note and backlog to reflect the new CI coverage.
- Fixed Windows file locking in `core/fileutil.py`.
- Reordered local-file validation ahead of disk-space checks in `core/preflight.py` and added a temp-dir fallback when home resolution is unavailable.
- Isolated headless onboarding tests from the real user config path.
- Fixed frontend lint findings and rebuilt the committed static bundle.

## Verification

- `ruff check src tests` passed.
- `pytest` passed: 129 passed, 1 skipped.
- `python -m build` produced both sdist and wheel for 0.8.4 after the follow-up metadata alignment.
- `npm run lint` passed.
- `npm run build` passed and rebuilt `src/anyscribecli/web/static/`.
- `npm audit --omit=dev` reported 0 production vulnerabilities.
