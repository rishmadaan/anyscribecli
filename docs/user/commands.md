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
| `ascli transcribe <url>` | Download and transcribe a video |
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
ascli transcribe <url>
```

### Flags

| Flag | Short | Description | Default |
|------|-------|-------------|---------|
| `--provider` | `-p` | Transcription provider to use | From config (openai) |
| `--language` | `-l` | Language code for transcription | `auto` (auto-detect) |
| `--json` | `-j` | Output result as JSON | Off |
| `--keep-media` | | Keep the downloaded audio file | From config (false) |
| `--quiet` | `-q` | No progress output (just the result) | Off |

### Examples

```bash
# Basic — transcribe a YouTube video
ascli transcribe https://www.youtube.com/watch?v=dQw4w9WgXcQ

# Specify language (skip auto-detection)
ascli transcribe https://youtube.com/watch?v=abc123 --language es

# Keep the audio file alongside the transcript
ascli transcribe https://youtube.com/watch?v=abc123 --keep-media

# Quiet mode — only print the file path
ascli transcribe https://youtube.com/watch?v=abc123 --quiet

# JSON output — for scripts, AI agents, or piping to other tools
ascli transcribe https://youtube.com/watch?v=abc123 --json
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
| Instagram | `instagram.com/reel/`, `instagram.com/p/` | Coming soon |

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
# Output: ascli v0.1.0
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
