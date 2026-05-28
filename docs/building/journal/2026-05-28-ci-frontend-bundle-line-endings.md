---
type: troubleshooting
tags: [release, ci, frontend, static-bundle]
tldr: "CI failed because the committed Vite JS hash came from a Windows line-ending build; the Linux runner produced a different hashed bundle, so static assets now use LF-normalized attributes."
---

# CI Frontend Bundle Line Endings

## Context

The v0.8.4 release hardening commit added a CI job that rebuilds the React frontend and verifies the committed static bundle is current. The first push failed in the frontend job during the final static bundle check.

## Root cause

The committed static bundle had been generated from a Windows checkout with CRLF-normalized frontend inputs. GitHub Actions checks out the repository on Ubuntu with LF inputs, so Vite produced a different JS content hash:

- committed bundle: `index-C0_w4koc.js`
- CI/Linux bundle: `index-Hn358_8g.js`

The application code was not failing. The release gate correctly caught that the committed generated assets did not match the Linux build environment used for publishing checks.

## Fix

Rebuilt the frontend from a clean Linux checkout and committed the Linux-generated static bundle. Added `.gitattributes` rules for the frontend source and committed web static text assets so future checkouts use LF consistently across Windows, macOS, and Linux.

## Follow-up note

If this class of issue returns, consider making Vite output stable non-hashed filenames for the embedded local UI, or move generated static verification into a script that reports untracked generated files explicitly.
