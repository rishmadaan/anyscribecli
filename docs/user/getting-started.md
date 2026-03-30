---
summary: Get ascli installed and transcribe your first video in about 5 minutes.
read_when:
  - First time setting up ascli
  - You want the fastest path to a working transcription
  - You're new to command-line tools
---

# Getting Started

Install ascli, run the setup wizard, and get your first transcript — all in about 5 minutes.

By the end of this guide you will have:
- ascli installed on your machine
- An Obsidian vault ready to browse your transcripts
- Your first video transcribed to markdown

## What you need

Before starting, you need:

- **A computer running macOS or Linux** (Windows via WSL2 works too)
- **An internet connection** (for downloading videos and calling the transcription API)
- **An API key** for your chosen provider — OpenAI is the default. Get one at [platform.openai.com/api-keys](https://platform.openai.com/api-keys). Whisper costs about $0.006/minute — a 10-minute video costs roughly 6 cents. Or use the **local** provider for free (no API key, runs on your machine).

> **New to the command line?** You'll be typing commands in your Terminal app (macOS) or terminal emulator (Linux). Every command in this guide starts with `ascli` — just copy-paste and press Enter.

## Step 1: Install Python

ascli needs Python 3.10 or newer. Check if you already have it:

```bash
python3 --version
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

> **Don't have Homebrew?** It's the standard package manager for macOS. Install it from [brew.sh](https://brew.sh).

## Step 2: Install ascli

```bash
pip install anyscribecli
```

Verify it worked:

```bash
ascli --version
```

You should see `ascli v0.3.1` (or a newer version).

> **Other install methods:** You can also use the [install script](https://raw.githubusercontent.com/rishmadaan/anyscribecli/main/install.sh) which checks and installs all dependencies for you, or [clone the repo](https://github.com/rishmadaan/anyscribecli) for development.

## Step 3: Run the setup wizard

```bash
ascli onboard
```

The wizard uses arrow-key selectors — navigate with **↑↓** and press **Enter** to select:

1. **Check your system** — makes sure `yt-dlp` and `ffmpeg` are installed. Offers to install missing ones.
2. **Choose your provider** — 5 options: OpenAI (default), OpenRouter, ElevenLabs, Sarvam AI, Local.
3. **Enter your API key** — stored locally at `~/.anyscribecli/.env`. Never sent anywhere except your provider.
4. **Add more provider keys** (optional) — configure multiple providers now or later.
5. **Configure Instagram** (optional) — username and password for downloading Instagram reels. A secondary account is recommended.
6. **Choose language** — auto-detect (default) or pick a specific language.
7. **Keep audio files** — whether to save the transcription audio to `~/.anyscribecli/media/audio/`.
8. **Post-transcription downloads** — whether ascli should offer to download the full video after each transcription (never/ask/always).
9. **Create workspace** — sets up your Obsidian vault at `~/.anyscribecli/workspace/`.

> **Re-run anytime:** `ascli onboard --force` to change settings. `ascli onboard --skip-deps` to skip the dependency check.

## Step 4: Transcribe your first video

Pick any YouTube video and run:

```bash
ascli transcribe "https://www.youtube.com/watch?v=VIDEO_ID"
```

Replace `VIDEO_ID` with a real video ID. A short video (under 5 minutes) is good for your first try.

> **Always wrap URLs in quotes** (`"..."`). Shells like zsh break URLs with `?` in them. Or run `ascli transcribe` with no URL and paste it when prompted — no quoting needed.

You'll see:

```
Transcription saved: ~/.anyscribecli/workspace/sources/youtube/2026-03-29/how-to-make-perfect-coffee.md
  Title:    How to Make Perfect Coffee
  Duration: 4:32
  Language: en
  Words:    847
```

### Also try

```bash
# Instagram reel
ascli transcribe "https://www.instagram.com/reel/SHORTCODE/"

# Just download, no transcription
ascli download "https://www.youtube.com/watch?v=VIDEO_ID"

# From clipboard (copy a URL first)
ascli transcribe --clipboard
```

## Step 5: Browse in Obsidian

Open Obsidian and select "Open folder as vault", then choose:

```
~/.anyscribecli/workspace/
```

> **Tip:** On macOS, press `Cmd+Shift+G` in the file picker and type `~/.anyscribecli/workspace/` to navigate to hidden folders.

You'll see:
- **`_index.md`** — a table of all your transcripts, newest first
- **`sources/youtube/`** and **`sources/instagram/`** — transcripts organized by platform and date
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

- **Transcribe more** — `ascli transcribe "url"` with any YouTube or Instagram link
- **Download video** — `ascli download "url"` to save video without transcribing
- **Batch process** — `ascli batch urls.txt` to transcribe a list of URLs
- **Switch providers** — `ascli config set provider elevenlabs`
- **Try JSON output** — `ascli transcribe "url" --json` for scripting
- **Check health** — `ascli doctor` verifies everything is working
- **Update** — `ascli update` pulls the latest version
- **View all commands** — `ascli --help`

## Troubleshooting

**"command not found: ascli"**
Your Python scripts directory may not be on your PATH. Try:
```bash
python3 -m pip show anyscribecli    # check it's installed
```
If installed but not found, add `~/.local/bin` (Linux) or the Python framework bin (macOS) to your PATH.

**"OPENAI_API_KEY not set"**
Run `ascli onboard --force` to re-enter your API key, or edit `~/.anyscribecli/.env` directly.

**"No matches found" when pasting a URL**
Your shell is interpreting `?` as a special character. Wrap the URL in quotes:
```bash
ascli transcribe "https://www.youtube.com/watch?v=VIDEO_ID"
```
Or run `ascli transcribe` without a URL and paste it at the prompt.

**"yt-dlp download failed"**
The video may be age-restricted, private, or geo-blocked. Try a different video. Update yt-dlp: `pip install --upgrade yt-dlp`.

**Instagram "login_required" errors**
Instagram rate-limits third-party access. Try again in a few minutes. Use a secondary account. Check credentials: `ascli config show`.

**Transcription in wrong language**
Force a specific language: `ascli transcribe "url" --language en` (or `es`, `fr`, `hi`, etc.)

**Large video taking too long**
Videos over ~30 minutes are chunked automatically. Each chunk is transcribed separately and merged. This is normal.

See [Commands](commands.md) for the full reference, [Configuration](configuration.md) for all settings, or [Providers](providers.md) for provider comparison.
