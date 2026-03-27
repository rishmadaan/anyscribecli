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
- Your first YouTube video transcribed to markdown

## What you need

Before starting, you need:

- **A computer running macOS or Linux** (Windows via WSL2 works too)
- **An internet connection** (for downloading videos and calling the transcription API)
- **An OpenAI API key** — get one at [platform.openai.com/api-keys](https://platform.openai.com/api-keys). You'll need to add a payment method, but Whisper transcription costs about $0.006/minute — a 10-minute video costs roughly 6 cents.

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

**Easiest way** — one command that handles everything:

```bash
curl -fsSL https://raw.githubusercontent.com/rishmadaan/anyscribecli/main/install.sh | bash
```

This checks your system, installs missing dependencies, installs ascli, and runs the setup wizard. If it works, you can skip to Step 4.

**Or install manually with pip:**

```bash
pip install git+https://github.com/rishmadaan/anyscribecli.git
```

**Or clone the source** (if you want to modify the code):

```bash
git clone https://github.com/rishmadaan/anyscribecli.git
cd anyscribecli
pip install -e .
```

Verify it worked:

```bash
ascli --version
```

You should see `ascli v0.2.0` (or a newer version).

> **What's the difference?** `pip install git+...` installs a packaged copy — clean, no source code on disk. `pip install -e .` is for developers — it links to the source so you can edit code and see changes immediately. Both create the same `ascli` command.

## Step 3: Run the setup wizard

```bash
ascli onboard
```

The wizard will:

1. **Check your system** — makes sure `yt-dlp` and `ffmpeg` are installed. If they're missing, it offers to install them for you.
2. **Choose your provider** — use arrow keys to select from 5 transcription providers (OpenAI is the default).
3. **Enter your API key** — stored locally at `~/.anyscribecli/.env` and never sent anywhere except your chosen provider.
4. **Configure Instagram** (optional) — provide credentials if you want to transcribe Instagram reels.
5. **Set preferences** — language (auto-detect by default), whether to keep audio files.
6. **Create your workspace** — an Obsidian vault at `~/.anyscribecli/workspace/`.

> **Already have everything installed?** You can skip the dependency check with `ascli onboard --skip-deps`.

## Step 4: Transcribe your first video

Pick any YouTube video and run:

```bash
ascli transcribe "https://www.youtube.com/watch?v=VIDEO_ID"
```

Replace `VIDEO_ID` with a real video ID. A short video (under 5 minutes) is good for your first try.

> **Important:** Always wrap the URL in quotes (`"..."`). Without quotes, your shell may break the URL. Or just run `ascli transcribe` with no URL and paste it when prompted.

You'll see progress output like:

```
Downloading audio...
  Downloaded: How to Make Perfect Coffee
Transcribing with openai...
  Done: 847 words, language=en
Writing to vault...
  Saved: ~/.anyscribecli/workspace/sources/youtube/2026-03-26/how-to-make-perfect-coffee.md
```

## Step 5: Browse in Obsidian

Open Obsidian and select "Open folder as vault", then choose:

```
~/.anyscribecli/workspace/
```

> **Tip:** On macOS, press `Cmd+Shift+G` in the file picker and type `~/.anyscribecli/workspace/` to navigate to hidden folders.

You'll see:
- **`_index.md`** — a table of all your transcripts, newest first
- **`sources/youtube/`** — your transcripts organized by date
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

- **Transcribe more videos** — just run `ascli transcribe <url>` with any YouTube link
- **Try JSON output** — `ascli transcribe <url> --json` gives machine-readable output for scripting
- **Check your setup** — `ascli doctor` verifies everything is healthy
- **Update ascli** — `ascli update` pulls the latest version

## Troubleshooting

**"command not found: ascli"**
Make sure you installed with `pip install -e .` and that your Python scripts directory is on your PATH. Try running `python3 -m anyscribecli.cli.main --help` as a workaround.

**"OPENAI_API_KEY not set"**
Run `ascli onboard --force` to re-enter your API key, or manually edit `~/.anyscribecli/.env`.

**"yt-dlp download failed"**
The video may be age-restricted, private, or geo-blocked. Try a different video. You can also update yt-dlp: `brew upgrade yt-dlp` or `pip install --upgrade yt-dlp`.

**Transcription seems wrong or in the wrong language**
Force a specific language: `ascli transcribe <url> --language en` (or `es`, `fr`, `hi`, etc.)

**Large video taking too long**
Videos over ~30 minutes are split into chunks automatically. This is normal — each chunk is transcribed separately and merged. The Whisper API has a 25MB file limit, so chunking is necessary.

See [Commands](commands.md) for the full reference, or [Configuration](configuration.md) for all settings.
