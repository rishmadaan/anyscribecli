# anyscribecli

**Download. Transcribe. Markdown.** A CLI tool that turns YouTube videos, Instagram reels, and local audio/video files into structured, searchable markdown — browsable in Obsidian.

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![PyPI](https://img.shields.io/pypi/v/anyscribecli.svg)](https://pypi.org/project/anyscribecli/)

---

## What it does

```
URL or local file → Download/convert audio → Transcribe → Formatted Markdown → Obsidian Vault
```

- **5 transcription providers** — OpenAI Whisper, ElevenLabs, OpenRouter, Sarvam AI, Local (offline)
- **3 input sources** — YouTube, Instagram (reels + posts), local files (mp3, mp4, m4a, wav, opus, ogg, flac, webm)
- **Obsidian-native output** — YAML frontmatter, word count, reading time, tags
- **Master index + daily logs** — browse everything in Obsidian
- **Download-only mode** — grab video or audio without transcribing
- **Batch processing** — transcribe a list of URLs from a file
- **`--json` on main commands** — for scripting and AI agent integration
- **Arrow-key onboarding wizard** — interactive setup, installs missing dependencies

## Quick Start

### Install

```bash
# From PyPI (recommended)
pip install anyscribecli

# Or use the install script (checks and installs dependencies too)
curl -fsSL https://raw.githubusercontent.com/rishmadaan/anyscribecli/main/install.sh | bash

# Or clone for development
git clone https://github.com/rishmadaan/anyscribecli.git
cd anyscribecli && pip install -e .
```

### Set up

```bash
ascli onboard
```

Interactive wizard with arrow-key selectors:
1. Checks system dependencies (yt-dlp, ffmpeg) — installs missing ones
2. Choose provider from 5 options (arrow keys)
3. Enter API key
4. Configure Instagram credentials (optional)
5. Choose language, media storage, post-transcription download behavior
6. Creates your Obsidian workspace

### Transcribe

```bash
# From a URL
ascli transcribe "https://www.youtube.com/watch?v=VIDEO_ID"

# From a local file
ascli transcribe /path/to/podcast.mp3
```

> **Always wrap URLs in quotes** — shells like zsh break URLs with `?` in them. Or just run `ascli transcribe` and paste when prompted. Local file paths don't need quotes.

### Download (no transcription)

```bash
ascli download "https://www.youtube.com/watch?v=VIDEO_ID"            # video
ascli download "https://www.youtube.com/watch?v=VIDEO_ID" --audio-only  # audio
```

## Commands

| Command | Description |
|---------|-------------|
| `ascli onboard` | Interactive setup wizard |
| `ascli transcribe "<url or file>"` | Transcribe a video or local file to markdown |
| `ascli download "<url>"` | Download video or audio only |
| `ascli batch <file>` | Batch transcribe URLs or file paths from a file |
| `ascli config show/set/path` | View and change settings |
| `ascli providers list/test` | Manage transcription providers |
| `ascli install-skill` | Install Claude Code skill |
| `ascli update` | Update to the latest version |
| `ascli doctor` | Check system health |

### Transcribe options

```bash
ascli transcribe "<url>"
  --provider, -p <name>    # Override provider (openai, elevenlabs, local, etc.)
  --language, -l <code>    # Language code (default: auto-detect)
  --json, -j               # JSON output for scripting/AI agents
  --keep-media             # Keep the downloaded audio file
  --clipboard, -c          # Read URL from clipboard
  --quiet, -q              # Suppress progress output
```

Provide a URL, file path, or use interactive mode:
```bash
ascli transcribe "https://..."     # quoted URL (primary)
ascli transcribe /path/to/file.mp3 # local audio/video file
ascli transcribe                    # interactive prompt (no quoting needed)
ascli transcribe --clipboard        # read URL from system clipboard
```

### Download options

```bash
ascli download "<url>"
  --video / --audio-only     # Video (default) or audio only
  --json, -j                 # JSON output
  --quiet, -q                # Suppress progress
  --clipboard, -c            # Read URL from clipboard
```

### Batch options

```bash
ascli batch <file>
  --provider, -p <name>      # Override provider
  --language, -l <code>      # Override language
  --json, -j                 # JSON output
  --keep-media               # Keep audio files
  --quiet, -q                # Suppress progress
  --stop-on-error            # Stop at first failure
```

### JSON output

```bash
ascli transcribe "https://youtube.com/watch?v=abc123" --json
```

```json
{
  "success": true,
  "file": "~/anyscribe/sources/youtube/2026-03-27/video-title.md",
  "title": "Video Title",
  "platform": "youtube",
  "duration": "12:34",
  "language": "en",
  "word_count": 1500,
  "provider": "openai"
}
```

## Prerequisites

The onboarding wizard checks for these and offers to install them:

| Dependency | Required | Install |
|------------|----------|---------|
| Python 3.10+ | Yes | [python.org](https://www.python.org/downloads/) |
| yt-dlp | Yes | `brew install yt-dlp` or `pip install yt-dlp` |
| ffmpeg | Yes | `brew install ffmpeg` or [ffmpeg.org](https://ffmpeg.org/) |
| API key | Yes (for cloud providers) | See [Provider Guide](docs/user/providers.md) |

## Directory structure

```
~/anyscribe/                              # Obsidian vault (configurable)
├── _index.md                             # Master index (newest first)
├── sources/
│   ├── youtube/YYYY-MM-DD/<slug>.md
│   ├── instagram/YYYY-MM-DD/<slug>.md
│   └── local/YYYY-MM-DD/<slug>.md
└── daily/YYYY-MM-DD.md

~/.anyscribecli/                          # App internals (hidden)
├── config.yaml                           # Settings (no secrets)
├── .env                                  # API keys + passwords
├── downloads/                            # Downloads (separate from vault)
│   ├── audio/<platform>/YYYY-MM-DD/      # Kept audio (if keep_media=true)
│   └── video/<platform>/YYYY-MM-DD/      # Downloaded videos
├── sessions/                             # Login sessions
└── logs/                                 # Processing logs
```

> **Workspace is visible and configurable** — transcripts default to `~/anyscribe/` (no hidden dot-dir). Change it with `ascli config set workspace_path /your/path`. Downloads stay separate to keep the vault lightweight.

## Providers

| Provider | Best for | API key |
|----------|----------|---------|
| **OpenAI Whisper** (default) | General purpose, multilingual | `OPENAI_API_KEY` |
| **ElevenLabs Scribe** | High accuracy, 99 languages, word timestamps | `ELEVENLABS_API_KEY` |
| **Sarvam AI** | Indic languages (Hindi, Tamil, Telugu, etc.) | `SARGAM_API_KEY` |
| **OpenRouter** | Access to various AI models | `OPENROUTER_API_KEY` |
| **Local** (faster-whisper) | Offline, free, no API key needed | None |

See [Provider Guide](docs/user/providers.md) for detailed comparison, pricing, and setup.

## Configuration

```yaml
# ~/.anyscribecli/config.yaml
provider: openai          # Transcription provider
language: auto             # Language (auto-detect or ISO code)
keep_media: false          # Keep audio files after transcription
output_format: clean       # clean | timestamped
prompt_download: never     # never | ask | always — download video after transcription
local_file_media: skip     # skip | copy | move | ask — what to do with local files
workspace_path: ""         # empty = ~/anyscribe (default), or set a custom path
```

API keys and passwords live in `~/.anyscribecli/.env` (separate from config, never committed).

See [Configuration Guide](docs/user/configuration.md) for all options.

## Claude Code Integration

ascli ships with a [Claude Code skill](https://code.claude.com/docs/en/skills) that teaches Claude how to transcribe, configure providers, and troubleshoot on your behalf. After installing ascli:

```bash
ascli install-skill
```

Or run `ascli onboard` — it auto-detects Claude Code and offers to install the skill. Once installed, Claude can use `/ascli` or auto-activate when you ask it to transcribe something.

## Documentation

| For | Where |
|-----|-------|
| First-time users | [Getting Started](docs/user/getting-started.md) |
| Command reference | [Commands](docs/user/commands.md) |
| All config options | [Configuration](docs/user/configuration.md) |
| Provider comparison | [Providers](docs/user/providers.md) |
| AI developers | [CLAUDE.md](CLAUDE.md) |
| Agent directives | [AGENTS.md](AGENTS.md) |
| Developer memory | [Building Docs](docs/building/) |

## Development

```bash
git clone https://github.com/rishmadaan/anyscribecli.git
cd anyscribecli
pip install -e ".[dev]"

ruff check src/          # lint
ruff format src/         # format
pytest                   # test
```

## License

MIT
