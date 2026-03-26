# anyscribecli

**Download. Transcribe. Markdown.** A CLI tool that turns YouTube and Instagram videos into structured, searchable markdown — browsable in Obsidian.

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

---

## What it does

```
YouTube/Instagram URL → Download audio → Transcribe (OpenAI Whisper) → Formatted Markdown → Obsidian Vault
```

- Downloads audio optimized for transcription (16kHz, mono, 64kbps)
- Transcribes via pluggable API providers (OpenAI default, OpenRouter, ElevenLabs, Sargam planned)
- Outputs markdown with YAML frontmatter, word count, reading time, timestamps
- Maintains a master index + daily processing logs in your Obsidian vault
- `--json` flag on all commands for scripting and AI agent integration

## Quick Start

### Install (recommended)

One command — checks for dependencies, installs everything, and runs setup:

```bash
curl -fsSL https://raw.githubusercontent.com/rishmadaan/anyscribecli/main/install.sh | bash
```

### Or install manually

```bash
# Option A: pip install from GitHub
pip install git+https://github.com/rishmadaan/anyscribecli.git

# Option B: clone and install (for development)
git clone https://github.com/rishmadaan/anyscribecli.git
cd anyscribecli
pip install -e .
```

Then run the setup wizard:

```bash
ascli onboard
```

The wizard checks your system for dependencies (Python, yt-dlp, ffmpeg), prompts for your API key, and sets up an Obsidian vault at `~/.anyscribecli/workspace/`.

### Transcribe

```bash
ascli transcribe https://www.youtube.com/watch?v=VIDEO_ID
```

That's it. Open `~/.anyscribecli/workspace/` in Obsidian to browse your transcripts.

## Commands

| Command | Description |
|---------|-------------|
| `ascli onboard` | Interactive setup wizard (first-time + reconfigure) |
| `ascli transcribe <url>` | Download and transcribe a video URL |
| `ascli update` | Update to the latest version |
| `ascli doctor` | Check system health and dependencies |
| `ascli --version` | Show version |
| `ascli --help` | Rich-formatted help |

### Transcribe Options

```bash
ascli transcribe <url>
  --provider, -p <name>    # Override transcription provider
  --language, -l <code>    # Language code (default: auto-detect)
  --json, -j               # JSON output for scripting/AI agents
  --keep-media             # Keep the downloaded audio file
  --quiet, -q              # Suppress progress output
```

### JSON Output

All commands support `--json` for machine-readable output:

```bash
ascli transcribe https://youtube.com/watch?v=abc123 --json
```

```json
{
  "success": true,
  "file": "~/.anyscribecli/workspace/sources/youtube/2026-03-26/video-title.md",
  "title": "Video Title",
  "platform": "youtube",
  "duration": "12:34",
  "language": "en",
  "word_count": 1500,
  "provider": "openai"
}
```

## Prerequisites

The onboarding wizard checks for these and helps you install them:

| Dependency | Required | Install |
|------------|----------|---------|
| Python 3.10+ | Yes | [python.org](https://www.python.org/downloads/) |
| yt-dlp | Yes | `brew install yt-dlp` or `pip install yt-dlp` |
| ffmpeg | Yes | `brew install ffmpeg` or [ffmpeg.org](https://ffmpeg.org/) |
| OpenAI API key | Yes (default provider) | [platform.openai.com](https://platform.openai.com/api-keys) |

## Workspace Structure

Your transcripts live in an Obsidian vault:

```
~/.anyscribecli/workspace/
├── _index.md                         # Master index (newest first)
├── sources/
│   ├── youtube/2026-03-26/
│   │   └── video-title.md            # Transcript with frontmatter
│   └── instagram/2026-03-26/
│       └── reel-caption.md
├── daily/
│   └── 2026-03-26.md                 # Daily processing log
└── media/                            # Audio files (if keep_media=true)
```

Each transcript includes YAML frontmatter for Obsidian properties:

```yaml
---
source: https://youtube.com/watch?v=...
platform: youtube
title: "Video Title"
duration: "12:34"
language: en
provider: openai
word_count: 1500
reading_time: "8 min"
tags: [transcript, youtube]
---
```

## Configuration

All settings live at `~/.anyscribecli/config.yaml`:

```yaml
provider: openai        # Transcription provider
language: auto           # Language (auto-detect or ISO code)
keep_media: false        # Keep downloaded audio files
output_format: clean     # clean | timestamped (future)
```

API keys are stored separately in `~/.anyscribecli/.env`.

## Providers

| Provider | Status | Best For |
|----------|--------|----------|
| OpenAI (Whisper) | Active (default) | General purpose, multilingual |
| OpenRouter | Planned | Model flexibility, cost options |
| ElevenLabs | Planned | TBD |
| Sargam | Planned | Indic languages |
| Local (whisper.cpp) | Planned | Offline, privacy, no API cost |

The provider architecture is pluggable — adding a new provider is one file implementing the `TranscriptionProvider` interface.

## Development

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Lint
ruff check src/

# Format
ruff format src/

# Test
pytest
```

See [CLAUDE.md](CLAUDE.md) for AI developer instructions and [docs/building/](docs/building/) for the developer memory layer.

## License

MIT
