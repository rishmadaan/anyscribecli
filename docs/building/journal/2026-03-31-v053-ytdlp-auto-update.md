---
type: project-note
tags: [yt-dlp, dependency, auto-update, youtube, reliability]
tldr: "v0.5.3 — Auto-detect and update stale yt-dlp (>60 days old) before any download. Prevents 403 errors from YouTube streaming format changes (SABR, etc.)."
---

# v0.5.3: Auto-Update Stale yt-dlp

## What Changed

Added `ensure_ytdlp_current()` to `core/deps.py`. Before any yt-dlp subprocess call, it parses the date-based version string (e.g. `yt-dlp 2025.10.22`), checks if it's older than 60 days, and auto-updates via `pip install --upgrade yt-dlp` if stale.

Wired into two call sites:
- `YouTubeDownloader.download()` — audio download for transcription
- `_download_video()` in `cli/download.py` — video download

## Why

YouTube frequently changes streaming formats. In March 2026, they began forcing SABR streaming for web clients (yt-dlp/yt-dlp#12482), breaking older yt-dlp versions with HTTP 403 errors. Users with yt-dlp installed months ago would see:

```
ERROR: unable to download video data: HTTP Error 403: Forbidden
```

This is a recurring pattern — YouTube changes something, yt-dlp ships a fix within days, but users who installed via pip don't get the update automatically.

## Why Not instaloader Too?

Considered auto-updating instaloader as well, but decided against it:

- **instaloader** uses semantic versioning (4.15.1), is imported as a Python library, and updates when anyscribecli itself is updated via pip. Instagram's API changes less aggressively than YouTube's.
- **yt-dlp** uses date-based versioning (YYYY.MM.DD), is called as a subprocess binary, and YouTube changes streaming formats weekly. It goes stale fast and independently of anyscribecli updates.

## Implementation Details

- `_parse_ytdlp_version_date()` — regex extracts YYYY.MM.DD from version string, returns datetime
- `YTDLP_MAX_AGE_DAYS = 60` — configurable threshold constant
- Uses `sys.executable -m pip install --upgrade yt-dlp` to update in the correct Python environment
- Graceful failure: prints manual update instruction if pip update fails or times out (120s)
- Lazy import in both call sites to avoid circular dependency

## Chat Summary

1. User hit a 403 error transcribing a YouTube video — yt-dlp 2025.10.22 was 160 days old
2. Identified the root cause: YouTube SABR streaming changes breaking old extractors
3. User wanted this as an auto-fix in the tool itself (v0.5.3 patch release)
4. Discussed whether instaloader needs the same treatment — concluded no, different update dynamics
5. Implemented `ensure_ytdlp_current()` with 60-day threshold and graceful fallback
6. Wired into both yt-dlp call sites (youtube downloader + video download command)

## Links

- https://github.com/yt-dlp/yt-dlp/issues/12482 — YouTube SABR streaming issue
