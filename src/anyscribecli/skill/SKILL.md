---
name: scribe
description: >
  Use scribe (anyscribecli) to transcribe video/audio from YouTube, Instagram,
  or local files into markdown. Activate when the user wants to transcribe a URL
  or file, download media, configure transcription providers, manage their scribe
  setup, batch-process multiple URLs, or troubleshoot scribe issues.
allowed-tools: Bash(scribe *), Read
---

# scribe — Transcription CLI Operator Guide

You are an expert operator of `scribe` (anyscribecli), a CLI tool that transcribes video/audio into structured markdown files in an Obsidian vault.

## Before Running Any Command

**Pre-flight check** — on first use in a session, verify scribe is available:

```bash
scribe --version
```

If not installed: suggest `pip install anyscribecli`. If installed but not configured (no `~/.anyscribecli/config.yaml`): guide the user through `scribe onboard`.

**Windows note:** If `scribe` is not on PATH (common on Windows), use `python -m anyscribecli` instead of `scribe` for all commands. Example: `python -m anyscribecli "url" --json --quiet`.

## Core Principle: Use --json for Machine Output

When YOU run scribe commands, always use `--json --quiet` flags so you can parse structured output. Show the user a clean summary, not raw JSON.

```bash
scribe "URL" --json --quiet
```

Parse the JSON result and present it conversationally:
- On success: file path, title, duration, word count, provider used
- On failure: the error message in plain language, plus a fix

When the USER wants to run commands themselves, show them the human-readable form (no --json).

## Command Decision Tree

| User wants to... | Command |
|---|---|
| Transcribe a URL or local file | `scribe "url"` or `scribe /path/to/file` |
| Transcribe with speaker diarization | `scribe "url" --diarize` (auto-routes to Deepgram if configured) |
| Transcribe Hinglish to Latin script | `scribe "url" --diarize -p deepgram -l hi-Latn` |
| Transcribe multiple URLs | `scribe batch urls.txt` |
| Download video/audio only | `scribe download "url"` or `scribe download "url" --audio-only` |
| Change settings | `scribe config set <key> <value>` |
| See current config | `scribe config show` |
| Switch provider | `scribe config set provider <name>` |
| Test a provider | `scribe providers test <name>` |
| List providers | `scribe providers list` |
| Initial setup or reconfigure | `scribe onboard` (or `--force` to re-run) |
| Diagnose problems | `scribe doctor` |
| Update scribe | `scribe update` |
| Check for updates | `scribe update --check` |

For complete command syntax and all flags, read [references/commands.md](references/commands.md).

## URL Handling — Critical

**Always wrap URLs in double quotes** when passing to scribe. Shells interpret `?` and `&` as special characters:

```bash
# Correct
scribe "https://www.youtube.com/watch?v=abc123"

# Wrong — shell breaks the URL
scribe https://www.youtube.com/watch?v=abc123
```

## Supported Sources

| Source | URL patterns | Notes |
|---|---|---|
| YouTube | `youtube.com/watch?v=`, `youtu.be/`, `youtube.com/shorts/`, `youtube.com/live/` | No auth needed |
| Instagram | `instagram.com/reel/`, `instagram.com/p/` | Requires Instagram credentials in config |
| Local files | `.mp3`, `.mp4`, `.m4a`, `.wav`, `.opus`, `.ogg`, `.flac`, `.webm`, `.aac`, `.wma` | No download step |

## Provider Selection Guidance

When the user asks which provider to use, or when you need to suggest one:

| Scenario | Recommend | Why |
|---|---|---|
| General purpose, most languages | **openai** | Best balance of cost, accuracy, language coverage |
| Multi-speaker (meetings, interviews) | `--diarize` (auto-routes to **deepgram**) | Native diarization, fast, consistent speaker labels |
| Hinglish / Hindi-English calls | **deepgram** with `-l hi-Latn --diarize` | Romanized Hindi output, code-switching support |
| Indian languages (Hindi, Tamil, Telugu...) | **sargam** | Specialized for 22 Indian languages, much better than Whisper |
| Highest accuracy, word timestamps | **elevenlabs** | Word-level timestamps, 99 languages |
| Offline / no API key / free | **local** | Runs locally with faster-whisper, zero cost |
| Specific model needed | **openrouter** | Access to various models, but slower and pricier |

For detailed provider comparison (pricing, limits, setup), read [references/providers.md](references/providers.md).

## Handling Transcription Results

After a successful transcription:
1. Tell the user the file path
2. Offer to read the transcript: `Read the file at the output path`
3. Mention the word count and duration
4. If they use Obsidian, remind them to check their workspace location with `scribe config show`

## Batch Transcription

For multiple URLs, create a temporary file and use `scribe batch`:

```bash
# Write URLs to a temp file (one per line)
cat > /tmp/scribe-urls.txt << 'EOF'
https://youtube.com/watch?v=abc123
https://youtube.com/watch?v=def456
EOF

scribe batch /tmp/scribe-urls.txt --json --quiet
```

## Troubleshooting

When something goes wrong:

1. **First:** Run `scribe doctor` to get system diagnostics
2. **Check** the error message — most are self-explanatory
3. **Common fixes:** Read [references/troubleshooting.md](references/troubleshooting.md)

## Safety Rules

1. **Never read or display `~/.anyscribecli/.env`** — it contains API keys and passwords
2. **Use `scribe config show`** to display settings (it masks sensitive values)
3. **Never hardcode API keys** in commands or output
4. **Don't run `scribe onboard`** without telling the user first — it's interactive and takes control of the terminal
5. **Warn before `scribe update`** — it modifies the installed package

## Configuration

App config lives at `~/.anyscribecli/`. Transcripts default to `~/anyscribe/` (configurable). For details on all settings, file locations, and workspace structure, read [references/config.md](references/config.md).

Quick config changes:
```bash
scribe config set provider elevenlabs    # Switch provider
scribe config set language hi            # Set default language
scribe config set keep_media true        # Keep audio files
scribe config set deepgram_api_key KEY   # Set API key (stored in .env)
```

## What scribe Outputs

Each transcription creates a markdown file with YAML frontmatter (title, source URL, duration, language, word count, reading time, tags) followed by the transcript text. Files are organized by source platform and date:

```
~/anyscribe/sources/<platform>/YYYY-MM-DD/<slug>.md
```

An `_index.md` file is auto-updated with links to all transcripts. Daily logs are written to `daily/YYYY-MM-DD.md`.
