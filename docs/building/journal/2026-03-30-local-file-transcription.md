---
type: feature
tags: [downloader, local-file, transcription]
tldr: Added local file transcription — users can now transcribe mp3, mp4, m4a, wav, opus, ogg, flac, webm, aac, wma files directly without a URL.
---

# Local File Transcription Support

## Context

Users wanted to transcribe local audio/video files, not just YouTube/Instagram URLs. The sibling project (anyscribe web app) already had this feature in production, confirming the approach: convert to Whisper-optimized mp3 (16kHz mono 64kbps) via ffmpeg, then feed to any provider.

## Decision

Implemented as a new `LocalFileDownloader` that fits into the existing downloader abstraction. No provider changes needed — providers already accept file paths.

## Implementation

1. **`downloaders/local_file.py`** — new `LocalFileDownloader` implementing `AbstractDownloader`
   - `can_handle()` checks if input is a local file with supported extension (not a URL)
   - `download()` converts to Whisper-optimized mp3 via ffmpeg, extracts duration
   - Returns `DownloadResult` with `platform="local"`

2. **`downloaders/registry.py`** — registered `LocalFileDownloader` first in `DOWNLOADERS` list (before URL matchers)

3. **`cli/transcribe.py`** — `_validate_url()` → `_validate_input()`, accepts file paths, updated help text

4. **`vault/writer.py`** — handles `platform="local"` with file path display instead of clickable link

5. **Batch support** — works automatically since batch just passes lines to the orchestrator

## Supported Formats

mp3, mp4, m4a, wav, opus, ogg, flac, webm, aac, wma — anything ffmpeg can handle.

## Usage

```bash
ascli transcribe /path/to/podcast.mp3
ascli transcribe ~/recordings/meeting.m4a
ascli transcribe ./interview.opus
```

Output goes to `sources/local/YYYY-MM-DD/<slug>.md` in the vault.
