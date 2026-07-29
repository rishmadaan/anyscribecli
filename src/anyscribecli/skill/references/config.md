# Configuration & Workspace

## File Locations

| File | Path | Purpose |
|------|------|---------|
| Workspace | `~/anyscribe/` | Obsidian vault — configurable via `workspace_path` |
| Config | `~/.anyscribecli/config.yaml` | Settings (no secrets) |
| Secrets | `~/.anyscribecli/.env` | API keys, passwords — **never display** |
| Downloads | `~/.anyscribecli/downloads/` | Downloaded audio/video files |
| Logs | `~/.anyscribecli/logs/` | Processing logs |
| Temp | `~/.anyscribecli/tmp/` | Temporary downloads (auto-cleaned) |

## config.yaml Settings

```yaml
provider: openai          # used when quality is `custom`: openai | deepgram | elevenlabs | sargam | groq | openrouter | local
provider_models: {}       # provider -> pinned model id; missing key = that provider's default
extra_models: {}          # openrouter -> [user-added slugs], merged into the pickers
local_model: base         # offline Whisper size (local provider only)
quality: balanced         # accuracy | balanced | cost | free | custom — picks the provider
language: auto            # auto | ISO code (en, es, fr, hi, hi-Latn, ar, zh, ja, ko...)
keep_media: false         # Keep audio files after transcription
output_format: clean      # clean | timestamped | diarized
diarize: false            # Enable speaker diarization by default
prompt_download: never    # never | ask | always
local_file_media: skip    # skip | copy | move | ask
workspace_path: ""        # empty = ~/anyscribe (default), or custom path
instagram:
  browser: ""
```

### Setting details

**provider** — The transcription service used when `quality` is `custom`. It is also the fallback when a `quality` tier's key is missing. Override per-command with `--provider`.

> **The invariant:** setting `provider` anywhere — `scribe config set provider`, the Web UI Settings page, MCP `set_config` — writes `quality: custom` in the same save, so the choice sticks. Never set `quality: custom` as a separate step.
>
> To see which one is winning: `scribe config --json` → `resolved.via` is `config`, `quality: <tier>`, `flag`, or `diarize`.

> **Web UI parity:** every config key (including `prompt_download`, `local_file_media`, `keep_media`, `instagram.browser`) is editable at `scribe ui` → Settings; the page leads with a "Next run" banner mirroring `scribe config`. When a user asks "where do I change X in the UI", the answer is always Settings — nothing is terminal-only.

**provider_models** — A map of provider name → pinned model id. Each provider has its own entry, so switching providers keeps whatever model you chose for each one. A provider with no entry uses its built-in default (the first in its list). Set with `scribe config set provider_models.<provider> <model>`; override for a single run with `-m`.

```yaml
provider_models:
  openai: whisper-1             # forces Whisper on every run (the default is gpt-transcribe)
  groq: whisper-large-v3        # higher accuracy than the turbo default
  openrouter: google/gemini-2.5-flash
```

Invalid models are rejected at set time with the valid list (exit 1); `openrouter` accepts any audio-capable slug. `provider_models.local` is rejected — the local provider's model lives in `local_model` because it has a download/cache lifecycle. See [providers.md](providers.md) for each provider's models and their tradeoffs.

**extra_models** — User-added model ids merged into the pickers, **openrouter only**:

```bash
scribe config set extra_models.openrouter "qwen/qwen3-omni-flash,openai/gpt-audio"
scribe config set extra_models.openrouter ""      # empty value removes the entry
```

```yaml
extra_models:
  openrouter:
    - qwen/qwen3-omni-flash
```

`extra_models.<any other provider>` is rejected: *custom models are only supported for openrouter (curated lists elsewhere)*. Those catalogs ship with scribe releases because each model needs response-parsing code — the fix for "my provider added a model" is `scribe update`.

**local_model** — Which cached Whisper size the `local` provider loads: `tiny`, `base`, `small`, `medium`, `large-v3`, `large-v3-turbo`, `distil-large-v3.5`. Set by `scribe local setup --model <size>`; changing it with `scribe config set local_model <size>` requires the size to already be cached (`scribe model pull <size>` first).

**quality** — Accuracy↔cost preset that picks a provider: `accuracy`→ElevenLabs scribe_v2, `balanced`→Deepgram nova-3, `cost`→Groq, `free`→local, or `custom`→whatever `provider` says. Default `balanced`. Override per-command with `--quality`; `--provider` wins over it for that run.

If the tier's provider has no key, scribe emits `WARNING: quality '<tier>' wants <p> but no <ENV> is set — using <provider> instead` and runs on the configured provider. Relay the warning; don't treat it as a failure.

**language** — Default audio language. `auto` lets the provider detect it. Set explicitly if detection is wrong. Override per-command with `--language`.

**keep_media** — When true, saves downloaded audio to `~/.anyscribecli/downloads/audio/<platform>/`. A 10-min video at 64kbps mono is ~5 MB.

**workspace_path** — Where transcripts are stored. Empty string (default) means `~/anyscribe/`. Set a custom path to use an existing Obsidian vault or preferred location. Check resolved path with `scribe config show`.

**output_format** — `clean` outputs paragraphs only. `timestamped` adds `[mm:ss]` markers per segment. `diarized` groups consecutive speaker turns into blocks with timestamps.

**diarize** — When true, enables speaker diarization (identifying who said what). Supported by OpenAI, Deepgram, and Sarvam providers. Can also be enabled per-run with `--diarize` flag. When diarization is active and no provider is explicitly specified, scribe auto-switches to Deepgram if configured.

**prompt_download** — After each transcription: `never` (just transcribe), `ask` (prompt to download video/audio), `always` (auto-download video too).

**local_file_media** — When transcribing local files: `skip` (leave original), `copy` (duplicate to downloads dir), `move` (relocate to downloads dir), `ask` (prompt each time).

### `instagram.browser`

Browser to read Instagram cookies from. yt-dlp uses this when downloading reels.
Empty string means anonymous (no cookies). Many public reels work without
cookies; private reels and rate-limited fetches need this set.

Supported values: `firefox`, `chrome`, `safari`, `brave`, `edge`, `chromium`,
`vivaldi`, `opera`, or empty.

Example:

```bash
scribe config set instagram.browser firefox
```

> **Pre-0.8.3 users:** the older `instagram.username` field and the
> `INSTAGRAM_PASSWORD` entry in `.env` are no longer used. They're silently
> ignored on load and can be removed when convenient.

## .env Variables

```bash
OPENAI_API_KEY=sk-proj-...
DEEPGRAM_API_KEY=...
ELEVENLABS_API_KEY=xi-...
OPENROUTER_API_KEY=sk-or-...
SARGAM_API_KEY=...
GROQ_API_KEY=gsk-...
ASCLI_LOCAL_MODEL=base                   # Optional: tiny|base|small|medium|large-v3|large-v3-turbo|distil-large-v3.5
```

> `OPENROUTER_MODEL` was removed in 0.15.0 and is no longer read. Use
> `scribe config set provider_models.openrouter <slug>` and delete the line.

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

**Downloads are separate:** Audio/video files live in `~/.anyscribecli/downloads/`, not in the workspace. The vault stays lightweight — pure markdown. Use `scribe config show` to see the resolved workspace path.

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

Open Obsidian → "Open folder as vault" → `~/anyscribe/` (or the custom workspace path from `scribe config show`).

The default workspace is in the home directory — visible in Finder and file pickers without navigating to hidden folders.

The `_index.md` file is the entry point — a table of all transcripts sorted newest-first with links to each file.
