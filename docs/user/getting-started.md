---
summary: Get scribe installed and transcribe your first video in about 5 minutes.
read_when:
  - First time setting up scribe
  - You want the fastest path to a working transcription
  - You're new to command-line tools
---

# Getting Started

Install scribe, run the setup wizard, and get your first transcript — all in about 5 minutes.

By the end of this guide you will have:
- scribe installed on your machine
- An Obsidian vault ready to browse your transcripts
- Your first video transcribed to markdown

## What you need

Before starting, you need:

- **A computer running macOS, Linux, or Windows** (native Windows and WSL2 both work)
- **An internet connection** (for downloading videos and calling the transcription API)
- **An API key** for your chosen provider — OpenAI is the default. Get one at [platform.openai.com/api-keys](https://platform.openai.com/api-keys). Whisper costs about $0.006/minute — a 10-minute video costs roughly 6 cents. Or use the **local** provider for free (no API key, runs on your machine).

> **New to the command line?** You'll be typing commands in your Terminal app (macOS), terminal emulator (Linux), or Command Prompt / PowerShell (Windows). Every command in this guide starts with `scribe` — just copy-paste and press Enter.

## Step 1: Install Python

scribe needs Python 3.10 or newer. Check if you already have it:

```bash
python3 --version      # macOS / Linux
python --version       # Windows
```

You should see something like `Python 3.12.x`. If you get an error or a version below 3.10:

**macOS:**
```bash
brew install python@3.12
```

**Linux (Ubuntu/Debian):**
```bash
sudo apt install python3 python3-pip python3-venv
```

**Windows:**
Download from [python.org/downloads](https://www.python.org/downloads/) and run the installer. **Check "Add Python to PATH"** during installation.

> **Don't have Homebrew?** It's the standard package manager for macOS. Install it from [brew.sh](https://brew.sh).

## Step 2: Install scribe

```bash
pip install anyscribecli
```

Verify it worked:

**macOS / Linux:**
```bash
scribe --version
```

**Windows:**
```bash
python -m anyscribecli --version
```

You should see `scribe v0.6.0` (or a newer version).

> **Why `python -m` on Windows?** pip installs `scribe.exe` to a Scripts directory that's usually not on PATH. `python -m anyscribecli` always works because it uses the same Python you installed with. On first run, it will print the exact PowerShell command to add `scribe` to your PATH permanently — after that, you can use `scribe` directly.

> **Other install methods:** You can also use the [install script](https://raw.githubusercontent.com/rishmadaan/anyscribecli/main/install.sh) which checks and installs all dependencies for you, or [clone the repo](https://github.com/rishmadaan/anyscribecli) for development.

## Step 3: Run the setup wizard

```bash
scribe onboard                       # macOS / Linux
python -m anyscribecli onboard      # Windows (first time — prints PATH fix)
```

The wizard uses arrow-key selectors — navigate with **↑↓** and press **Enter** to select:

1. **Check your system** — makes sure `yt-dlp` and `ffmpeg` are installed. Offers to install missing ones.
2. **Choose your provider** — 5 options: OpenAI (default), OpenRouter, ElevenLabs, Sarvam AI, Local.
3. **Enter your API key** — stored locally at `~/.anyscribecli/.env`. Never sent anywhere except your provider.
4. **Add more provider keys** (optional) — configure multiple providers now or later.
5. **Configure Instagram** (optional) — username and password for downloading Instagram reels. A secondary account is recommended.
6. **Choose language** — auto-detect (default) or pick a specific language.
7. **Keep audio files** — whether to save the transcription audio to `~/.anyscribecli/downloads/audio/`.
8. **Local file handling** — what to do with original files when transcribing local audio/video (skip/copy/move/ask).
9. **Post-transcription downloads** — whether scribe should offer to download the full video after each transcription (never/ask/always).
10. **Choose workspace location** — where to store transcripts (default: `~/anyscribe/`).
11. **Create workspace** — sets up your Obsidian vault at the chosen location.

> **Re-run anytime:** `scribe onboard --force` to change settings — it shows your current config and lets you choose which parts to update. `scribe onboard --skip-deps` to skip the dependency check.

## Step 4: Transcribe your first video

Pick any YouTube video and run:

```bash
scribe "https://www.youtube.com/watch?v=VIDEO_ID"
```

Replace `VIDEO_ID` with a real video ID. A short video (under 5 minutes) is good for your first try.

> **No subcommand needed.** Just `scribe "url"` — it knows you want to transcribe. You can also write `scribe transcribe "url"` explicitly, but it's not required.

> **Always wrap URLs in quotes** (`"..."`). Shells like zsh break URLs with `?` in them. Or run `scribe` with no URL and paste it when prompted — no quoting needed.

You'll see:

```
Transcription saved: ~/anyscribe/sources/youtube/how-to-make-perfect-coffee.md
  Title:    How to Make Perfect Coffee
  Duration: 4:32
  Language: en
  Words:    847
```

### Also try

```bash
# Local audio/video file (mp3, mp4, m4a, wav, opus, ogg, flac, webm)
scribe /path/to/podcast.mp3

# Instagram reel
scribe "https://www.instagram.com/reel/SHORTCODE/"

# Just download, no transcription
scribe download "https://www.youtube.com/watch?v=VIDEO_ID"

# From clipboard (copy a URL first)
scribe --clipboard
```

## Step 5: Browse in Obsidian

Open Obsidian and select "Open folder as vault", then choose:

```
~/anyscribe/
```

> **Tip:** This folder is in your home directory — it shows up in Finder and file pickers by default. If you chose a custom workspace path during setup, use that path instead.

You'll see:
- **`_index.md`** — a table of all your transcripts, newest first
- **`sources/youtube/`**, **`sources/instagram/`**, and **`sources/local/`** — transcripts organized by source
- **`daily/`** — a log of what you transcribed each day

Each transcript has YAML properties that Obsidian can search and filter:

```yaml
title: "How to Make Perfect Coffee"
platform: youtube
duration: "4:32"
language: en
word_count: 847
reading_time: "4 min"
tags: [transcript, youtube]
```

## What to do next

- **Transcribe more** — `scribe "url"` with any YouTube or Instagram link, or `scribe /path/to/file.mp3` for local files
- **Download video** — `scribe download "url"` to save video without transcribing
- **Batch process** — `scribe batch urls.txt` to transcribe a list of URLs
- **Switch providers** — `scribe config set provider elevenlabs`
- **Try JSON output** — `scribe "url" --json` for scripting
- **Check health** — `scribe doctor` verifies everything is working
- **Update** — `scribe update` pulls the latest version
- **Claude Code** — skill auto-installs when Claude Code is detected. Run `scribe install-skill --force` to reinstall manually
- **MCP server** — `pip install anyscribecli[mcp]` for Claude Desktop, Cursor, and other AI harnesses
- **View all commands** — `scribe --help`

## Troubleshooting

**"command not found: scribe"** or **"scribe is not recognized"**
You can always use `python -m anyscribecli` as a drop-in replacement for `scribe`:
```bash
python -m anyscribecli onboard           # works exactly like: scribe onboard
python -m anyscribecli transcribe "..."  # works exactly like: scribe transcribe "..."
```

To make the `scribe` shortcut work, add your Python Scripts directory to PATH:
- **macOS**: add the Python framework bin directory to your PATH
- **Linux**: add `~/.local/bin` to your PATH
- **Windows** (PowerShell, run as admin):
  ```powershell
  # Find where pip installed scripts:
  python -c "import sysconfig; print(sysconfig.get_path('scripts'))"
  # Then add that path permanently (replace <path> with the output above):
  [Environment]::SetEnvironmentVariable('Path', [Environment]::GetEnvironmentVariable('Path', 'User') + ';<path>', 'User')
  ```
  Then restart your terminal.

**"OPENAI_API_KEY not set"**
Run `scribe onboard --force` to re-enter your API key, or edit `~/.anyscribecli/.env` directly.

**"No matches found" when pasting a URL**
Your shell is interpreting `?` as a special character. Wrap the URL in quotes:
```bash
scribe transcribe "https://www.youtube.com/watch?v=VIDEO_ID"
```
Or run `scribe transcribe` without a URL and paste it at the prompt.

**"yt-dlp download failed"**
scribe automatically updates yt-dlp if it's more than 60 days old (YouTube frequently changes formats, breaking older versions). If you still see this error, the video may be age-restricted, private, or geo-blocked. Try a different video, or manually update: `pip install --upgrade yt-dlp`.

**Instagram "login_required" errors**
Instagram rate-limits third-party access. Try again in a few minutes. Use a secondary account. Check credentials: `scribe config show`.

**Transcription in wrong language**
Force a specific language: `scribe transcribe "url" --language en` (or `es`, `fr`, `hi`, etc.)

**Large video taking too long**
Videos over ~30 minutes are chunked automatically. Each chunk is transcribed separately and merged. This is normal.

See [Commands](commands.md) for the full reference, [Configuration](configuration.md) for all settings, or [Providers](providers.md) for provider comparison.
