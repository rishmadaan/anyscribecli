# Downloaders

**Last updated:** 2026-03-26 (v0.2.0)

## Available Downloaders

| Name | Tool | Auth Required | Status |
|------|------|---------------|--------|
| youtube | yt-dlp (subprocess) | No | Active |
| instagram | instaloader (Python API) | Yes (username/password) | Active (optional dep) |

## Downloader-Specific Notes

### YouTube (`downloaders/youtube.py`)
- Uses yt-dlp via subprocess (stable CLI, Python API is undocumented)
- Two-step: metadata via `--dump-json --no-download`, then download with `--extract-audio`
- Audio optimized for Whisper: 16kHz, mono, 64kbps mp3
- Handles: `youtube.com/watch`, `youtu.be/`, `youtube.com/shorts/`, `youtube.com/live/`

### Instagram (`downloaders/instagram.py`)
- Uses instaloader Python API (not subprocess) for session management
- Session caching pattern from Dropzone bundle: load session → test_login → fresh login if invalid → save
- Sessions stored at `~/.anyscribecli/sessions/instagram_session`
- Downloads video via instaloader, then extracts audio via ffmpeg
- Handles: `instagram.com/reel/`, `instagram.com/p/`
- Only video posts — image posts are rejected with a helpful error
- Requires `pip install instaloader` (optional dependency)
- Lazy-loaded in registry — won't crash if instaloader not installed

## Registry Pattern

`registry.py` uses lazy loading for optional downloaders:

```python
def _load_downloaders():
    downloaders = [YouTubeDownloader()]
    try:
        from .instagram import InstagramDownloader
        downloaders.append(InstagramDownloader())
    except ImportError:
        pass  # instaloader not installed
    return downloaders
```

## Adding a Downloader

1. Create `src/anyscribecli/downloaders/<name>.py`
2. Implement `AbstractDownloader` from `base.py`:
   - `can_handle(url)` returning bool
   - `download(url, output_dir)` returning `DownloadResult`
3. Add to `_load_downloaders()` in `registry.py` (lazy if optional dep)
4. Update this doc and `docs/user/commands.md` (Supported Platforms table)

## Audio Optimization

All downloaders should output audio optimized for Whisper:
- Format: mp3
- Sample rate: 16kHz
- Channels: mono
- Quality: 64kbps

These settings come from the AnyScribe web app where they proved optimal for Whisper's 12kHz processing threshold while keeping file sizes small.
