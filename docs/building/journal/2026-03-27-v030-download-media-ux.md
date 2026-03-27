---
type: project-note
tags: [v0.3.0, download, media, ux, beaupy, url-validation, security]
tldr: "v0.3.0 — download command, media restructured outside vault, arrow-key selectors, URL validation, Instagram password to .env"
---

# v0.3.0 — Download, Media Restructure, UX Polish

## Context

After v0.2.0 was feature-complete (all providers, Instagram, batch, config), focus shifted to usability, structure, and real-world testing. End-to-end tests on YouTube and Instagram revealed UX issues (unintuitive prompts, zsh URL mangling) and architectural issues (media bloating the Obsidian vault, Instagram password in plaintext config).

## What Changed

### Download command (`ascli download`)
- Download video or audio only — no transcription
- `--video` (default) and `--audio-only` flags
- Supports `--clipboard`, `--json`, interactive prompt
- Uses yt-dlp for both YouTube and Instagram video downloads
- Saves to `~/.anyscribecli/media/video/` or `media/audio/`

### Media restructure
- **Before:** Media inside workspace at `workspace/media/YYYY-MM-DD/` (flat, no platform split)
- **After:** Media outside workspace at `media/audio/<platform>/YYYY-MM-DD/` and `media/video/<platform>/YYYY-MM-DD/`
- Workspace stays pure markdown — Obsidian vault is lightweight
- Audio (from transcription) and video (from download) are separated

### Security: Instagram password moved to .env
- **Before:** Password stored in `config.yaml` alongside non-sensitive settings
- **After:** Password stored in `.env` with other secrets
- Config.yaml is safe to share; .env never is

### Onboarding UX overhaul
- Replaced text-entry prompts with arrow-key selectors (beaupy library)
- Provider selection: Rich table → arrow keys → Enter
- Language selection: common languages + "other" option
- Yes/no prompts use highlight selectors
- Added `prompt_download` config step (never/ask/always)
- Clear instruction text before every prompt

### URL validation
- Detects zsh-mangled URLs (truncated `?v=` part) with actionable error message
- Interactive prompt fallback when no URL argument given
- `--clipboard` flag reads URL from system clipboard (pbpaste/xclip)
- Basic URL validation (must start with http)

### Dependency changes
- `instaloader` promoted from optional to main dependency
- `beaupy` added for interactive CLI selectors
- `faster-whisper` remains optional (local provider only)

## Decisions

- **Media outside vault:** Obsidian vault should be fast and git-friendly. Binary media bloats it. Separate directories keep concerns clean.
- **beaupy over InquirerPy:** beaupy is built on Rich (which we already depend on), lightweight, cross-platform. InquirerPy pulls in prompt_toolkit.
- **Three URL input methods:** quotes (primary, for agents), interactive prompt (for humans who forget quotes), clipboard (convenience). All three end up at the same code path.
