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

provider: openai          # Explicit provider (or let `quality` pick one)
quality: balanced          # accuracy | balanced | cost | free — picks a provider
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
| `elevenlabs` | ElevenLabs Scribe v2 (highest accuracy, 90+ languages) | `ELEVENLABS_API_KEY` |
| `sargam` | Sarvam AI (23 Indic languages + English) | `SARGAM_API_KEY` |
| `groq` | Groq (fast, cheap Whisper large-v3-turbo) | `GROQ_API_KEY` |
| `local` | faster-whisper (offline, free) | None needed |

> **Tip:** Most people should use the `quality` setting (below) instead of
> picking a provider directly — it chooses the right provider for you.

> **Why multiple providers?** Different services handle different languages better. OpenAI Whisper is a good default, ElevenLabs has high accuracy across 90+ languages, Sarvam excels at Indian languages, and the local provider is free and works offline.

> **Local provider** requires `pip install faster-whisper`. Models download automatically on first use. Works on CPU (slower) or GPU (fast with CUDA).

#### quality

Pick **what you want** — higher accuracy or lower cost — and scribe chooses the
provider for you. Default: `balanced` (Deepgram). This is the easiest way to use
scribe; you rarely need to touch `provider` directly.

| Value | Picks | Best for |
|-------|-------|----------|
| `balanced` (default) | Deepgram `nova-3` | Strong accuracy + native speaker labels |
| `accuracy` | ElevenLabs `scribe_v2` | Highest accuracy, primarily-English |
| `cost` | Groq `whisper-large-v3-turbo` | Cheapest + fastest cloud (~$0.04/hr) |
| `free` | Local faster-whisper | Offline, $0 (needs `scribe local setup`) |

Change it with `scribe config set quality cost`, per-run with
`scribe transcribe <url> --quality cost`, or from the picker in the Web UI.

> **How it works:** the tier picks a provider. If you pass `--provider` (or pick
> one in the Web UI), that wins. If the tier's provider has no API key set,
> scribe falls back to your configured `provider` so it still runs.

> **Need a key:** each tier needs that provider's key in `.env` —
> `accuracy` needs `ELEVENLABS_API_KEY`, `cost` needs `GROQ_API_KEY`, etc.
> `free` needs no key.

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

#### local_model

Which Whisper model the `local` provider uses when transcribing. Default: `base`.

| Value | Download | RAM | Quality |
|-------|----------|-----|---------|
| `tiny` | ~75 MB | ~400 MB | lowest |
| `base` (default) | ~145 MB | ~600 MB | good for most |
| `small` | ~480 MB | ~1.2 GB | noticeably better |
| `medium` | ~1.5 GB | ~2.5 GB | near-large for many languages |
| `large-v3` | ~3 GB | ~5 GB | highest |

Change it with `scribe config set local_model small` or from the default-model dropdown inside the Local provider panel in the Web UI. You can only select a model that's been cached — pull others with `scribe model pull <size>`. A one-off override is available via `ASCLI_LOCAL_MODEL=medium scribe "<url>"`.

> **Not set until setup.** This field has no effect until you run `scribe local setup --model <size>` (or the equivalent Web UI button). The field is still present in `config.yaml` with the default value of `base`.

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
# GROQ_API_KEY=gsk-...
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
scribe config set groq_api_key gsk-...
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

## What you can change vs what's fixed

Most things you'd want to adjust are settings you can change anytime. A few
things are **fixed in the code** — they're tuned defaults that keep transcription
reliable, and changing them means editing scribe's source and reinstalling.

```
   things you set (knobs)                things baked in (constants)
   ┌──────────────────────────┐         ┌──────────────────────────────┐
   │ config.yaml settings     │         │ audio quality (16kHz/mono)   │
   │ .env API keys + secrets  │         │ how big files get split up   │
   │ --flags on commands      │         │ which model each provider uses│
   │ the Web UI settings page │         │ where app files live         │
   └──────────────────────────┘         │ Web UI is localhost-only     │
   change anytime, no restart           └──────────────────────────────┘
                                         changing these needs a code edit
```

**You can change anytime** (this whole page): your provider, language, output
format, diarization, whether media is kept, your workspace location, the local
model, and all your API keys.

**Fixed in the code** (and why):

| What's fixed | Current value | Why it's not a setting |
|--------------|---------------|------------------------|
| Audio quality | 16 kHz, mono, 64 kbps mp3 | Tuned for the best transcription accuracy per megabyte. Higher quality wouldn't improve the text. |
| File-splitting limits | Split if over 25 MB or 30 min, into 18-min pieces | Driven by the transcription APIs' own upload and timeout limits, not your preference. |
| The model each provider uses | e.g. OpenAI uses `whisper-1`, ElevenLabs uses `scribe_v2` | Pinned per provider so results stay consistent. Picking a *provider* (or `quality` tier) is your choice; picking the exact model within a provider isn't. |
| App folder location | `~/.anyscribecli` | The fixed home for config, logs, and downloads. Your transcripts' location (`workspace_path`) *is* configurable. |
| Web UI address | `127.0.0.1` (your machine only) | The Web UI has no password, so it only listens to your own computer. The port is changeable with `scribe ui --port 9000`. |

> **Want one of these to be a real setting?** These are deliberate defaults, not
> oversights — see the developer note in
> [docs/building/architecture.md](../building/architecture.md) for which ones are
> candidates to become configurable. If you have a concrete need (say, a custom
> audio bitrate), that's a reasonable feature request.

## Resetting Everything

To start fresh, delete the app directory and re-run onboarding:

```bash
rm -rf ~/.anyscribecli ~/anyscribe
scribe onboard
```

> **Warning:** This deletes your config, API keys, and transcripts. Back up `~/anyscribe/` first if you want to keep your transcripts. If you used a custom workspace path, back up that location instead.
