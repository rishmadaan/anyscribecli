---
summary: Complete reference for all scribe commands, flags, and options.
read_when:
  - You want to know what flags are available
  - You need the exact syntax for a command
  - You're scripting or automating with scribe
---

# Command Reference

Every scribe command. Copy-paste friendly.

## Quick Overview

| Command | What it does |
|---------|-------------|
| `scribe "<url or file>"` | Transcribe a URL or local file (default action) |
| `scribe onboard` | First-time setup wizard |
| `scribe download "<url>"` | Download video or audio only (no transcription) |
| `scribe batch <file>` | Batch transcribe URLs or file paths from a file |
| `scribe config show` | View current settings |
| `scribe config set <key> <value>` | Change a setting |
| `scribe config path` | Print config file location |
| `scribe providers list` | Show available providers |
| `scribe providers test [name]` | Test a provider's API key |
| `scribe install-skill` | Install/update Claude Code skill |
| `scribe update` | Update to the latest version |
| `scribe doctor` | Check system health |
| `scribe --version` | Show version |
| `scribe --help` | Show help |

---

## scribe onboard

Interactive setup wizard. Run this once after installing, or again to change settings.

```bash
scribe onboard
```

**What it does** (arrow-key selectors throughout):
1. Checks system dependencies (Python, yt-dlp, ffmpeg) — offers to install missing ones
2. Choose transcription provider (5 options, arrow keys)
3. Enter API key for your chosen provider
4. Optionally add API keys for other providers
5. Optionally configure Instagram credentials
6. Choose default language (arrow-key selector with common options)
7. Choose whether to keep audio files after transcription
8. Choose post-transcription download behavior (never/ask/always)
9. Choose workspace location (default: `~/anyscribe/`)
10. Creates your Obsidian workspace

### Flags

| Flag | Description |
|------|-------------|
| `--force`, `-f` | Re-run setup even if already configured |
| `--skip-deps` | Skip the dependency check |

### Examples

```bash
# First-time setup
scribe onboard

# Re-run to change settings (e.g., switch provider or update API key)
scribe onboard --force

# Skip dependency check (you know they're installed)
scribe onboard --force --skip-deps
```

---

## scribe (default: transcribe)

The main command. Transcribes a URL or local audio/video file and saves a formatted markdown file. **A bare URL routes to transcribe automatically — no subcommand needed.**

```bash
scribe "<url>"                          # bare URL — just works
scribe /path/to/file.mp3               # local file — just works
scribe transcribe "<url>"              # explicit subcommand (also works)
```

> **Important:** Always wrap URLs in quotes. Shells like zsh treat `?` as a special character, which breaks unquoted YouTube URLs. Local file paths don't need quotes.

### Ways to provide input

```bash
# 1. Pass a URL as an argument (always use quotes)
scribe "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

# 2. Pass a local audio/video file
scribe /path/to/podcast.mp3
scribe ~/recordings/meeting.m4a

# 3. Run without input — you'll be prompted to paste a URL or file path
scribe transcribe

# 4. Copy a URL to your clipboard, then:
scribe --clipboard
```

### Flags

| Flag | Short | Description | Default |
|------|-------|-------------|---------|
| `--provider` | `-p` | Transcription provider to use | From config (openai) |
| `--language` | `-l` | Language code for transcription | `auto` (auto-detect) |
| `--json` | `-j` | Output result as JSON | Off |
| `--keep-media` | | Keep the downloaded audio file | From config (false) |
| `--diarize` | `-d` | Enable speaker diarization (auto-routes to Deepgram if configured) | Off |
| `--quiet` | `-q` | No progress output (just the result) | Off |
| `--clipboard` | `-c` | Read URL from system clipboard | Off |

### Examples

```bash
# YouTube video (always quote the URL)
scribe "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

# Instagram reel
scribe "https://www.instagram.com/reel/C17LiBLyIOe/"

# Local audio/video file
scribe /path/to/podcast.mp3
scribe ~/recordings/meeting.m4a
scribe ./interview.opus

# Interactive — paste URL or file path when prompted
scribe transcribe

# From clipboard
scribe --clipboard

# Specify language (skip auto-detection)
scribe "https://youtube.com/watch?v=abc123" --language es

# Keep the audio file alongside the transcript
scribe "https://youtube.com/watch?v=abc123" --keep-media

# Enable speaker diarization (auto-switches to Deepgram if configured)
scribe "https://youtube.com/watch?v=abc123" --diarize

# Diarize with a specific provider (overrides auto-routing)
scribe "https://youtube.com/watch?v=abc123" --diarize --provider openai

# Diarize Hinglish to Latin script
scribe "https://youtube.com/watch?v=abc123" --diarize --provider deepgram --language hi-Latn

# JSON output — for scripts, AI agents, or piping to other tools
scribe "https://youtube.com/watch?v=abc123" --json
```

### JSON Output

When you use `--json`, scribe prints structured JSON to stdout (progress goes to stderr):

```json
{
  "success": true,
  "file": "/Users/you/anyscribe/sources/youtube/video-title.md",
  "title": "Video Title",
  "platform": "youtube",
  "duration": "12:34",
  "language": "en",
  "word_count": 1500,
  "provider": "openai"
}
```

On error:

```json
{
  "success": false,
  "error": "yt-dlp download failed: Video unavailable"
}
```

> **Scripting tip:** Use `--json --quiet` together to get clean JSON with no extra output. Pipe to `jq` for filtering: `scribe "url" --json -q | jq '.file'`

### Supported Inputs

| Source | Patterns | Status |
|--------|----------|--------|
| YouTube | `youtube.com/watch?v=`, `youtu.be/`, `youtube.com/shorts/`, `youtube.com/live/` | Working |
| Instagram | `instagram.com/reel/`, `instagram.com/p/` | Working (requires Instagram credentials in config) |
| Local files | `.mp3`, `.mp4`, `.m4a`, `.wav`, `.opus`, `.ogg`, `.flac`, `.webm`, `.aac`, `.wma` | Working |

---

## scribe batch

Transcribe multiple URLs or local files from a list. One entry per line, blank lines and `#comments` are skipped.

```bash
scribe batch urls.txt
```

### Flags

| Flag | Short | Description | Default |
|------|-------|-------------|---------|
| `--provider` | `-p` | Override provider | From config |
| `--language` | `-l` | Override language | `auto` |
| `--json` | `-j` | Output results as JSON | Off |
| `--keep-media` | | Keep audio files | From config |
| `--diarize` | `-d` | Enable speaker diarization | Off |
| `--quiet` | `-q` | Suppress progress | Off |
| `--stop-on-error` | | Stop at first failure | Off (continues) |

### Examples

```bash
# Create a file with URLs and/or file paths
cat > urls.txt << EOF
https://youtube.com/watch?v=abc123
https://youtube.com/watch?v=def456
# this line is skipped
https://instagram.com/reel/xyz789
/path/to/local-recording.mp3
EOF

# Transcribe all
scribe batch urls.txt

# Stop if any fail
scribe batch urls.txt --stop-on-error

# JSON output for scripting
scribe batch urls.txt --json
```

---

## scribe download

Download video or audio from a URL — no transcription. Useful when you just want the file.

```bash
scribe download "<url>"
```

Saves to `~/.anyscribecli/downloads/video/<platform>/` (default) or `~/.anyscribecli/downloads/audio/<platform>/` with `--audio-only`.

### Flags

| Flag | Description | Default |
|------|-------------|---------|
| `--video` / `--audio-only` | Download video (default) or extract audio only | `--video` |
| `--json`, `-j` | Output result as JSON | Off |
| `--quiet`, `-q` | Suppress progress output | Off |
| `--clipboard`, `-c` | Read URL from clipboard | Off |

### Examples

```bash
# Download video
scribe download "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

# Download audio only (no video)
scribe download "https://www.youtube.com/watch?v=dQw4w9WgXcQ" --audio-only

# From clipboard
scribe download --clipboard

# Interactive (paste URL when prompted)
scribe download

# JSON output
scribe download "https://youtube.com/watch?v=abc123" --json
```

---

## scribe config

View and change settings.

```bash
scribe config show           # display all settings
scribe config set key value  # change a setting
scribe config path           # print config file location
```

### Flags

| Command | Flag | Short | Description |
|---------|------|-------|-------------|
| `config show` | `--json` | `-j` | Output settings as JSON |

### Examples

```bash
# Show current config
scribe config show

# Change provider
scribe config set provider elevenlabs

# Change language
scribe config set language hi

# Set an API key (stored in .env, not config.yaml)
scribe config set deepgram_api_key YOUR_KEY
scribe config set openai_api_key YOUR_KEY

# Set Instagram credentials
scribe config set instagram.username myuser
scribe config set instagram.password mypass

# Get JSON output
scribe config show --json
```

> **Dot-notation:** Use dots for nested keys like `instagram.username`.
>
> **API keys:** `scribe config set` also accepts API key names (e.g., `deepgram_api_key`, `openai_api_key`, `elevenlabs_api_key`, `sargam_api_key`, `openrouter_api_key`). These are stored in `~/.anyscribecli/.env`, not in config.yaml.

---

## scribe providers

Manage transcription providers.

```bash
scribe providers list          # show all providers
scribe providers test          # test active provider
scribe providers test openai   # test a specific provider
```

### Flags

| Command | Flag | Short | Description |
|---------|------|-------|-------------|
| `providers list` | `--json` | `-j` | Output provider list as JSON |

### Available Providers

| Provider | API Key Env Var | Best For |
|----------|-----------------|----------|
| `openai` | `OPENAI_API_KEY` | General purpose, multilingual, diarization (default) |
| `deepgram` | `DEEPGRAM_API_KEY` | Fast, accurate, native diarization + Hindi Latin |
| `openrouter` | `OPENROUTER_API_KEY` | Access to various models |
| `elevenlabs` | `ELEVENLABS_API_KEY` | High accuracy, 99 languages |
| `sargam` | `SARGAM_API_KEY` | Indic languages (Hindi, Tamil, Telugu, etc.) |
| `local` | None needed | Offline, free, runs on your machine |

> **Local provider** requires `pip install faster-whisper`. No API key, no internet. Runs on CPU (slower) or GPU (fast). Models download automatically on first use.

---

## scribe install-skill

Manually install or update the scribe skill for [Claude Code](https://docs.anthropic.com/en/docs/claude-code). This teaches Claude how to transcribe, configure providers, and troubleshoot scribe on your behalf.

```bash
scribe install-skill
```

Copies skill files from the scribe package to `~/.claude/skills/scribe/`. Requires Claude Code to be installed (`~/.claude/` must exist).

### Flags

| Flag | Short | Description |
|------|-------|-------------|
| `--force` | `-f` | Overwrite existing skill files |

> **Tip:** You usually don't need to run this manually. The skill **auto-installs** when Claude Code is detected and **auto-updates** on every CLI invocation when the version changes. Use `--force` only if you need to repair a corrupted install.

---

## scribe update

Update scribe to the latest version by pulling from git and reinstalling.

```bash
scribe update
```

### Flags

| Flag | Short | Description |
|------|-------|-------------|
| `--force` | `-f` | Update even if you have local changes (stashes them first) |
| `--check` | `-c` | Only check if an update is available, don't install |

### Examples

```bash
# Check for updates without installing
scribe update --check

# Update to latest
scribe update

# Force update (stashes any local changes)
scribe update --force
```

---

## scribe doctor

Run diagnostic checks on your system. Useful when something isn't working.

```bash
scribe doctor
```

**What it checks:**
1. System dependencies (Python, yt-dlp, ffmpeg, ffprobe)
2. Configuration (app directory, config.yaml, .env, workspace vault, workspace index)
3. Installation info (version, install type, repo path)
4. Claude Code skill (installed, version, current or outdated)
5. Available updates

> **Tip:** If you're reporting a bug or asking for help, run `scribe doctor` and include the output — it gives all the info needed to debug.

---

## scribe --version

Print the installed version.

```bash
scribe --version
# Output: scribe v0.7.2
```

---

## scribe --help

Show all available commands and global options.

```bash
scribe --help
```

Every command also has its own help:

```bash
scribe transcribe --help
scribe onboard --help
```

---

## Shell Completion

scribe supports tab-completion for bash, zsh, and fish. Install it once:

```bash
scribe --install-completion
```

After restarting your shell, you can press Tab to autocomplete commands and flags.
