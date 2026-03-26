---
summary: All configuration options, file locations, and how to change settings.
read_when:
  - You want to change your default provider or language
  - You need to find where config files are stored
  - You want to understand what each setting does
---

# Configuration

ascli stores all its data in a single directory: `~/.anyscribecli/`. Here's what's inside and how to change it.

## File Locations

| File | Path | What it stores |
|------|------|---------------|
| Config | `~/.anyscribecli/config.yaml` | Your preferences (provider, language, etc.) |
| API Keys | `~/.anyscribecli/.env` | Secret API keys (never committed to git) |
| Workspace | `~/.anyscribecli/workspace/` | Your Obsidian vault with all transcripts |
| Logs | `~/.anyscribecli/logs/` | Processing logs |
| Sessions | `~/.anyscribecli/sessions/` | Instagram login sessions (when enabled) |
| Temp | `~/.anyscribecli/tmp/` | Temporary downloads (auto-cleaned) |

> **Tip:** Run `ascli doctor` to see if all these exist and are healthy.

## config.yaml

This is your main settings file. The onboarding wizard creates it, but you can also edit it directly.

```yaml
# ~/.anyscribecli/config.yaml

provider: openai        # Which transcription service to use
language: auto           # Language for transcription
keep_media: false        # Whether to save audio files
output_format: clean     # How to format transcripts
instagram:               # Instagram credentials (for future use)
  username: ""
  password: ""
```

### Settings Explained

#### provider

Which API to use for transcription. Default: `openai`.

| Value | Service | What you need |
|-------|---------|---------------|
| `openai` | OpenAI Whisper API | `OPENAI_API_KEY` in .env |
| `openrouter` | OpenRouter (audio-via-chat models) | `OPENROUTER_API_KEY` |
| `elevenlabs` | ElevenLabs Scribe (99 languages) | `ELEVENLABS_API_KEY` |
| `sargam` | Sarvam AI (Indic languages) | `SARGAM_API_KEY` |
| `local` | faster-whisper (offline, free) | None needed |

> **Why multiple providers?** Different services handle different languages better. OpenAI Whisper is a good default, ElevenLabs has high accuracy across 99 languages, Sarvam excels at Indian languages, and the local provider is free and works offline.

> **Local provider** requires `pip install faster-whisper`. Models download automatically on first use. Works on CPU (slower) or GPU (fast with CUDA).

#### language

What language to expect in the audio. Default: `auto` (let the API auto-detect).

Use standard language codes: `en` (English), `es` (Spanish), `fr` (French), `hi` (Hindi), `ar` (Arabic), `zh` (Chinese), `ja` (Japanese), `ko` (Korean), etc.

> **When to set this explicitly:** Auto-detection works well for most videos, but if you're transcribing content in a specific language and getting wrong results, setting the language explicitly helps. You can also override per-video: `ascli transcribe <url> --language hi`

#### keep_media

Whether to save the downloaded audio file alongside the transcript. Default: `false`.

When `true`, audio files are saved to `~/.anyscribecli/workspace/media/YYYY-MM-DD/`. This uses more disk space but lets you re-listen or re-transcribe later without downloading again.

> **Disk space:** A 10-minute video at 64kbps mono is about 5MB of audio. If you transcribe a lot, this adds up.

#### output_format

How to format the transcript text. Default: `clean`.

| Value | Description |
|-------|-------------|
| `clean` | Plain text transcript, paragraphs only |
| `timestamped` | Transcript with `[mm:ss]` timestamps per segment (planned) |

## .env (API Keys)

Your API keys are stored separately from config for security:

```bash
# ~/.anyscribecli/.env
OPENAI_API_KEY=sk-proj-...
```

> **Important:** This file contains secrets. It's excluded from git by default. Never share it or commit it to a repository.

### Changing your API key

The easiest way is to re-run onboarding:

```bash
ascli onboard --force
```

Or edit the file directly:

```bash
nano ~/.anyscribecli/.env
```

## Workspace Structure

Your transcripts are organized in an Obsidian vault:

```
~/.anyscribecli/workspace/
├── .obsidian/                         # Obsidian app config (auto-generated)
├── _index.md                          # Master index — all transcripts, newest first
├── sources/
│   ├── youtube/
│   │   └── 2026-03-26/
│   │       └── video-title.md         # One file per transcript
│   └── instagram/
│       └── 2026-03-26/
│           └── reel-caption.md
├── daily/
│   └── 2026-03-26.md                  # What you transcribed today
└── media/                             # Audio files (only if keep_media=true)
    └── 2026-03-26/
        └── video-title.mp3
```

### How files are named

- **Date folders:** `YYYY-MM-DD` (e.g., `2026-03-26`)
- **File names:** A "slug" of the video title — lowercase, hyphens instead of spaces, max 60 characters
- **Collisions:** If two videos have the same slug on the same day, the second gets `-2` appended

### Transcript frontmatter

Each markdown file has YAML properties at the top that Obsidian can search and filter:

```yaml
---
source: https://youtube.com/watch?v=...    # Original URL
platform: youtube                           # Where it came from
title: "Video Title"                        # Video title
duration: "12:34"                           # Length of the video
language: en                                # Detected language
provider: openai                            # Which API transcribed it
date_processed: 2026-03-26                  # When you ran the transcription
word_count: 1500                            # Total words in transcript
reading_time: "8 min"                       # Estimated reading time
tags:                                       # For Obsidian tag filtering
  - transcript
  - youtube
tldr: "Video Title"                         # Quick summary
---
```

## Resetting Everything

To start fresh, delete the app directory and re-run onboarding:

```bash
rm -rf ~/.anyscribecli
ascli onboard
```

> **Warning:** This deletes all your transcripts, config, and API keys. Back up `~/.anyscribecli/workspace/` first if you want to keep your transcripts.
