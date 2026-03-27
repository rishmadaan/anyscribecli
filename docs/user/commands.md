---
summary: Complete reference for all ascli commands, flags, and options.
read_when:
  - You want to know what flags are available
  - You need the exact syntax for a command
  - You're scripting or automating with ascli
---

# Command Reference

Every ascli command. Copy-paste friendly.

## Quick Overview

| Command | What it does |
|---------|-------------|
| `ascli onboard` | First-time setup wizard |
| `ascli transcribe "<url>"` | Download and transcribe a video |
| `ascli download "<url>"` | Download video or audio only (no transcription) |
| `ascli batch <file>` | Batch transcribe URLs from a file |
| `ascli config show` | View current settings |
| `ascli config set <key> <value>` | Change a setting |
| `ascli providers list` | Show available providers |
| `ascli providers test [name]` | Test a provider's API key |
| `ascli update` | Update to the latest version |
| `ascli doctor` | Check system health |
| `ascli --version` | Show version |
| `ascli --help` | Show help |

---

## ascli onboard

Interactive setup wizard. Run this once after installing, or again to change settings.

```bash
ascli onboard
```

**What it does:**
1. Checks system dependencies (Python, yt-dlp, ffmpeg)
2. Offers to install anything missing
3. Asks for your API key
4. Sets preferences (provider, language, keep media)
5. Creates your Obsidian workspace

### Flags

| Flag | Description |
|------|-------------|
| `--force`, `-f` | Re-run setup even if already configured |
| `--skip-deps` | Skip the dependency check |

### Examples

```bash
# First-time setup
ascli onboard

# Re-run to change settings (e.g., switch provider or update API key)
ascli onboard --force

# Skip dependency check (you know they're installed)
ascli onboard --force --skip-deps
```

---

## ascli transcribe

The main command. Downloads audio from a URL, transcribes it, and saves a formatted markdown file.

```bash
ascli transcribe "<url>"
```

> **Important:** Always wrap URLs in quotes. Shells like zsh treat `?` as a special character, which breaks unquoted YouTube URLs. If you forget the quotes, ascli will detect the problem and tell you.

### Three ways to provide the URL

```bash
# 1. Pass the URL as an argument (always use quotes)
ascli transcribe "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

# 2. Run without a URL — you'll be prompted to paste it (no quoting needed)
ascli transcribe

# 3. Copy a URL to your clipboard, then:
ascli transcribe --clipboard
```

### Flags

| Flag | Short | Description | Default |
|------|-------|-------------|---------|
| `--provider` | `-p` | Transcription provider to use | From config (openai) |
| `--language` | `-l` | Language code for transcription | `auto` (auto-detect) |
| `--json` | `-j` | Output result as JSON | Off |
| `--keep-media` | | Keep the downloaded audio file | From config (false) |
| `--quiet` | `-q` | No progress output (just the result) | Off |
| `--clipboard` | `-c` | Read URL from system clipboard | Off |

### Examples

```bash
# YouTube video (always quote the URL)
ascli transcribe "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

# Instagram reel
ascli transcribe "https://www.instagram.com/reel/C17LiBLyIOe/"

# Interactive — paste URL when prompted
ascli transcribe

# From clipboard
ascli transcribe --clipboard

# Specify language (skip auto-detection)
ascli transcribe "https://youtube.com/watch?v=abc123" --language es

# Keep the audio file alongside the transcript
ascli transcribe "https://youtube.com/watch?v=abc123" --keep-media

# JSON output — for scripts, AI agents, or piping to other tools
ascli transcribe "https://youtube.com/watch?v=abc123" --json
```

### JSON Output

When you use `--json`, ascli prints structured JSON to stdout (progress goes to stderr):

```json
{
  "success": true,
  "file": "/Users/you/.anyscribecli/workspace/sources/youtube/2026-03-26/video-title.md",
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

> **Scripting tip:** Use `--json --quiet` together to get clean JSON with no extra output. Pipe to `jq` for filtering: `ascli transcribe <url> --json -q | jq '.file'`

### Supported Platforms

| Platform | URL patterns | Status |
|----------|-------------|--------|
| YouTube | `youtube.com/watch?v=`, `youtu.be/`, `youtube.com/shorts/`, `youtube.com/live/` | Working |
| Instagram | `instagram.com/reel/`, `instagram.com/p/` | Working (requires Instagram credentials in config) |

---

## ascli batch

Transcribe multiple URLs from a file. One URL per line, blank lines and `#comments` are skipped.

```bash
ascli batch urls.txt
```

### Flags

| Flag | Short | Description | Default |
|------|-------|-------------|---------|
| `--provider` | `-p` | Override provider | From config |
| `--language` | `-l` | Override language | `auto` |
| `--json` | `-j` | Output results as JSON | Off |
| `--keep-media` | | Keep audio files | From config |
| `--quiet` | `-q` | Suppress progress | Off |
| `--stop-on-error` | | Stop at first failure | Off (continues) |

### Examples

```bash
# Create a file with URLs
cat > urls.txt << EOF
https://youtube.com/watch?v=abc123
https://youtube.com/watch?v=def456
# this line is skipped
https://instagram.com/reel/xyz789
EOF

# Transcribe all
ascli batch urls.txt

# Stop if any fail
ascli batch urls.txt --stop-on-error

# JSON output for scripting
ascli batch urls.txt --json
```

---

## ascli download

Download video or audio from a URL — no transcription. Useful when you just want the file.

```bash
ascli download "<url>"
```

Saves to `~/.anyscribecli/media/video/` (default) or `~/.anyscribecli/media/audio/`.

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
ascli download "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

# Download audio only (no video)
ascli download "https://www.youtube.com/watch?v=dQw4w9WgXcQ" --audio-only

# From clipboard
ascli download --clipboard

# Interactive (paste URL when prompted)
ascli download

# JSON output
ascli download "https://youtube.com/watch?v=abc123" --json
```

---

## ascli config

View and change settings.

```bash
ascli config show           # display all settings
ascli config set key value  # change a setting
ascli config path           # print config file location
```

### Examples

```bash
# Show current config
ascli config show

# Change provider
ascli config set provider elevenlabs

# Change language
ascli config set language hi

# Set Instagram credentials
ascli config set instagram.username myuser
ascli config set instagram.password mypass

# Get JSON output
ascli config show --json
```

> **Dot-notation:** Use dots for nested keys like `instagram.username`.

---

## ascli providers

Manage transcription providers.

```bash
ascli providers list          # show all providers
ascli providers test          # test active provider
ascli providers test openai   # test a specific provider
```

### Available Providers

| Provider | API Key Env Var | Best For |
|----------|-----------------|----------|
| `openai` | `OPENAI_API_KEY` | General purpose, multilingual (default) |
| `openrouter` | `OPENROUTER_API_KEY` | Access to various models |
| `elevenlabs` | `ELEVENLABS_API_KEY` | High accuracy, 99 languages, diarization |
| `sargam` | `SARGAM_API_KEY` | Indic languages (Hindi, Tamil, Telugu, etc.) |
| `local` | None needed | Offline, free, runs on your machine |

> **Local provider** requires `pip install faster-whisper`. No API key, no internet. Runs on CPU (slower) or GPU (fast). Models download automatically on first use.

---

## ascli update

Update ascli to the latest version by pulling from git and reinstalling.

```bash
ascli update
```

### Flags

| Flag | Short | Description |
|------|-------|-------------|
| `--force` | `-f` | Update even if you have local changes (stashes them first) |
| `--check` | `-c` | Only check if an update is available, don't install |

### Examples

```bash
# Check for updates without installing
ascli update --check

# Update to latest
ascli update

# Force update (stashes any local changes)
ascli update --force
```

---

## ascli doctor

Run diagnostic checks on your system. Useful when something isn't working.

```bash
ascli doctor
```

**What it checks:**
1. System dependencies (Python, yt-dlp, ffmpeg, ffprobe)
2. Configuration files (config.yaml, .env, workspace)
3. Installation info (version, install type, repo path)
4. Available updates

> **Tip:** If you're reporting a bug or asking for help, run `ascli doctor` and include the output — it gives all the info needed to debug.

---

## ascli --version

Print the installed version.

```bash
ascli --version
# Output: ascli v0.3.0
```

---

## ascli --help

Show all available commands and global options.

```bash
ascli --help
```

Every command also has its own help:

```bash
ascli transcribe --help
ascli onboard --help
```

---

## Shell Completion

ascli supports tab-completion for bash, zsh, and fish. Install it once:

```bash
ascli --install-completion
```

After restarting your shell, you can press Tab to autocomplete commands and flags.
