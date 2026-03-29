# anyscribecli

**Download. Transcribe. Markdown.** A CLI tool that turns YouTube and Instagram videos into structured, searchable markdown — browsable in Obsidian.

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-0.3.1-orange.svg)](https://github.com/rishmadaan/anyscribecli/releases)

---

## What it does

```
YouTube/Instagram URL → Download audio → Transcribe → Formatted Markdown → Obsidian Vault
```

- **5 transcription providers** — OpenAI Whisper, ElevenLabs, OpenRouter, Sarvam AI, Local (offline)
- **2 platforms** — YouTube and Instagram (reels + posts)
- **Obsidian-native output** — YAML frontmatter, word count, reading time, tags
- **Master index + daily logs** — browse everything in Obsidian
- **Download-only mode** — grab video or audio without transcribing
- **Batch processing** — transcribe a list of URLs from a file
- **`--json` on main commands** — for scripting and AI agent integration
- **Arrow-key onboarding wizard** — interactive setup, installs missing dependencies

## Quick Start

### Install

```bash
# From GitHub (recommended)
pip install git+https://github.com/rishmadaan/anyscribecli.git

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
ascli transcribe "https://www.youtube.com/watch?v=VIDEO_ID"
```

> **Always wrap URLs in quotes** — shells like zsh break URLs with `?` in them. Or just run `ascli transcribe` and paste when prompted.

### Download (no transcription)

```bash
ascli download "https://www.youtube.com/watch?v=VIDEO_ID"            # video
ascli download "https://www.youtube.com/watch?v=VIDEO_ID" --audio-only  # audio
```

## Commands

| Command | Description |
|---------|-------------|
| `ascli onboard` | Interactive setup wizard |
| `ascli transcribe "<url>"` | Transcribe a video to markdown |
| `ascli download "<url>"` | Download video or audio only |
| `ascli batch <file>` | Batch transcribe URLs from a file |
| `ascli config show/set/path` | View and change settings |
| `ascli providers list/test` | Manage transcription providers |
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

Three ways to provide the URL:
```bash
ascli transcribe "https://..."     # quoted argument (primary)
ascli transcribe                    # interactive prompt (no quoting needed)
ascli transcribe --clipboard        # read from system clipboard
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
  "file": "~/.anyscribecli/workspace/sources/youtube/2026-03-27/video-title.md",
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
~/.anyscribecli/
├── config.yaml                           # Settings (no secrets)
├── .env                                  # API keys + passwords
├── workspace/                            # Obsidian vault (pure markdown)
│   ├── _index.md                         # Master index (newest first)
│   ├── sources/
│   │   ├── youtube/YYYY-MM-DD/<slug>.md
│   │   └── instagram/YYYY-MM-DD/<slug>.md
│   └── daily/YYYY-MM-DD.md
├── media/                                # Downloads (separate from vault)
│   ├── audio/<platform>/YYYY-MM-DD/      # Kept audio (if keep_media=true)
│   └── video/<platform>/YYYY-MM-DD/      # Downloaded videos
├── sessions/                             # Login sessions
└── logs/                                 # Processing logs
```

> **Media is separate from the vault** — your Obsidian workspace stays lightweight, just markdown.

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
```

API keys and passwords live in `~/.anyscribecli/.env` (separate from config, never committed).

See [Configuration Guide](docs/user/configuration.md) for all options.

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
