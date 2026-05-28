---
type: troubleshooting
tags: [release, publishing, audit, dependencies]
tldr: "Follow-up audit aligned package metadata to the documented 0.8.4 release, fixed a dev-only npm advisory, and re-ran the publish gates."
---

# Publish-Readiness Follow-up Audit

Goal: verify the release-hardening work from a clean audit pass and close any remaining publish blockers.

## Findings

- `BACKLOG.md` documented `0.8.4` as the current mainline release, but `pyproject.toml` and `src/anyscribecli/__init__.py` still reported `0.8.2`. A publish from this checkout would have produced and uploaded the wrong version.
- `npm audit --omit=dev` was clean, but the full frontend audit found a moderate dev-only advisory in `brace-expansion` under the TypeScript ESLint dependency tree.
- The PyPI publish workflow still lacked the frontend lint/build/static-bundle freshness gate, so a direct release tag could publish stale web assets even though normal CI would catch them on branch pushes and PRs.
- The globally installed Windows package was still `anyscribecli 0.8.1`; release verification needs to use the local editable environment or explicit build artifacts, not the ambient install.
- Frontend builds can fail if `ui/node_modules` is missing the current platform's optional Rolldown native binding. Running `npm install --include=optional` from `ui/` restored the Windows binding without changing app source.

## Changes Made

- Bumped package metadata to `0.8.4` in both required source-of-truth files.
- Updated the frontend lockfile from `brace-expansion 5.0.5` to `5.0.6`.
- Added frontend install, lint, build, and committed-static verification to the PyPI publish workflow.
- Rebuilt the web UI and normalized the generated static HTML after the build.

## Verification

- `python -m ruff check src tests` passed.
- `python -m pytest` passed: 129 passed, 1 skipped.
- `python -m build` produced both sdist and wheel for `0.8.4`.
- `npm run lint` passed.
- `npm run build` passed.
- `npm audit --omit=dev` reported 0 production vulnerabilities.
- `npm audit` reported 0 vulnerabilities after the lockfile fix.
