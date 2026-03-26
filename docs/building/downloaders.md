# Downloaders

**Last updated:** 2026-03-26

## Available Downloaders

| Name | Tool | Auth Required | Status |
|------|------|---------------|--------|
| youtube | yt-dlp (subprocess) | No | Active |
| instagram | instaloader (Python API) | Yes (username/password) | Planned |

## Adding a Downloader

1. Create `src/anyscribecli/downloaders/<name>.py`
2. Implement `AbstractDownloader` from `base.py`:
   - `can_handle(url)` returning bool
   - `download(url, output_dir)` returning `DownloadResult`
3. Add instance to `DOWNLOADERS` list in `registry.py`
4. Update this doc

## Audio Optimization

All downloaders should output audio optimized for Whisper:
- Format: mp3
- Sample rate: 16kHz
- Channels: mono
- Quality: 64kbps

These settings come from the AnyScribe web app where they proved optimal for Whisper's 12kHz processing threshold while keeping file sizes small.

## URL Detection

`registry.py` matches URLs with regex patterns:
- YouTube: `youtube.com/watch`, `youtu.be/`, `youtube.com/shorts/`
- Instagram: `instagram.com/reel/`, `instagram.com/p/`
