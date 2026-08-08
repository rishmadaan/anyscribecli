# anyscribe

**Let your AI agent transcribe anything.** Turns YouTube videos, Instagram reels, and local audio/video files into structured, searchable markdown, browsable in Obsidian.

Built agent-first, with three ways to reach it, in priority order:

- **With your AI agent** (primary) — anyscribe ships as a Claude Code skill that installs itself the first time you run any scribe command, plus an MCP server (`pip install "anyscribe[mcp]"`, ten tools) for Claude Desktop, Cursor, and any MCP host. Most commands that report results also take `--json`, and the ones that would stop to ask take `--yes` — for agents, CI, and scripts.
- **The web UI** (`scribe ui`) — a clean local dashboard at `127.0.0.1:8457` for when you want to see it: paste a URL, watch progress live, browse history, change settings, first-run wizard included.
- **The CLI** (`scribe "<url>"`, `scribe onboard`) — one command with arrow-key prompts, for when you want your hands on it.

Shared backend, shared state: a transcription started from any surface is visible to all of them.

### Private by default, local-first

- **The Web UI is a local server, not a cloud service.** It runs at `127.0.0.1:8457` on your own machine. No account, no sign-up, no telemetry. There is no "anyscribe.com" backend.
- **Internet is only involved when *you* ask for it.** Three cases, all transparent:
  - **Downloading a YouTube or Instagram source** — obvious; you gave it the URL.
  - **Calling an API provider** (OpenAI, Deepgram, ElevenLabs, Sarvam, Groq, OpenRouter) — your audio goes to the provider you picked, and nothing else. Your data stays between you and them.
  - **Pulling a Whisper model** (one-time, only if you enable local transcription) — weights download from Hugging Face.
- **Fully offline is available.** Local files + the local provider (`scribe local setup --model base`) = zero network traffic. Your audio never leaves your machine. Same pipeline, same output format as the cloud providers.
- No analytics, no phone-home. `scribe update --check` reaches PyPI to compare versions, but only when you run it.

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](https://github.com/rishmadaan/anyscribe/blob/main/LICENSE)
[![PyPI](https://img.shields.io/pypi/v/anyscribe.svg)](https://pypi.org/project/anyscribe/)
[![Platforms: macOS, Linux, Windows](https://img.shields.io/badge/platform-macOS%20%7C%20Linux%20%7C%20Windows-informational.svg)](https://pypi.org/project/anyscribe/)

---

## What you need

- **Python 3.10 or newer** — [python.org](https://www.python.org/downloads/)
- **ffmpeg and yt-dlp** — the installers below put both in place for you; with the pip route, install them yourself (`brew install ffmpeg yt-dlp`, or [ffmpeg.org](https://ffmpeg.org/))
- **An API key** for one cloud provider (OpenAI, Deepgram, ElevenLabs, Sarvam, Groq, OpenRouter) — or none at all if you run offline with the local provider

`scribe doctor` checks all of this at any time, and the setup wizard checks it for you on first run.

## Install

**macOS / Linux** — installs Python, ffmpeg, yt-dlp, and scribe with the menu-bar app:

```bash
curl -fsSL https://raw.githubusercontent.com/rishmadaan/anyscribe/main/install.sh | bash
```

**Windows** (PowerShell) — same, for Windows:

```powershell
irm https://raw.githubusercontent.com/rishmadaan/anyscribe/main/install.ps1 | iex
```

**Already have Python, ffmpeg, and yt-dlp?**

```bash
pip install anyscribe
```

Then start it:

```bash
scribe ui    # opens the web dashboard — guides you through setup
```

On first launch the web UI opens a full-screen onboarding wizard — pick a provider, paste the API key (with a live Test button), optionally enable offline transcription, confirm your workspace, done. Prefer the terminal? `scribe onboard` does the same thing with arrow keys, and `scribe onboard --provider openai --api-key "$OPENAI_API_KEY" --yes --json` does it headlessly for agents and CI.

> **Windows:** if `scribe` isn't recognized, use `python -m anyscribe ui`.

![The anyscribe web UI — paste a URL, watch progress, browse your transcripts](https://raw.githubusercontent.com/rishmadaan/anyscribe/main/landing/assets/scribe-ui.png)

Then transcribe something:

```bash
scribe "https://www.youtube.com/watch?v=VIDEO_ID"   # always quote URLs — shells break on ? and &
scribe /path/to/podcast.mp3
```

## Docs

| Start here | What it covers |
|------------|----------------|
| **[Use it from your AI agent](https://github.com/rishmadaan/anyscribe/blob/main/docs/user/agents.md)** | The primary path — Claude Code skill and MCP setup, what your agent can drive |
| [Getting started](https://github.com/rishmadaan/anyscribe/blob/main/docs/user/getting-started.md) | Install to first transcript, step by step |
| [Commands](https://github.com/rishmadaan/anyscribe/blob/main/docs/user/commands.md) | Every command and flag, with examples |
| [Providers](https://github.com/rishmadaan/anyscribe/blob/main/docs/user/providers.md) | The seven providers compared — accuracy, cost, languages |
| [Configuration](https://github.com/rishmadaan/anyscribe/blob/main/docs/user/configuration.md) | Every setting, where it lives, what it changes |
| [Troubleshooting](https://github.com/rishmadaan/anyscribe/blob/main/docs/user/troubleshooting.md) | Common errors and plain-English fixes |

For contributors: [CLAUDE.md](https://github.com/rishmadaan/anyscribe/blob/main/CLAUDE.md), [AGENTS.md](https://github.com/rishmadaan/anyscribe/blob/main/AGENTS.md), and [docs/building/](https://github.com/rishmadaan/anyscribe/tree/main/docs/building/).

## Development

```bash
git clone https://github.com/rishmadaan/anyscribe.git
cd anyscribe
pip install -e ".[dev]"

ruff check src/          # lint
ruff format src/         # format
pytest                   # test
```

## Upgrading from `anyscribecli`

The package, command, and app folder were renamed (the `scribe` and `ascli` commands still work as permanent aliases). After `pip install --upgrade anyscribe`, run `anyscribe migrate` once — it moves your config and API keys from `~/.anyscribecli/` to `~/.anyscribe/` without overwriting anything. Add `--dry-run` to preview first.

## License

MIT
