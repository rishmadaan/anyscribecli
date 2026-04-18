---
summary: All configuration options, file locations, and how to change settings.
read_when:
  - You want to change your default provider or language
  - You need to find where config files are stored
  - You want to understand what each setting does
---

# Configuration

scribe uses two locations: a visible workspace for your transcripts and a hidden directory for app internals.

## File Locations

| File | Path | What it stores |
|------|------|---------------|
| **Workspace** | `~/anyscribe/` | Your Obsidian vault with all transcripts (configurable) |
| Config | `~/.anyscribecli/config.yaml` | Your preferences (provider, language, etc.) |
| API Keys | `~/.anyscribecli/.env` | Secret API keys (never committed to git) |
| Downloads | `~/.anyscribecli/downloads/` | Downloaded audio/video files |
| Logs | `~/.anyscribecli/logs/` | Processing logs |
| Sessions | `~/.anyscribecli/sessions/` | Instagram login sessions (when enabled) |
| Temp | `~/.anyscribecli/tmp/` | Temporary downloads (auto-cleaned) |

> **Upgrading from an older version?** If you have transcripts at `~/.anyscribecli/workspace/`, scribe will automatically move them to `~/anyscribe/` on your next transcription.

> **Tip:** Run `scribe doctor` to see if all these exist and are healthy.

## config.yaml

This is your main settings file. The onboarding wizard creates it, but you can also edit it directly.

```yaml
# ~/.anyscribecli/config.yaml

provider: openai          # Which transcription service to use
language: auto             # Language for transcription
keep_media: false          # Whether to save audio files
output_format: clean       # How to format transcripts
diarize: false             # Enable speaker diarization by default
prompt_download: never     # Ask to download video after transcription
local_file_media: skip     # What to do with local files after transcription
workspace_path: ""         # Empty = ~/anyscribe (default), or set a custom path
instagram:                 # Instagram credentials
  username: ""
```

> **Note:** Instagram password and API keys are stored in `~/.anyscribecli/.env`, not in config.yaml. Secrets never go in config.

### Settings Explained

#### provider

Which API to use for transcription. Default: `openai`.

| Value | Service | What you need |
|-------|---------|---------------|
| `openai` | OpenAI Whisper API | `OPENAI_API_KEY` in .env |
| `deepgram` | Deepgram Nova (diarization + hi-Latn) | `DEEPGRAM_API_KEY` |
| `openrouter` | OpenRouter (audio-via-chat models) | `OPENROUTER_API_KEY` |
| `elevenlabs` | ElevenLabs Scribe (92 languages) | `ELEVENLABS_API_KEY` |
| `sargam` | Sarvam AI (23 Indic languages + English) | `SARGAM_API_KEY` |
| `local` | faster-whisper (offline, free) | None needed |

> **Why multiple providers?** Different services handle different languages better. OpenAI Whisper is a good default, ElevenLabs has high accuracy across 90+ languages, Sarvam excels at Indian languages, and the local provider is free and works offline.

> **Local provider** requires `pip install faster-whisper`. Models download automatically on first use. Works on CPU (slower) or GPU (fast with CUDA).

#### language

What language to expect in the audio. Default: `auto` (let the API auto-detect).

Use standard language codes: `en` (English), `es` (Spanish), `fr` (French), `hi` (Hindi), `ar` (Arabic), `zh` (Chinese), `ja` (Japanese), `ko` (Korean), etc.

Each provider expects codes in a slightly different format — Whisper-family providers (`openai`, `local`) use ISO 639-1 like `en`, Deepgram uses BCP-47 like `en-US` or `hi-Latn`, and Sarvam uses BCP-47 with `-IN` suffixes like `hi-IN`. If you're unsure, the web UI (`scribe ui`) shows a per-provider dropdown of every supported code on the Transcribe page Options panel.

> **When to set this explicitly:** Auto-detection works well for most videos, but if you're transcribing content in a specific language and getting wrong results, setting the language explicitly helps. You can also override per-video: `scribe transcribe <url> --language hi`

#### keep_media

Whether to save the downloaded audio file alongside the transcript. Default: `false`.

When `true`, audio files are saved to `~/.anyscribecli/downloads/audio/<platform>/` (separate from the Obsidian workspace). This uses more disk space but lets you re-listen or re-transcribe later without downloading again.

> **Disk space:** A 10-minute video at 64kbps mono is about 5MB of audio. If you transcribe a lot, this adds up.

#### output_format

How to format the transcript text. Default: `clean`.

| Value | Description |
|-------|-------------|
| `clean` | Plain text transcript, paragraphs only |
| `timestamped` | Transcript with `[mm:ss]` timestamps per segment |
| `diarized` | Speaker-grouped turns with timestamps (for multi-speaker audio) |

> **Tip:** When you use `--diarize`, the output format is automatically set to `diarized` unless you've explicitly set it to `timestamped`.

> **Web UI label:** The `diarized` value is shown as `with-speaker-labels` in `scribe ui`. The wire value (what gets stored in `config.yaml`) is unchanged — picking either spelling produces the same output.

#### diarize

Whether to enable speaker diarization (identifying who said what) by default. Default: `false`.

When enabled, providers that support diarization (OpenAI, Deepgram, Sarvam) will label each speaker in the transcript. You can also enable per-transcription with `--diarize` without changing this default.

> **Auto-routing:** When `--diarize` is used (or this is set to `true`) without an explicit `--provider`, scribe automatically switches to Deepgram if a Deepgram API key is configured. Deepgram handles large files natively and produces the most consistent speaker labels. Override with `--provider openai` if needed.

> **Automatic speaker detection:** The number of speakers is detected automatically from the audio — you never need to specify how many speakers are in the recording. Deepgram analyzes voice characteristics (pitch, tone, cadence) to distinguish speakers.

> **Language tip:** For mostly-English meetings, auto-detect works well. For Hindi or Hinglish (Hindi-English mix), add `--language hi-Latn` for romanized Latin script output. See [Providers](providers.md) for the full language guide.

> **When to enable:** If you primarily transcribe meetings, interviews, or podcasts with multiple speakers. Leave off for single-speaker content like YouTube videos.

#### prompt_download

Whether to offer downloading the video/audio file after each transcription. Default: `never`.

| Value | Description |
|-------|-------------|
| `never` | Don't ask — just transcribe (default) |
| `ask` | Ask after each transcription if you want the video/audio too |
| `always` | Always download the full video after transcription |

> **Tip:** You can always download manually with `scribe download "<url>"` regardless of this setting.

#### local_file_media

What to do with the original file when transcribing local audio/video files. Default: `skip`.

| Value | Description |
|-------|-------------|
| `skip` | Leave the original file where it is (default) |
| `copy` | Copy to `~/.anyscribecli/downloads/audio/local/` for organization |
| `move` | Move to the downloads directory (removes the original) |
| `ask` | Ask each time what to do |

> **Why skip by default?** Unlike URL downloads where audio is temporary, local files already exist on your disk. Copying them wastes space unless you want everything organized in one place.

## .env (API Keys and Secrets)

API keys and passwords are stored separately from config for security:

```bash
# ~/.anyscribecli/.env
OPENAI_API_KEY=sk-proj-...
DEEPGRAM_API_KEY=...
INSTAGRAM_PASSWORD=your-password
# ELEVENLABS_API_KEY=xi-...
# OPENROUTER_API_KEY=sk-or-...
# SARGAM_API_KEY=...
```

> **Important:** This file contains secrets. It's excluded from git by default. Never share it or commit it to a repository.

### Changing your API key

The easiest way is to use `scribe config set`:

```bash
scribe config set openai_api_key sk-proj-...
scribe config set deepgram_api_key YOUR_KEY
scribe config set elevenlabs_api_key xi-...
scribe config set sargam_api_key YOUR_KEY
scribe config set openrouter_api_key sk-or-...
```

These are stored in `~/.anyscribecli/.env` automatically.

Or re-run onboarding:

```bash
scribe onboard --force
```

This shows your current settings (API keys masked) and lets you change only what you need — no need to re-enter everything.

Or edit the file directly:

```bash
nano ~/.anyscribecli/.env
```

## Workspace Structure

Your transcripts live in the workspace (pure markdown, no binaries). Downloaded files are stored separately in the app directory.

```
~/anyscribe/                               # Obsidian vault (configurable)
├── .obsidian/                             # Obsidian app config
├── _index.md                              # Master index — newest first
├── sources/
│   ├── youtube/                           # YouTube transcripts
│   ├── instagram/                         # Instagram transcripts
│   └── local/                             # Local file transcripts
└── daily/YYYY-MM-DD.md                   # Daily processing log

~/.anyscribecli/                           # App internals (hidden)
├── downloads/                             # Downloads (separate from vault)
│   ├── audio/<platform>/                  # Audio files (if keep_media=true)
│   └── video/<platform>/                  # Video files (scribe download)
├── sessions/                              # Login sessions
└── logs/                                  # Processing logs
```

> **Why are downloads separate?** Keeping binaries out of the Obsidian vault means the vault stays lightweight and fast — even with hundreds of transcripts.

#### workspace_path

Where to store your transcript workspace. Default: `~/anyscribe/` (when set to empty string or omitted).

Set a custom path to use an existing Obsidian vault or a different location:
```bash
scribe config set workspace_path ~/Documents/transcripts
```

> **Tip:** Leave this empty to use the default `~/anyscribe/`. The workspace is visible in Finder/file managers — no need to navigate to hidden folders.

### How files are named

- **File names:** A "slug" of the video title — lowercase, hyphens instead of spaces, max 60 characters
- **Collisions:** If two videos have the same slug, the second gets `-2` appended

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
rm -rf ~/.anyscribecli ~/anyscribe
scribe onboard
```

> **Warning:** This deletes your config, API keys, and transcripts. Back up `~/anyscribe/` first if you want to keep your transcripts. If you used a custom workspace path, back up that location instead.
