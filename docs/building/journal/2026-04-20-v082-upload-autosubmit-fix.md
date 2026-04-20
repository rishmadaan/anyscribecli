---
type: bugfix
date: 2026-04-20
version: 0.8.2
tags: [web-ui, ux, bugfix]
tldr: >
  Fix the Web UI "Browse local file" button auto-submitting the job the
  moment the upload finishes. The server-side path now populates the URL
  field so the user can open Options, tweak settings, then press
  Transcribe themselves — same contract as the URL text path.
---

# v0.8.2 — Fix local-file browse auto-submitting

## The bug

In the Web UI Transcribe page, clicking the folder-icon "Browse local
file" button kicked off transcription as soon as the upload finished.
There was no chance to open the options accordion, swap providers, or
change the output format first.

Source: `ui/src/components/URLInput.tsx` — the post-upload handler
called `onSubmit(path)` directly, which the page wires straight into
the job-submit flow.

## Why it happened

When the file-browse path was added (v0.7.4.6.1), the intent was
"uploading a file is the same as pasting a URL." The code took the
shortcut of submitting immediately on upload. That's fine for a
happy-path demo but breaks the mental model everywhere else in the UI:
URL text entry lets you review settings before hitting Transcribe, and
the local-file path should behave the same way.

## The fix

After a successful upload, populate the URL input with the
server-side path and focus it. The user stays in control of when to
submit — same contract as the URL text path.

```diff
 try {
   const { path } = await uploadFile(file);
-  // Submit directly with the server-side path
-  onSubmit(path);
+  // Populate the input with the server-side path. The user drives
+  // submission — they may want to tweak options before transcribing.
+  setUrl(path);
+  inputRef.current?.focus();
 } catch (err) {
```

No backend or API changes — the upload endpoint still returns
`{ path }` and the submission contract is unchanged. `detectPlatform`
already recognises absolute paths as `local`, so the platform badge
lights up immediately after upload.

## What a user sees now

1. Click folder icon → OS file picker opens
2. Pick a file → spinner while uploading
3. Upload completes → URL field shows the server-side path, "Local
   file" badge appears, cursor focused in the input
4. (Optional) open Options accordion, change provider / language /
   format
5. Click Transcribe (or press Enter) → job starts

## Surface parity

This restores the rule in `docs/building/architecture.md` →
"CLI ↔ Web UI: shared backend, asymmetric surfaces": each surface
controls its own UX, but the user intent model should be consistent
within a surface. Web UI has always been "fill the input, then press
the button" — the browse-file shortcut was the only place that broke
that pattern.

## Scope

- `ui/src/components/URLInput.tsx` — two-line change
- Rebuilt Web UI static bundle (`src/anyscribecli/web/static/`)
- Version bump: 0.8.1 → 0.8.2
