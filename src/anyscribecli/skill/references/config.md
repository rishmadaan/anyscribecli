# Configuration & Workspace

## File Locations

| File | Path | Purpose |
|------|------|---------|
| Workspace | `~/anyscribe/` | Obsidian vault — configurable via `workspace_path` |
| Config | `~/.anyscribecli/config.yaml` | Settings (no secrets) |
| Secrets | `~/.anyscribecli/.env` | API keys, passwords — **never display** |
| Downloads | `~/.anyscribecli/downloads/` | Downloaded audio/video files |
| Logs | `~/.anyscribecli/logs/` | Processing logs |
| Sessions | `~/.anyscribecli/sessions/` | Instagram login sessions |
| Temp | `~/.anyscribecli/tmp/` | Temporary downloads (auto-cleaned) |

## config.yaml Settings

```yaml
provider: openai          # openai | elevenlabs | sargam | openrouter | local
language: auto            # auto | ISO code (en, es, fr, hi, ar, zh, ja, ko...)
keep_media: false         # Keep audio files after transcription
output_format: clean      # clean | timestamped
prompt_download: never    # never | ask | always
local_file_media: skip    # skip | copy | move | ask
workspace_path: ""        # empty = ~/anyscribe (default), or custom path
instagram:
  username: ""
```

### Setting details

**provider** — Default transcription service. Override per-command with `--provider`.

**language** — Default audio language. `auto` lets the provider detect it. Set explicitly if detection is wrong. Override per-command with `--language`.

**keep_media** — When true, saves downloaded audio to `~/.anyscribecli/downloads/audio/<platform>/`. A 10-min video at 64kbps mono is ~5 MB.

**workspace_path** — Where transcripts are stored. Empty string (default) means `~/anyscribe/`. Set a custom path to use an existing Obsidian vault or preferred location. Check resolved path with `ascli config show`.

**output_format** — `clean` outputs paragraphs only. `timestamped` adds `[mm:ss]` markers per segment.

**prompt_download** — After each transcription: `never` (just transcribe), `ask` (prompt to download video/audio), `always` (auto-download video too).

**local_file_media** — When transcribing local files: `skip` (leave original), `copy` (duplicate to downloads dir), `move` (relocate to downloads dir), `ask` (prompt each time).

**instagram.username** — Instagram account for reel downloads. Password stored in `.env`.

## .env Variables

```bash
OPENAI_API_KEY=sk-proj-...
ELEVENLABS_API_KEY=xi-...
OPENROUTER_API_KEY=sk-or-...
SARGAM_API_KEY=...
INSTAGRAM_PASSWORD=...
OPENROUTER_MODEL=openai/gpt-4o-audio-preview   # Optional override
ASCLI_LOCAL_MODEL=base                           # Optional: tiny|base|small|medium|large-v3
```

## Workspace Structure

```
~/anyscribe/                                # Default (configurable)
├── .obsidian/                              # Obsidian config
├── _index.md                               # Master index (newest first)
├── sources/
│   ├── youtube/
│   │   └── video-title-slug.md
│   ├── instagram/
│   │   └── reel-title-slug.md
│   └── local/
│       └── file-name-slug.md
└── daily/
    └── YYYY-MM-DD.md                       # Daily processing log
```

**Organization:** Files grouped by platform. Slugs are lowercase, hyphenated, max 60 chars. Duplicate slugs get `-2`, `-3`, etc.

**Downloads are separate:** Audio/video files live in `~/.anyscribecli/downloads/`, not in the workspace. The vault stays lightweight — pure markdown. Use `ascli config show` to see the resolved workspace path.

## Transcript File Format

Each file has YAML frontmatter + markdown body:

```yaml
---
source: https://youtube.com/watch?v=...
platform: youtube
title: "Video Title"
duration: "12:34"
language: en
provider: openai
date_processed: 2026-03-26
word_count: 1500
reading_time: "8 min"
tags:
  - transcript
  - youtube
tldr: "Video Title"
---

# Video Title

**Channel:** Channel Name

**Source:** [youtube](https://youtube.com/watch?v=...)

**Duration:** 12:34 | **Words:** 1500 | **Reading time:** 8 min

---

## Transcript

The transcript text goes here...
```

## Viewing in Obsidian

Open Obsidian → "Open folder as vault" → `~/anyscribe/` (or the custom workspace path from `ascli config show`).

The default workspace is in the home directory — visible in Finder and file pickers without navigating to hidden folders.

The `_index.md` file is the entry point — a table of all transcripts sorted newest-first with links to each file.
