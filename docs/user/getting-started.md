# Getting Started

## Prerequisites

- Python 3.10+
- [yt-dlp](https://github.com/yt-dlp/yt-dlp) installed and on PATH
- [ffmpeg](https://ffmpeg.org/) installed and on PATH
- An OpenAI API key (for Whisper transcription)

## Install

```bash
# Clone or navigate to the project
cd anyscribecli

# Create a virtual environment and install
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -e .
```

## First-Time Setup

Run the onboarding wizard:

```bash
ascli onboard
```

This will:
1. Create `~/.anyscribecli/` with your configuration
2. Prompt for your OpenAI API key
3. Set default preferences (provider, language, keep media)
4. Initialize an Obsidian vault at `~/.anyscribecli/workspace/`

## Your First Transcription

```bash
ascli transcribe https://www.youtube.com/watch?v=VIDEO_ID
```

This downloads the audio, transcribes it, and saves a formatted markdown file to your workspace.

## View in Obsidian

Open `~/.anyscribecli/workspace/` as an Obsidian vault. You'll see:
- `_index.md` — master index of all transcripts
- `sources/youtube/` — transcripts organized by date
- `daily/` — daily processing logs

## Next Steps

- See [Commands](commands.md) for the full command reference
- See [Configuration](configuration.md) for all settings options
