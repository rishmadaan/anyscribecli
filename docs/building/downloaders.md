# Downloaders

**Last updated:** 2026-04-29 (v0.8.3 — Instagram migrates to yt-dlp)

## Available Downloaders

| Name | Tool | Auth Required | Status |
|------|------|---------------|--------|
| youtube | yt-dlp (subprocess) | No | Active |
| instagram | yt-dlp (subprocess) | Optional (browser cookies) | Active |

## Downloader-Specific Notes

### YouTube (`downloaders/youtube.py`)
- Uses yt-dlp via subprocess (stable CLI, Python API is undocumented)
- Two-step: metadata via `--dump-json --no-download`, then download with `--extract-audio`
- Audio optimized for Whisper: 16kHz, mono, 64kbps mp3
- Handles: `youtube.com/watch`, `youtu.be/`, `youtube.com/shorts/`, `youtube.com/live/`

### Instagram (`downloaders/instagram.py`)
- Uses yt-dlp via subprocess (same pattern as YouTube)
- Two-step: metadata via `--dump-json --no-download`, then download with `--extract-audio`
- Audio optimized for Whisper: 16kHz, mono, 64kbps mp3
- Cookies are optional — many public reels work anonymously. For private reels or
  rate-limited cases, set `instagram.browser` (config) to one of `firefox`, `chrome`,
  `safari`, `brave`, `edge`, `chromium`, `vivaldi`, `opera`. yt-dlp pulls cookies from
  that browser's profile via `--cookies-from-browser`. No password is ever stored.
- The browser allowlist lives at `downloaders.instagram.SUPPORTED_BROWSERS`; the
  headless onboarding validator imports it for cross-surface consistency.
- Handles: `instagram.com/reel/`, `instagram.com/p/`, `instagram.com/<username>/reel/`, `instagram.com/<username>/p/`
- `_friendly_error()` translates yt-dlp stderr into actionable messages for the three
  most common failure modes: rate-limit/login required, private account, video unavailable.

> **Pre-0.8.3 history:** Instagram used the `instaloader` Python library with
> session caching that probed `test_login()` on every download. Instagram's
> anti-automation flagged the GraphQL pattern, producing
> `401 — "Please wait a few minutes"` errors even with valid sessions. The
> migration to yt-dlp eliminates the probe entirely. See
> `docs/building/journal/2026-04-29-instagram-yt-dlp-migration.md` for the
> decision record.

## Registry Pattern

`registry.py` directly imports all downloaders:

```python
from anyscribecli.downloaders.youtube import YouTubeDownloader
from anyscribecli.downloaders.instagram import InstagramDownloader

DOWNLOADERS = [YouTubeDownloader(), InstagramDownloader()]
```

For future optional downloaders, use lazy loading:
```python
try:
    from .newplatform import NewDownloader
    DOWNLOADERS.append(NewDownloader())
except ImportError:
    pass
```

## Adding a Downloader

1. Create `src/anyscribecli/downloaders/<name>.py`
2. Implement `AbstractDownloader` from `base.py`:
   - `can_handle(url)` returning bool
   - `download(url, output_dir)` returning `DownloadResult`
3. Add import to `registry.py` (direct if main dep, lazy if optional)
4. Update this doc and `docs/user/commands.md` (Supported Platforms table)

## Audio Optimization

All downloaders should output audio optimized for Whisper:
- Format: mp3
- Sample rate: 16kHz
- Channels: mono
- Quality: 64kbps

These settings come from the AnyScribe web app where they proved optimal for Whisper's 12kHz processing threshold while keeping file sizes small.
