---
type: decision
date: 2026-04-29
version: 0.8.3
tags: [instagram, downloader, yt-dlp, instaloader, migration]
tldr: >
  Replaced instaloader with yt-dlp for Instagram. No more password on disk;
  rate-limit-prone test_login() probe gone.
---

# Instagram → yt-dlp migration (0.8.3)

## Problem

`instaloader` calls authenticated GraphQL endpoints (`test_login()`,
`Post.from_shortcode`) on every download. Instagram's anti-automation
heuristic flags this pattern, especially under burst usage from
`scribe ui`. Users hit `401 Unauthorized — "Please wait a few minutes
before you try again"` even with valid sessions.

The library also forced users to put `INSTAGRAM_PASSWORD` in `.env`,
which was poor hygiene for a privacy-first local app. The Dropzone
"Instagram Downloader" bundle uses the same library with the same
flow — it works only because of light, manual, drag-by-drag usage; not
because the library is robust.

## Decision

Drop `instaloader`. Use `yt-dlp` as the sole Instagram downloader,
called via subprocess (matching the existing `YouTubeDownloader`
pattern). For private/throttled cases, read cookies from the user's
browser via `--cookies-from-browser`. No password ever stored.

## Why yt-dlp

- Nightly extractor fixes (instaloader is quarterly).
- Already a project dependency for YouTube — no new tool.
- Browser-cookie auth uses real session, doesn't trigger heuristics.
- Higher quality ceiling (1080p vs instaloader's 720p).
- Public reels often work with no auth at all.

## Alternatives considered

- **gallery-dl**: image-oriented; its own ecosystem routes reels to
  yt-dlp anyway.
- **instagrapi**: documented account-ban risk; requires user/pass.
- **Playwright/Selenium**: heavy install footprint; reinventing yt-dlp.

## Migration

- Config schema: `instagram.username` (config.yaml) + `INSTAGRAM_PASSWORD`
  (.env) → `instagram.browser` (config.yaml). Old keys silently discarded
  on load; users see a deprecation notice during re-onboard.
- TUI / `--yes` / Web UI: shared `run_headless_onboard()` rewritten;
  `instagram_username` + `instagram_password` parameters → `instagram_browser`.
- Backend validates browser name against `SUPPORTED_BROWSERS` (defined in
  `downloaders/instagram.py`) — same guard for all surfaces.
- Skill + user docs rewritten end-to-end.

## Source URLs (verified 2026-04-29)

- yt-dlp issue tracker: https://github.com/yt-dlp/yt-dlp/issues/7165 (canonical IG login issue)
- instaloader rate-limit reports: issues #2426, #2501, #2511, #2532, #2568, #2682
- instaloader ban warning: #2555
