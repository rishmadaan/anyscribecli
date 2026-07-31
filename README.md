# anyscribe

**Let your AI agent transcribe anything.** Turns YouTube videos, Instagram reels, and local audio/video files into structured, searchable markdown, browsable in Obsidian.

Built agent-first, with three ways to reach it, in priority order:

- **With your AI agent** (primary) — anyscribe ships as a Claude Code skill that installs itself during onboarding, plus an MCP server (`pip install "anyscribe[mcp]"`, ten tools) for Claude Desktop, Cursor, and any MCP host. Every command also takes `--json` and `--yes` for agents, CI, and scripts.
- **The web UI** (`anyscribe ui`) — a clean local dashboard at `127.0.0.1:8457` for when you want to see it: paste a URL, watch progress live, browse history, change settings, first-run wizard included.
- **The CLI** (`anyscribe "<url>"`, `anyscribe onboard`) — one command with arrow-key prompts, for when you want your hands on it.

Shared backend, shared state: a transcription started from any surface is visible to all of them.

### Private by default, local-first

- **The Web UI is a local server, not a cloud service.** It runs at `127.0.0.1:8457` on your own machine. No account, no sign-up, no telemetry. There is no "anyscribe.com" backend.
- **Internet is only involved when *you* ask for it.** Three cases, all transparent:
  - **Downloading a YouTube or Instagram source** — obvious; you gave it the URL.
  - **Calling an API provider** (OpenAI, Deepgram, ElevenLabs, Sarvam, Groq, OpenRouter) — your audio goes to the provider you picked, and nothing else. Your data stays between you and them.
  - **Pulling a Whisper model** (one-time, only if you enable local transcription) — weights download from Hugging Face.
- **Fully offline is available.** Local files + the local provider (`anyscribe local setup --model base`) = zero network traffic. Your audio never leaves your machine. Same pipeline, same output format as the cloud providers.
- No analytics, no phone-home. `anyscribe update --check` reaches PyPI to compare versions, but only when you run it.

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![PyPI](https://img.shields.io/pypi/v/anyscribe.svg)](https://pypi.org/project/anyscribe/)
[![Platforms: macOS, Linux, Windows](https://img.shields.io/badge/platform-macOS%20%7C%20Linux%20%7C%20Windows-informational.svg)](https://pypi.org/project/anyscribe/)

---

## What it does

```
URL or local file → Download/convert audio → Transcribe → Formatted Markdown → Obsidian Vault
```

- **7 transcription providers** — OpenAI Whisper, Deepgram Nova, ElevenLabs, Groq, OpenRouter, Sarvam AI, Local (offline)
- **Speaker diarization** — `--diarize` flag for multi-speaker transcripts (meetings, interviews, podcasts)
- **3 input sources** — YouTube, Instagram (reels + posts), local files (mp3, mp4, m4a, wav, opus, ogg, flac, webm)
- **Obsidian-native output** — YAML frontmatter, word count, reading time, tags
- **Master index + daily logs** — browse everything in Obsidian
- **Download-only mode** — grab video or audio without transcribing
- **Batch processing** — transcribe a list of URLs from a file
- **No duplicate work** — a source already in your vault is returned from the existing file, not re-transcribed; `--force` overrides
- **Web UI** — `anyscribe ui` launches a local dashboard (transcribe, browse history, manage settings, first-run onboarding wizard) at `127.0.0.1:8457` — served from your own machine, no cloud backend; local Whisper model downloads show byte-level progress (percent + MB)
- **Local-first, no account** — no sign-up, no telemetry, no SaaS layer; fully offline with the local provider + local files
- **Agent-friendly CLI** — `--json` output, structured exit codes, `--yes` for non-interactive runs on every consequential command; no silent defaults for choices an agent might make on the user's behalf
- **Three-surface onboarding parity** — wizard modal in the Web UI, interactive prompts in `anyscribe onboard`, flag-driven in `anyscribe onboard --yes ...`; all three write the same config

## Quick Start

### Install

**macOS / Linux** (one command — installs Python, ffmpeg, and anyscribe):
```bash
curl -fsSL https://raw.githubusercontent.com/rishmadaan/anyscribe/main/install.sh | bash
```

**Windows** (PowerShell — installs Python, ffmpeg, and anyscribe):
```powershell
irm https://raw.githubusercontent.com/rishmadaan/anyscribe/main/install.ps1 | iex
```

**Or install manually:**
```bash
pip install anyscribe
```

> **Upgrading from `anyscribecli`?** The package, command, and app folder were
> renamed (the `scribe` and `ascli` commands still work as permanent aliases).
> After `pip install --upgrade anyscribe`, run `anyscribe migrate` once — it
> moves your config and API keys from `~/.anyscribecli/` to `~/.anyscribe/`
> without overwriting anything. Add `--dry-run` to preview first.

### Get started

```bash
anyscribe ui    # opens web dashboard — guides you through setup
```

On first launch the web UI opens a full-screen **onboarding wizard** — pick a provider, paste the API key (with a live Test button), optionally enable offline transcription, confirm your workspace, done.

> **Windows:** If `anyscribe` isn't recognized, use `python -m anyscribe ui`
>
> **Alternative paths** (same end state):
> - `anyscribe onboard` — interactive terminal wizard.
> - `anyscribe onboard --provider openai --api-key "$OPENAI_API_KEY" --yes --json` — headless mode for agents, CI, and scripts.

### Transcribe

```bash
# From a URL
anyscribe "https://www.youtube.com/watch?v=VIDEO_ID"

# From a local file
anyscribe /path/to/podcast.mp3
```

> **Always wrap URLs in quotes** — shells like zsh break URLs with `?` and `&`.

### Download (no transcription)

```bash
anyscribe download "https://www.youtube.com/watch?v=VIDEO_ID"            # video
anyscribe download "https://www.youtube.com/watch?v=VIDEO_ID" --audio-only  # audio
```

## Commands

| Command | Description |
|---------|-------------|
| `anyscribe onboard` | Interactive setup wizard (TUI) |
| `anyscribe onboard --provider X --api-key $KEY --yes` | Headless setup for agents / CI |
| `anyscribe transcribe "<url or file>"` | Transcribe a video or local file to markdown (`-p` picks a provider, `-m` a specific model, e.g. `-p openai -m whisper-1`) |
| `anyscribe download "<url>"` | Download video or audio only |
| `anyscribe batch <file>` | Batch transcribe URLs or file paths from a file |
| `anyscribe rm <path-or-slug>` | Delete a transcript and update the index |
| `anyscribe logs` | View recent transcription activity + recovery artifacts |
| `anyscribe config` | Defaults dashboard — the provider + model your next run uses, and every alternative |
| `anyscribe config show/set/path/list-keys` | View and change settings |
| `anyscribe providers list/test` | Manage transcription providers |
| `anyscribe local setup --model <size>` | Install faster-whisper + download a Whisper model |
| `anyscribe local status` / `anyscribe local teardown` | Report / remove offline transcription |
| `anyscribe model list / pull / rm / reinstall / info` | Manage cached Whisper model weights |
| `anyscribe ui` | Launch the web UI in your browser |
| `anyscribe tray` | Menu-bar icon that supervises the web server (needs `pip install "anyscribe[tray]"`) |
| `anyscribe install-service` / `anyscribe uninstall-service` | Auto-start the tray at login (macOS) |
| `anyscribe install-skill` | Install Claude Code skill |
| `anyscribe update` | Update to the latest version |
| `anyscribe doctor` | Check system health |

### Transcribe options

```bash
anyscribe transcribe "<url>"
  --quality <tier>         # accuracy | balanced | cost | free — picks a provider (default: balanced)
  --provider, -p <name>    # Explicit provider (openai, deepgram, elevenlabs, sargam, groq, local, ...) — overrides --quality
  --language, -l <code>    # Language code (default: auto-detect)
  --diarize, -d            # Enable speaker diarization (multi-speaker transcripts)
  --force, -f              # Re-transcribe even if this source is already in the vault
  --json, -j               # JSON output for scripting/AI agents
  --keep-media             # Keep the downloaded audio file
  --clipboard, -c          # Read URL from clipboard
  --quiet, -q              # Suppress progress output
```

Provide a URL, file path, or use interactive mode:
```bash
anyscribe transcribe "https://..."     # quoted URL (primary)
anyscribe transcribe /path/to/file.mp3 # local audio/video file
anyscribe transcribe                    # interactive prompt (no quoting needed)
anyscribe transcribe --clipboard        # read URL from system clipboard
```

### Download options

```bash
anyscribe download "<url>"
  --video / --audio-only     # Video (default) or audio only
  --json, -j                 # JSON output
  --quiet, -q                # Suppress progress
  --clipboard, -c            # Read URL from clipboard
```

### Batch options

```bash
anyscribe batch <file>
  --provider, -p <name>      # Override provider
  --language, -l <code>      # Override language
  --json, -j                 # JSON output
  --keep-media               # Keep audio files
  --force, -f                # Re-transcribe sources already in the vault
  --quiet, -q                # Suppress progress
  --stop-on-error            # Stop at first failure
```

### JSON output

```bash
anyscribe transcribe "https://youtube.com/watch?v=abc123" --json
```

```json
{
  "success": true,
  "file": "~/anyscribe/sources/youtube/video-title.md",
  "title": "Video Title",
  "platform": "youtube",
  "duration": "12:34",
  "language": "en",
  "word_count": 1500,
  "provider": "openai"
}
```

## Menu-bar app

Want `anyscribe ui` always running instead of launching it by hand? Install the tray extra and click the icon:

```bash
pip install "anyscribe[tray]"
anyscribe tray                    # menu-bar icon: Open UI, Status, Restart, Check for updates, Quit
anyscribe install-service         # optional: auto-start the tray at login (macOS)
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
│   ├── youtube/<slug>.md
│   ├── instagram/<slug>.md
│   └── local/<slug>.md
└── daily/YYYY-MM-DD.md

~/.anyscribe/                          # App internals (hidden)
├── config.yaml                           # Settings (no secrets)
├── .env                                  # API keys + passwords
├── downloads/                            # Downloads (separate from vault)
│   ├── audio/<platform>/                 # Kept audio (if keep_media=true)
│   └── video/<platform>/                 # Downloaded videos
├── sessions/                             # Login sessions
└── logs/                                 # Processing logs
```

> **Workspace is visible and configurable** — transcripts default to `~/anyscribe/` (no hidden dot-dir). Change it with `anyscribe config set workspace_path /your/path`. Downloads stay separate to keep the vault lightweight.

## Providers

| Provider | Best for | API key |
|----------|----------|---------|
| **OpenAI Whisper** (default) | General purpose, multilingual | `OPENAI_API_KEY` |
| **Deepgram Nova** | Diarization (auto-selected with `--diarize`), Hinglish | `DEEPGRAM_API_KEY` |
| **ElevenLabs Scribe** | High accuracy, 99 languages, word timestamps | `ELEVENLABS_API_KEY` |
| **Sarvam AI** | Indic languages (Hindi, Tamil, Telugu, etc.) | `SARGAM_API_KEY` |
| **OpenRouter** | Access to various AI models | `OPENROUTER_API_KEY` |
| **Local** (faster-whisper) | Offline, free, no API key needed | None |

See [Provider Guide](docs/user/providers.md) for detailed comparison, pricing, and setup.

## Configuration

```yaml
# ~/.anyscribe/config.yaml
provider: openai          # Transcription provider (used when quality is `custom`)
quality: balanced          # accuracy | balanced | cost | free | custom — picks the provider
provider_models: {}        # provider -> pinned model id (empty = each provider's default)
extra_models: {}           # openrouter -> your own model slugs, merged into the pickers
language: auto             # Language (auto-detect or ISO code)
keep_media: false          # Keep audio files after transcription
output_format: clean       # clean | timestamped | diarized
diarize: false             # enable speaker diarization
prompt_download: never     # never | ask | always — download video after transcription
local_file_media: skip     # skip | copy | move | ask — what to do with local files
workspace_path: ""         # empty = ~/anyscribe (default), or set a custom path
```

API keys and passwords live in `~/.anyscribe/.env` (separate from config, never committed). You can set API keys directly:

```bash
anyscribe config set deepgram_api_key YOUR_KEY
anyscribe config set openai_api_key YOUR_KEY
```

> **One knob picks the provider.** `quality` is either a tier (which chooses the provider) or `custom` (which uses your `provider` line). Setting a provider anywhere writes `quality: custom` in the same save, so your choice sticks. Run `anyscribe config` to see what wins.

> **Diarization auto-routing:** When you use `--diarize` without specifying a provider, anyscribe automatically switches to Deepgram (if configured) for best speaker detection. Override with `-p openai` if needed.

> **Timestamps on OpenAI are automatic.** The default model `gpt-transcribe` is cheaper and more accurate but can't emit `[mm:ss]` markers, so anyscribe switches that run to `whisper-1` when your output format is `timestamped` or `diarized` — unless you named a model yourself with `-m`.

> **Web UI labels:** The CLI's `--diarize` flag is shown as `Multi-speaker` in the web UI, and the `diarized` output format is labelled `with-speaker-labels`. Wire values are unchanged — the rename is display-only so the UI reads in plain English.

See [Configuration Guide](docs/user/configuration.md) for all options.

## Claude Code Integration

anyscribe ships with a [Claude Code skill](https://code.claude.com/docs/en/skills) that teaches Claude how to transcribe, configure providers, and troubleshoot on your behalf. After installing anyscribe:

```bash
anyscribe install-skill
```

Or run `anyscribe onboard` — it auto-detects Claude Code and offers to install the skill. Once installed, Claude can use `/anyscribe` or auto-activate when you ask it to transcribe something.

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
git clone https://github.com/rishmadaan/anyscribe.git
cd anyscribe
pip install -e ".[dev]"

ruff check src/          # lint
ruff format src/         # format
pytest                   # test
```

## License

MIT
