---
summary: Complete reference for all anyscribe commands, flags, and options.
read_when:
  - You want to know what flags are available
  - You need the exact syntax for a command
  - You're scripting or automating with anyscribe
---

# Command Reference

Every anyscribe command. Copy-paste friendly.

> **Agentic-first CLI.** anyscribe's CLI is designed to be usable by AI agents, CI jobs, and scripts — not just humans. Consequential commands follow the same contract:
>
> - **`--json` on every command** — machine-parseable output; agents parse this, humans ignore it.
> - **`--yes` for non-interactive runs** — commands that would normally prompt for confirmation refuse to run without `--yes` when there's no TTY (i.e., when invoked from an agent or script).
> - **No silent defaults for choices agents might make** — e.g., `anyscribe local setup` requires `--model` explicitly; the CLI never picks a size on your behalf. The recommended value is documented so agents know what to pass.
> - **Structured exit codes** — `0` success, `1` operational failure, `2` usage error. Stderr on exit 2 carries a JSON payload with the missing field(s).
> - **Prefer env vars for secrets** — passing `--api-key` on argv leaks to shell history; set `$OPENAI_API_KEY` etc. in the environment instead.
>
> Humans running anyscribe interactively can mostly ignore these rules — the defaults are friendly without flags. They're called out here so script authors and agent skills know what to expect.

## Quick Overview

| Command | What it does |
|---------|-------------|
| `anyscribe "<url or file>"` | Transcribe a URL or local file (default action) |
| `anyscribe onboard` | First-time setup wizard (interactive TUI) |
| `anyscribe onboard --yes --provider X ...` | Headless setup (for agents / scripts) |
| `anyscribe download "<url>"` | Download video or audio only (no transcription) |
| `anyscribe batch <file>` | Batch transcribe URLs or file paths from a file |
| `anyscribe rm <path-or-slug>` | Delete a transcript and update the index |
| `anyscribe logs` | View recent transcription activity + recovery artifacts |
| `anyscribe config` | Dashboard: what the next run will use, and every provider's model |
| `anyscribe config show` | View current settings |
| `anyscribe config set <key> <value>` | Change a setting |
| `anyscribe config set provider_models.<provider> <model>` | Pin which model a provider uses |
| `anyscribe config set extra_models.openrouter <slugs>` | Add your own OpenRouter models to the pickers |
| `anyscribe config path` | Print config file location |
| `anyscribe providers list` | Show available providers |
| `anyscribe providers test [name]` | Test a provider's API key |
| `anyscribe local setup --model <size>` | Install faster-whisper + download a Whisper model |
| `anyscribe local status` | Report local-transcription readiness |
| `anyscribe local teardown --yes` | Uninstall faster-whisper + delete all cached models |
| `anyscribe model list` | List Whisper models with cache status |
| `anyscribe model pull <size>` | Download an additional Whisper model |
| `anyscribe model rm <size> --yes` | Delete a cached Whisper model |
| `anyscribe model reinstall <size> --yes` | Delete + re-download in one step (for corrupted weights) |
| `anyscribe model info <size>` | Inspect a single Whisper model |
| `anyscribe ui` | Launch the web UI in your browser |
| `anyscribe tray` | Menu-bar icon that supervises the web server (needs the `[tray]` extra) |
| `anyscribe install-service` | Auto-start the tray at login (macOS only) |
| `anyscribe uninstall-service` | Remove the login auto-start |
| `anyscribe install-skill` | Install/update Claude Code skill |
| `anyscribe update` | Update to the latest version |
| `anyscribe migrate` | One-time move from an old `anyscribecli` install (run once after upgrading) |
| `anyscribe doctor` | Check system health |
| `anyscribe --version` | Show version |
| `anyscribe --help` | Show help |

---

## anyscribe onboard

Interactive setup wizard. Run this once after installing, or again to change settings.

```bash
anyscribe onboard
```

> **Prefer clicking to typing?** `anyscribe ui` opens the Web UI with the same onboarding flow as a modal wizard. Both paths set up the same config — pick whichever feels faster. See [getting-started.md](getting-started.md) for the Web UI walk-through.

**What the TUI does** (arrow-key selectors throughout):
1. Checks system dependencies (Python, yt-dlp, ffmpeg) — offers to install missing ones
2. Choose transcription provider (7 options, arrow keys)
3. Choose that provider's model, if it has more than one (defaults to the first — press Enter to accept)
4. Enter API key for your chosen provider
5. Optionally add API keys for other providers
6. Optionally configure Instagram browser (for cookie-based downloads)
7. Choose default language (arrow-key selector with common options)
8. Choose whether to keep audio files after transcription
9. Choose post-transcription download behavior (never/ask/always)
10. Choose workspace location (default: `~/anyscribe/`)
11. Creates your Obsidian workspace

### Headless mode (for agents + scripts)

Pass `--yes` with the settings you want and skip the interactive flow entirely. Required for automation and CI — arrow-key TUIs don't work without a tty.

```bash
anyscribe onboard \
  --provider openai \
  --api-key "$OPENAI_API_KEY" \
  --yes --json
```

Add `--model` to pin a model and `--quality` to pick a tier instead of a fixed provider:

```bash
anyscribe onboard --provider openai --model whisper-1 --yes --json
anyscribe onboard --provider deepgram --quality balanced --yes --json
```

The JSON result reports what was written, including the effective model:

```json
{"status": "onboarded", "provider": "openai", "quality": "custom", "model": "whisper-1", "...": "..."}
```

For offline/local transcription as the primary provider:

```bash
anyscribe onboard \
  --provider local \
  --local-model base \
  --yes --json
```

| Flag | Required with `--yes` | Default | Description |
|------|-----------------------|---------|-------------|
| `--yes` / `-y` | yes | off | Opt into headless mode. Without this, `anyscribe onboard` runs the interactive TUI. |
| `--provider` / `-p` | **yes** | none | One of `openai`, `deepgram`, `elevenlabs`, `sargam`, `groq`, `openrouter`, `local`. |
| `--api-key` | for API providers (or use env var) | none | Stored in `~/.anyscribe/.env`. Prefer setting the env var (e.g. `OPENAI_API_KEY`) to avoid leaking keys into shell history. |
| `--local-model` | **yes when `--provider=local`** | none | Whisper size. Recommended: `base`. |
| `--model` / `-m` | no | provider's default | Pin the model for `--provider` (written to `provider_models`). Rejected with the valid list if the provider doesn't offer it. Not for `local` — use `--local-model`. |
| `--quality` | no | `custom` | `accuracy`, `balanced`, `cost`, `free`, or `custom`. Omit it and onboarding writes `custom`, so the provider you just chose is the one that runs. |
| `--workspace` | no | `~/anyscribe` | Absolute path to the Obsidian vault. |
| `--language` | no | `auto` | Default language code. |
| `--keep-media` / `--no-keep-media` | no | `--no-keep-media` | Keep downloaded audio after transcription. |
| `--output-format` | no | `clean` | `clean`, `timestamped`, or `diarized`. |
| `--instagram-browser` | no | — | Browser to read Instagram cookies from (`firefox`, `chrome`, `safari`, etc.). Only needed for rate-limited or private reels. |
| `--force` / `-f` | no | off | Re-run over existing config. Required if `config.yaml` already exists. |
| `--json` / `-j` | no | off | Emit the result as a single JSON object on stdout. |

**Exit codes:** 0 success · 1 setup failure (e.g., local install failed) · 2 usage error (missing `--provider`, already configured without `--force`, etc.). On exit 2 stderr carries a structured JSON error with the missing field or the reason.

### Flags

| Flag | Description |
|------|-------------|
| `--force`, `-f` | Re-run setup even if already configured |
| `--skip-deps` | Skip the dependency check |

### Examples

```bash
# First-time setup
anyscribe onboard

# Re-run to change settings (e.g., switch provider or update API key)
anyscribe onboard --force

# Skip dependency check (you know they're installed)
anyscribe onboard --force --skip-deps
```

---

## anyscribe (default: transcribe)

The main command. Transcribes a URL or local audio/video file and saves a formatted markdown file. **A bare URL routes to transcribe automatically — no subcommand needed.**

```bash
anyscribe "<url>"                          # bare URL — just works
anyscribe /path/to/file.mp3               # local file — just works
anyscribe transcribe "<url>"              # explicit subcommand (also works)
```

> **Important:** Always wrap URLs in quotes. Shells like zsh treat `?` as a special character, which breaks unquoted YouTube URLs. Local file paths don't need quotes.

### Ways to provide input

```bash
# 1. Pass a URL as an argument (always use quotes)
anyscribe "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

# 2. Pass a local audio/video file
anyscribe /path/to/podcast.mp3
anyscribe ~/recordings/meeting.m4a

# 3. Run without input — you'll be prompted to paste a URL or file path
anyscribe transcribe

# 4. Copy a URL to your clipboard, then:
anyscribe --clipboard
```

### Flags

| Flag | Short | Description | Default |
|------|-------|-------------|---------|
| `--quality` | | Quality preset: `accuracy` \| `balanced` \| `cost` \| `free` (picks a provider) | From config (balanced) |
| `--provider` | `-p` | Explicit provider — overrides `--quality` | From config |
| `--model` | `-m` | Specific model to use within that provider | The provider's default |
| `--language` | `-l` | Language code for transcription | `auto` (auto-detect) |
| `--json` | `-j` | Output result as JSON | Off |
| `--keep-media` | | Keep the downloaded audio file | From config (false) |
| `--diarize` | `-d` | Enable speaker diarization (auto-routes to Deepgram if configured) | Off |
| `--force` | `-f` | Re-transcribe even if this source was already transcribed | Off |
| `--quiet` | `-q` | No progress output (just the result) | Off |
| `--clipboard` | `-c` | Read URL from system clipboard | Off |

### Choosing a model (`--model`)

A **provider** is the service that does the transcribing (OpenAI, Deepgram, Groq...). A **model** is the specific engine inside that service. Each provider has a default model that anyscribe uses unless you say otherwise — you can ignore this entirely and everything still works.

Use `--model` (short: `-m`) when you want a different one for a single run:

```bash
# OpenAI's newer model — cheaper and more accurate than the default
anyscribe "https://youtube.com/watch?v=abc123" -p openai -m gpt-transcribe

# Groq's more accurate (slightly slower) model
anyscribe "https://youtube.com/watch?v=abc123" -p groq -m whisper-large-v3
```

To see what's available, run:

```bash
anyscribe config            # or: anyscribe providers list
```

That prints every provider, the model it's currently using, and the other models you can pick.

> **Want it every time?** `--model` only affects the one run. To make it stick, see [`anyscribe config set provider_models`](#pinning-a-model-per-provider) below.

> **Heads up on timestamps.** OpenAI's `gpt-transcribe` (the default), `gpt-4o-transcribe`, and `gpt-4o-mini-transcribe` don't return timestamps. When your output format is `timestamped` or `diarized`, anyscribe switches the run to `whisper-1` for you and prints `switched to whisper-1 — gpt-transcribe can't produce timestamps`. Passing `-m gpt-transcribe` yourself turns that off — an explicit model is always honoured, paragraphs and all. See [providers.md](providers.md) for the full picture.

### The line above your transcript

Every run prints one line naming what it's about to use:

```
→ deepgram · nova-3 (quality: balanced)
```

- **provider · model** — exactly what will be called.
- **(reason)** — `flag` (you passed `--provider`), `diarize` (auto-routed for speaker labels), `quality: <tier>`, or `config` (your `provider` setting).

Anything anyscribe decided on your behalf is printed underneath, indented:

```
→ openai · whisper-1 (config)
    WARNING: quality 'balanced' wants deepgram but no DEEPGRAM_API_KEY is set — using openai instead
    switched to whisper-1 — gpt-transcribe can't produce timestamps
```

The line goes to stderr, so it never mixes into `--json` output — and `--quiet` hides it.

> **The `local` provider is different.** Its models are downloaded to your machine, so you pick them with `anyscribe local setup --model <size>` and `anyscribe model pull <size>`, not with `-m`.

> **Already transcribed something? anyscribe won't do it twice.** Before transcribing, anyscribe checks your vault for a transcript of the same URL or file (it matches the `source:` line in each note's frontmatter — the metadata block at the top). If it finds one, it hands you back that existing file instead of spending time and API credits re-transcribing. You'll see `Already transcribed: <path> — use --force to re-transcribe.` To force a fresh transcription anyway (say you switched providers, or the video was re-uploaded), add `--force`.

### Examples

```bash
# YouTube video (always quote the URL)
anyscribe "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

# Instagram reel
anyscribe "https://www.instagram.com/reel/C17LiBLyIOe/"

# Local audio/video file
anyscribe /path/to/podcast.mp3
anyscribe ~/recordings/meeting.m4a
anyscribe ./interview.opus

# Interactive — paste URL or file path when prompted
anyscribe transcribe

# Pick a quality tier — balanced (default), accuracy, cost, or free
anyscribe "https://youtube.com/watch?v=abc123" --quality accuracy  # highest accuracy
anyscribe "https://youtube.com/watch?v=abc123" --quality cost      # cheapest (Groq)

# From clipboard
anyscribe --clipboard

# Re-transcribe a source that's already in your vault (skip the "already transcribed" shortcut)
anyscribe "https://youtube.com/watch?v=abc123" --force

# Specify language (skip auto-detection)
anyscribe "https://youtube.com/watch?v=abc123" --language es

# Keep the audio file alongside the transcript
anyscribe "https://youtube.com/watch?v=abc123" --keep-media

# Enable speaker diarization (auto-switches to Deepgram if configured)
# Deepgram auto-detects the number of speakers — no need to specify a count
anyscribe "https://youtube.com/watch?v=abc123" --diarize

# Diarize with a specific provider (overrides auto-routing)
anyscribe "https://youtube.com/watch?v=abc123" --diarize --provider openai

# Diarize a mostly-Hindi or Hinglish recording (romanized Latin script output)
anyscribe "https://youtube.com/watch?v=abc123" --diarize --language hi-Latn

# JSON output — for scripts, AI agents, or piping to other tools
anyscribe "https://youtube.com/watch?v=abc123" --json
```

### JSON Output

When you use `--json`, anyscribe prints structured JSON to stdout (progress goes to stderr):

```json
{
  "success": true,
  "file": "/Users/you/anyscribe/sources/youtube/video-title.md",
  "title": "Video Title",
  "platform": "youtube",
  "duration": "12:34",
  "language": "en",
  "word_count": 1500,
  "provider": "openai",
  "model": "gpt-transcribe",
  "cached": false
}
```

> **The `model` field** tells you which model actually ran — useful when anyscribe switched it for you (e.g. back to `whisper-1` for timestamps).

> **The `cached` field:** `false` means anyscribe transcribed the source just now. `true` means the source was already in your vault and anyscribe returned the existing file (`file` points at it) instead of re-transcribing. Add `--force` to make it transcribe fresh.

On error:

```json
{
  "success": false,
  "error": "yt-dlp download failed: Video unavailable"
}
```

> **Scripting tip:** Use `--json --quiet` together to get clean JSON with no extra output. Pipe to `jq` for filtering: `anyscribe "url" --json -q | jq '.file'`

### Speaker Diarization

The `--diarize` flag enables multi-speaker transcription — anyscribe identifies who said what and labels each turn.

**How it works:**
- **Automatic speaker detection** — the number of speakers is detected automatically from audio characteristics (pitch, tone, cadence). You never need to specify how many speakers are in the recording.
- **Speaker labels** — each speaker gets a label (`Speaker 0`, `Speaker 1`, `Speaker 2`, etc.) assigned in the order they first appear.
- **Auto-routing to Deepgram** — when `--diarize` is used without `-p`, anyscribe automatically switches to Deepgram if a Deepgram API key is configured. Deepgram handles files of any size natively and produces consistent speaker labels. Override with `-p openai` if needed.
- **No file size limit with Deepgram** — unlike OpenAI (25MB limit for diarization), Deepgram processes the full audio in one shot regardless of length.

**Language and diarization:**
- **Auto-detect (default)** — works well for English and English-with-some-Hindi conversations. Use this for most meetings.
- **`--language hi-Latn`** — use when the conversation is predominantly Hindi or Hinglish. Outputs romanized Hindi in Latin script instead of Devanagari. Deepgram handles code-switching (Hindi-English mixing) well in this mode.
- **Auto-detect vs `hi-Latn`** — if the meeting is mostly English with some Hindi words sprinkled in, auto-detect is fine. If it's mostly Hindi with some English, use `hi-Latn`.

**Output format:** Each speaker turn is a separate block with the speaker label and timestamp:

```markdown
**Speaker 0** *[0:00]*: Welcome everyone to the meeting...

**Speaker 1** *[0:15]*: Thanks for having me. So about the project...

**Speaker 0** *[0:30]*: Right, let's dive in.
```

**Quick setup:**
```bash
# 1. Add your Deepgram key (free $200 credit on signup at console.deepgram.com)
anyscribe config set deepgram_api_key YOUR_KEY

# 2. Transcribe with speakers
anyscribe "url" --diarize                        # English / auto-detect
anyscribe "url" --diarize --language hi-Latn     # Hindi / Hinglish
```

### Supported Inputs

| Source | Patterns | Status |
|--------|----------|--------|
| YouTube | `youtube.com/watch?v=`, `youtu.be/`, `youtube.com/shorts/`, `youtube.com/live/` | Working |
| Instagram | `instagram.com/reel/`, `instagram.com/p/` | Working (public reels out of the box; set `instagram.browser` for rate-limited or private reels) |
| Local files | `.mp3`, `.mp4`, `.m4a`, `.wav`, `.opus`, `.ogg`, `.flac`, `.webm`, `.aac`, `.wma` | Working |

---

## anyscribe batch

Transcribe multiple URLs or local files from a list. One entry per line, blank lines and `#comments` are skipped.

```bash
anyscribe batch urls.txt
```

### Flags

| Flag | Short | Description | Default |
|------|-------|-------------|---------|
| `--quality` | | Quality preset: `accuracy` \| `balanced` \| `cost` \| `free` | From config |
| `--provider` | `-p` | Override provider (wins over `--quality`) | From config |
| `--model` | `-m` | Specific model within that provider, applied to every URL in the batch | The provider's default |
| `--language` | `-l` | Override language | `auto` |
| `--json` | `-j` | Output results as JSON | Off |
| `--keep-media` | | Keep audio files | From config |
| `--diarize` | `-d` | Enable speaker diarization | Off |
| `--force` | `-f` | Re-transcribe sources already in your vault | Off |
| `--quiet` | `-q` | Suppress progress | Off |
| `--stop-on-error` | | Stop at first failure | Off (continues) |
| `--timeout` | | Per-URL timeout in seconds. A URL that runs longer is marked failed (`"timed out after Ns"`) and the batch moves on to the next one | None (no timeout) |

> **Duplicate detection applies here too.** Any source already in your vault is skipped and returned from the existing file — the summary table marks those rows `CACHED` and each such result carries `"cached": true`. This makes it safe to re-run a batch file: only the new entries are actually transcribed. Pass `--force` to re-transcribe everything.

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
anyscribe batch urls.txt

# Stop if any fail
anyscribe batch urls.txt --stop-on-error

# JSON output for scripting
anyscribe batch urls.txt --json

# Cap each URL at 5 minutes — slow ones fail and the batch keeps going
anyscribe batch urls.txt --timeout 300

# Run the whole batch on a cheaper model
anyscribe batch urls.txt -p openai -m gpt-4o-mini-transcribe
```

> **A timed-out URL doesn't stop cleanly mid-download or mid-transcription** — anyscribe can't kill that work outright, so it abandons it and moves on. This is fine for a normal batch run; just know the timed-out attempt may still be using network/API resources briefly in the background.

---

## anyscribe rm

Delete a transcript from your vault and remove its row from the master index (`_index.md`). Use this to clean up a transcript you no longer want — or to clear the way before re-transcribing a source from scratch.

```bash
anyscribe rm "sources/youtube/my-video.md"    # by file path
anyscribe rm my-video                          # by slug
```

> **What's a "slug"?** The slug is a transcript's filename without the `.md` extension — the short, dash-separated name anyscribe generates from the title. For a file at `sources/youtube/my-video.md`, the slug is `my-video`. You can pass either the full path or just the slug.

If a slug matches more than one transcript (same title from different platforms, say), anyscribe lists the matches and stops without deleting anything — re-run with the full path to pick one.

> **What gets deleted:** only the transcript file itself and its entry in `_index.md`. Your **daily logs** (`daily/YYYY-MM-DD.md`) are left alone — they're a historical record of what you transcribed each day, so anyscribe keeps them intact.

### Flags

| Flag | Short | Description | Default |
|------|-------|-------------|---------|
| `--yes` | `-y` | Skip the "Delete …?" confirmation prompt | Off (prompts) |
| `--json` | `-j` | Output the result as JSON | Off |

### Examples

```bash
# Delete by path (you'll be asked to confirm)
anyscribe rm "sources/youtube/my-video.md"

# Delete by slug, no confirmation prompt
anyscribe rm my-video --yes

# JSON output (for scripts)
anyscribe rm my-video --yes --json
```

### JSON Output

```json
{ "success": true, "data": { "deleted": "sources/youtube/my-video.md" }, "error": null }
```

If nothing matches, the slug is ambiguous, or the file can't be deleted, `success` is `false`, `error` explains why, and the command exits with code 1.

---

## anyscribe logs

See what you've transcribed recently, and check for any leftover audio from failed runs.

```bash
anyscribe logs                # last 20 entries, newest first
anyscribe logs --limit 50     # more entries
```

This reads straight from your workspace's `daily/YYYY-MM-DD.md` logs — the same
files you can open in Obsidian — so there's nothing extra to keep in sync. It
also lists **recovery artifacts**: if a transcription downloaded audio but then
failed before finishing, anyscribe keeps that audio around instead of throwing it
away, so you don't have to re-download it. Those show up in a separate section
of the output.

> **Empty vault?** You'll see `No activity logged yet.` — that's normal for a fresh install.

### Flags

| Flag | Short | Description | Default |
|------|-------|-------------|---------|
| `--limit` | `-n` | Number of log entries to show | `20` |
| `--json` | `-j` | Output result as JSON | Off |

### Examples

```bash
# Quick check on today's activity
anyscribe logs --limit 5

# JSON for scripting or piping to jq
anyscribe logs --json --limit 100
```

### JSON Output

```json
{
  "success": true,
  "data": {
    "entries": [
      {
        "date": "2026-07-04",
        "time": "09:12",
        "platform": "youtube",
        "entry": "[[sources/youtube/video-title.md|Video Title]]",
        "duration": "12:34"
      }
    ],
    "recovery": [
      { "name": "youtube/abc123.mp3", "size": 4821932, "mtime": "2026-07-03T22:14:01" }
    ]
  },
  "error": null
}
```

---

## anyscribe download

Download video or audio from a URL — no transcription. Useful when you just want the file.

```bash
anyscribe download "<url>"
```

Saves to `~/.anyscribe/downloads/video/<platform>/` (default) or `~/.anyscribe/downloads/audio/<platform>/` with `--audio-only`.

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
anyscribe download "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

# Download audio only (no video)
anyscribe download "https://www.youtube.com/watch?v=dQw4w9WgXcQ" --audio-only

# From clipboard
anyscribe download --clipboard

# Interactive (paste URL when prompted)
anyscribe download

# JSON output
anyscribe download "https://youtube.com/watch?v=abc123" --json
```

---

## anyscribe config

View and change settings.

```bash
anyscribe config                # dashboard: what runs next + every provider's model
anyscribe config show           # display all settings
anyscribe config set key value  # change a setting
anyscribe config path           # print config file location
anyscribe config list-keys      # every settable key with its current value
```

### The defaults dashboard

Run `anyscribe config` with no subcommand to see, in one screen, what your next
transcription will use and what else you could switch to:

```
Next run: deepgram · nova-3 (quality: balanced)

Provider      Default model           Alternatives      Key      Notes
→ deepgram    nova-3                  nova-2            ✓        balanced
  elevenlabs  scribe_v2                                 missing  accuracy
  groq        whisper-large-v3-turbo  whisper-large-v3  missing  cost
  local       —                                         —        free, local_model: base
  openai      gpt-transcribe          3 more            missing
  openrouter  openai/gpt-audio-mini   5 more            missing
  sargam      saaras:v3                                 missing

Missing keys:    elevenlabs, groq, openai, openrouter, sargam  (anyscribe config set <provider>_api_key <key>)
Change provider: anyscribe config set provider <name>  (also sets quality = custom, so it sticks)
Pin a model:     anyscribe config set provider_models.<provider> <model>
Or pick a tier:  anyscribe config set quality accuracy|balanced|cost|free|custom
```

How to read it:

| Part | Meaning |
|------|---------|
| **Next run** | The provider and model that will actually be used, and why — `config`, `quality: <tier>`, `flag`, or `diarize` |
| Indented lines under it | Anything anyscribe decided for you: a missing-key fallback, an automatic model switch, `hi-Latn` routing |
| **→** | Marks the provider that wins right now — which is not always your `provider` setting, since a quality tier can override it |
| **Default model** | What that provider would use: your pin if you set one, otherwise its first listed model |
| **Alternatives** | The other models available (names when there are one or two, a count when there are more) |
| **Key** | `✓` key present · `missing` key needed · `—` no key needed |
| **Notes** | The quality tier that maps here, `pinned` if you set a model, `N custom` for added OpenRouter models, and the cached size for `local` |

> **This is the command to run when you're not sure what anyscribe will do.** `anyscribe config show` dumps the raw settings file; `anyscribe config` answers "what happens if I hit enter".

`anyscribe config --json` returns the same thing for scripts and agents — the full settings, a `resolved` block (`provider`, `model`, `via`, `notes`), and a `providers` array with each provider's models, key status, and tier.

### Flags

| Command | Flag | Short | Description |
|---------|------|-------|-------------|
| `config` (no subcommand) | `--json` | `-j` | Settings + `resolved` + `providers` as JSON |
| `config show` | `--json` | `-j` | Output settings as JSON |
| `config list-keys` | `--json` | `-j` | Output the settable-key list as JSON |

### Examples

```bash
# What will the next run use?
anyscribe config

# Show current config
anyscribe config show

# Change provider (also writes quality: custom, so the choice sticks)
anyscribe config set provider elevenlabs

# Or let a tier pick the provider instead
anyscribe config set quality accuracy

# Change language
anyscribe config set language hi

# Set an API key (stored in .env, not config.yaml)
anyscribe config set deepgram_api_key YOUR_KEY
anyscribe config set openai_api_key YOUR_KEY

# Pin a model for a provider (see below)
anyscribe config set provider_models.openai whisper-1

# Add your own OpenRouter models to the pickers (empty value clears them)
anyscribe config set extra_models.openrouter "qwen/qwen3-omni-flash,openai/gpt-audio"

# Set Instagram browser (for cookie-based downloads)
anyscribe config set instagram.browser firefox

# Get JSON output
anyscribe config show --json
```

### Pinning a model per provider

`--model` on a single command is temporary. To make a model choice permanent, set it in your config:

```bash
anyscribe config set provider_models.openai whisper-1
anyscribe config set provider_models.groq whisper-large-v3
```

The key is `provider_models.` followed by the provider name. Each provider gets its own entry, so if you switch between providers, each one remembers the model you picked for it. Anything you haven't set keeps that provider's default.

If you type a model that provider doesn't have, anyscribe refuses the change and prints the list of valid ones:

```
Unknown model 'whisper-2' for openai. Available: gpt-transcribe, whisper-1, gpt-4o-transcribe, gpt-4o-mini-transcribe
```

> **OpenRouter is the exception.** It accepts any audio-capable model slug, so anyscribe doesn't check it — a typo won't be caught until the request reaches OpenRouter.

### Adding your own models (OpenRouter only)

```bash
anyscribe config set extra_models.openrouter "qwen/qwen3-omni-flash,openai/gpt-audio"
anyscribe config set extra_models.openrouter ""     # clears the list
```

Models you add are merged into every picker — the `anyscribe config` dashboard, `anyscribe providers list` (where they're marked `(custom)`), and the Web UI's OpenRouter model box.

> **Why only OpenRouter?** It forwards any model name unchanged, so anyscribe doesn't need to know anything about the model in advance. Every other provider returns its own response shape, which anyscribe needs code to read — so their lists ship with releases. **To get a new Deepgram or ElevenLabs model, run `anyscribe update`**, not `config set`.

> **For the `local` provider, use `local_model` instead** (`anyscribe config set local_model small`). Local models are downloaded to your machine, so they have their own commands — see `anyscribe model` below.

See [configuration.md](configuration.md) for the full setting reference and [providers.md](providers.md) for what each model is good at.

> **Dot-notation:** Use dots for nested keys like `instagram.browser` and `provider_models.openai`.
>
> **API keys:** `anyscribe config set` also accepts API key names (e.g., `deepgram_api_key`, `openai_api_key`, `elevenlabs_api_key`, `sargam_api_key`, `groq_api_key`, `openrouter_api_key`). These are stored in `~/.anyscribe/.env`, not in config.yaml.

---

## anyscribe providers

Manage transcription providers.

```bash
anyscribe providers list          # show all providers
anyscribe providers test          # test active provider
anyscribe providers test openai   # test a specific provider
```

### Flags

| Command | Flag | Short | Description |
|---------|------|-------|-------------|
| `providers list` | `--json` | `-j` | Output provider list as JSON |

### What `providers list` shows

```
        Transcription Providers
Provider    Model             Also available                     Active
deepgram    nova-3            nova-2                             Active
openai      gpt-transcribe    whisper-1, gpt-4o-transcribe, ...
...
```

| Column | Meaning |
|--------|---------|
| **Provider** | The service name you'd pass to `--provider` |
| **Model** | The model that would actually be used right now — your pinned model if you set one, otherwise that provider's default |
| **Also available** | The other models you could switch to with `-m` or `provider_models`. Models you added yourself are marked `(custom)` |
| **Active** | Marks your `provider` setting |

> **`Active` is your setting, not necessarily what runs.** A `quality` tier can override it. For what will actually run, use `anyscribe config`.

### Available Providers

| Provider | API Key Env Var | Best For |
|----------|-----------------|----------|
| `openai` | `OPENAI_API_KEY` | General purpose, multilingual, diarization (default) |
| `deepgram` | `DEEPGRAM_API_KEY` | Fast, accurate, native diarization + Hindi Latin |
| `openrouter` | `OPENROUTER_API_KEY` | Access to various models |
| `elevenlabs` | `ELEVENLABS_API_KEY` | High accuracy, 99 languages |
| `sargam` | `SARGAM_API_KEY` | Indic languages (Hindi, Tamil, Telugu, etc.) |
| `groq` | `GROQ_API_KEY` | Cheapest cloud option (the `cost` quality tier) |
| `local` | None needed | Offline, free, runs on your machine |

> **Local provider** requires a one-time setup: `anyscribe local setup --model base` (or click "Set up local transcription" in the Web UI). See `anyscribe local` and `anyscribe model` below.

---

## anyscribe local

Three subcommands that manage offline transcription as a single opt-in lifecycle: install faster-whisper, download a model, persist the default; or reverse the whole thing. See also [providers.md → Local](providers.md).

### anyscribe local setup

```bash
anyscribe local setup --model base --yes
```

Installs faster-whisper into the same Python environment as anyscribe, downloads the Whisper model you picked, and saves it as your default. **Idempotent** — re-running with a model that's already cached just updates the default-model setting.

| Flag | Description |
|------|-------------|
| `--model`, `-m` | **Required.** Whisper size: `tiny`, `base`, `small`, `medium`, `large-v3`, `large-v3-turbo`, `distil-large-v3.5`. Recommended: `base`. No default — the CLI refuses to pick silently. |
| `--yes`, `-y` | Skip the confirmation prompt. Required in non-TTY (agent) contexts. |
| `--json`, `-j` | Stream NDJSON progress events to stdout (one JSON object per phase). |

### anyscribe local status

```bash
anyscribe local status --json
```

Reports faster-whisper version, ffmpeg presence, cached models, disk usage, and the detected install method (pip-venv / pipx / system). Always exits 0 — safe to call before setup.

### anyscribe local teardown

```bash
anyscribe local teardown --yes
```

Uninstalls faster-whisper via the same method it was installed with, deletes every cached Whisper model, and resets `settings.provider` to `openai` if it was currently `local`. `--yes` is required.

---

## anyscribe model

Day-to-day management of the Whisper cache. Requires `anyscribe local setup` to have run first (otherwise `pull` and `rm` error out with a hint pointing you at setup).

Valid sizes: `tiny`, `base`, `small`, `medium`, `large-v3`, `large-v3-turbo`, `distil-large-v3.5`. See [providers.md → Local](providers.md) for download sizes, RAM needs, and speed.

> **This is offline models only.** Cloud providers' models don't need downloading — you pick those with `-m` or `provider_models` (see above).

### anyscribe model list

```bash
anyscribe model list
anyscribe model list --json
```

Shows every size with cache status, disk usage, and which one is your default.

### anyscribe model pull

```bash
anyscribe model pull small
anyscribe model pull large-v3-turbo --json
```

Downloads an additional model into the cache. Idempotent — re-running on a cached size returns `{status: "already_present"}`.

### anyscribe model rm

```bash
anyscribe model rm tiny --yes
```

Deletes a cached model from disk. `--yes` required (destructive action).

### anyscribe model reinstall

```bash
anyscribe model reinstall base --yes --json
```

Delete + re-download in one call. Use when cached weights look corrupted or when you want to force a fresh copy. If the model wasn't cached to begin with, this is equivalent to `anyscribe model pull`. `--yes` is required (destructive).

Returns `{status: "reinstalled", bytes_freed, bytes_downloaded}` when weights were replaced, or `{status: "downloaded_only"}` when the model wasn't cached.

### anyscribe model info

```bash
anyscribe model info base --json
```

Inspects a single size — repo id, cache status, disk bytes, spec (download size / RAM / speed / quality).

---

## anyscribe ui

Launch a local web dashboard in your browser. Provides a visual interface for transcribing, browsing history, and managing settings — same functionality as the CLI, in a browser window.

```bash
anyscribe ui
```

Opens your browser at `http://127.0.0.1:8457` with three views:

- **Transcribe** — paste a URL, choose options (provider, language, multi-speaker mode), watch real-time progress, see results
- **History** — browse past transcripts from your vault, grouped by date, with search
- **Settings** — change config, view provider status, add/replace/remove API keys, check system health

> **Managing API keys in Settings → Providers:** expand a provider to add or replace its key. Once a key is saved, a **Remove key** button appears — click it, then click **Remove?** to confirm, and the key is deleted from `~/.anyscribe/.env`. If a key comes from your shell environment instead (e.g. `export OPENAI_API_KEY=…` in your shell profile), the Remove button is hidden — anyscribe can't edit your shell, so unset it there instead.

> **Web UI label conventions:** the `--diarize` CLI flag appears as a `Multi-speaker` toggle, and the `diarized` output format is labelled `with-speaker-labels`. Wire values (what gets sent to the API and saved to config) are unchanged — only the display labels are friendlier. The provider dropdown also disables unconfigured providers with a `· needs key` suffix and a one-click link to Settings, and the language input is a per-provider dropdown of every supported code (clear the field on focus to see the full list).

### Flags

| Flag | Short | Description | Default |
|------|-------|-------------|---------|
| `--port` | `-p` | Port to listen on | `8457` |
| `--no-open` | | Don't auto-open browser | Off (opens automatically) |

### Examples

```bash
# Launch web UI (opens browser automatically)
anyscribe ui

# Use a different port
anyscribe ui --port 9000

# Start without opening browser
anyscribe ui --no-open
```

> **Local only.** The web UI binds to `127.0.0.1` — it's only accessible from your machine. No auth needed. Stop it with Ctrl+C.

---

## anyscribe tray

A menu-bar icon that keeps `anyscribe ui` running in the background — click the icon instead of remembering to run a command every time.

> **Requires an extra install:** `pip install -U "anyscribe[tray]"`. This pulls in `pystray`, `Pillow`, and (on macOS) `pyobjc` — kept out of the base install so `pip install anyscribe` stays lightweight. If you run `anyscribe tray` without it, you'll get an install hint instead of a crash.

```bash
anyscribe tray
```

The icon appears in your menu bar (macOS) or system tray (Linux/Windows) with:

- **Open UI** — opens `http://127.0.0.1:8457` in your browser
- **Status** — shows `running` or `stopped`
- **Restart server** — stops and restarts the web server
- **Check for updates…** — opens the [GitHub releases page](https://github.com/rishmadaan/anyscribe/releases)
- **Quit** — stops the server and exits the tray cleanly

If a `anyscribe ui` server is already running on the port, `anyscribe tray` attaches to it instead of starting a second one. If a tray is already running, a second `anyscribe tray` refuses to start (no port collisions, no duplicate icons).

### Flags

| Flag | Short | Description | Default |
|------|-------|-------------|---------|
| `--port` | `-p` | Port the supervised web server listens on | `8457` |

### Examples

```bash
# Start the tray (installs the extra first, one time)
pip install -U "anyscribe[tray]"
anyscribe tray

# Use a different port
anyscribe tray --port 9000
```

> **Tip:** Quitting the tray (menu → Quit, or Ctrl+C in the terminal) stops the server it started and cleans up its pidfile. If it attached to a server it didn't start, quitting the tray leaves that server running.

---

## anyscribe install-service

Register `anyscribe tray` to start automatically every time you log in — so the menu-bar icon is just always there, no manual launch.

> **macOS only for now.** Other platforms print a friendly "not supported yet" error.

```bash
anyscribe install-service
```

Writes a launchd `LaunchAgent` (`~/Library/LaunchAgents/com.anyscribe.tray.plist`) with `RunAtLoad` set, and loads it immediately — so the tray starts now *and* at every future login.

### Flags

| Flag | Short | Description |
|------|-------|-------------|
| `--yes` | `-y` | Skip the confirmation prompt |
| `--json` | `-j` | Output result as JSON |

### Examples

```bash
anyscribe install-service              # prompts for confirmation
anyscribe install-service --yes        # no prompt
anyscribe install-service --json       # {"success": true, "data": {"plist": "..."}, "error": null}
```

---

## anyscribe uninstall-service

Remove the login auto-start registered by `anyscribe install-service`.

> **macOS only for now.** Other platforms print a friendly "not supported yet" error.

```bash
anyscribe uninstall-service
```

Unloads and deletes the LaunchAgent plist. This only removes the auto-start — it doesn't uninstall anyscribe itself or stop a tray that's currently running.

### Flags

| Flag | Short | Description |
|------|-------|-------------|
| `--yes` | `-y` | Skip the confirmation prompt |
| `--json` | `-j` | Output result as JSON |

### Examples

```bash
anyscribe uninstall-service            # prompts for confirmation
anyscribe uninstall-service --yes      # no prompt
```

> **Fully removing the tray?** `anyscribe uninstall-service` stops it from auto-starting at login. If a tray is currently running, quit it separately from its menu (or Ctrl+C the terminal it's running in).

---

## anyscribe install-skill

Manually install or update the anyscribe skill for [Claude Code](https://docs.anthropic.com/en/docs/claude-code). This teaches Claude how to transcribe, configure providers, and troubleshoot anyscribe on your behalf.

```bash
anyscribe install-skill
```

Copies skill files from the anyscribe package to `~/.claude/skills/anyscribe/`. Requires Claude Code to be installed (`~/.claude/` must exist).

### Flags

| Flag | Short | Description |
|------|-------|-------------|
| `--force` | `-f` | Overwrite existing skill files |

> **Tip:** You usually don't need to run this manually. The skill **auto-installs** when Claude Code is detected and **auto-updates** on every CLI invocation when the version changes. Use `--force` only if you need to repair a corrupted install.

---

## anyscribe update

Update anyscribe to the latest version by pulling from git and reinstalling.

```bash
anyscribe update
```

### Flags

| Flag | Short | Description |
|------|-------|-------------|
| `--force` | `-f` | Update even if you have local changes (stashes them first) |
| `--check` | `-c` | Only check if an update is available, don't install |

### Examples

```bash
# Check for updates without installing
anyscribe update --check

# Update to latest
anyscribe update

# Force update (stashes any local changes)
anyscribe update --force
```

---

## anyscribe migrate

Run this **once** after upgrading from the old `anyscribecli` package. It moves
your config, API keys, sessions, and downloads from the old app folder
(`~/.anyscribecli/`) to the new one (`~/.anyscribe/`), refreshes the Claude Code
skill, re-points the MCP server registration at `anyscribe`, and checks that the
`anyscribe`, `scribe`, and `ascli` commands all work. It never overwrites
anything already in the new folder, and it reports how many keys it moved —
never the keys themselves — so the output is safe to paste into a bug report.

> **Try `--dry-run` first.** It prints exactly what a real run would move and
> writes nothing at all. If the preview looks right, run it again without the flag.

```bash
anyscribe migrate --dry-run   # preview — nothing is written
anyscribe migrate             # actually migrate
```

Running it a second time is safe: it will simply report there is nothing left to do.

### Flags

| Flag | Short | Description |
|------|-------|-------------|
| `--dry-run` | | Show exactly what would change and write nothing (not even a backup) |
| `--json` | `-j` | Print the report as JSON instead of formatted text |

### Examples

```bash
# See what would move, change nothing
anyscribe migrate --dry-run

# Do the migration
anyscribe migrate

# Machine-readable report (for scripts / agents)
anyscribe migrate --json
```

---

## anyscribe doctor

Run diagnostic checks on your system. Useful when something isn't working.

```bash
anyscribe doctor
```

**What it checks:**
1. System dependencies (Python, yt-dlp, ffmpeg, ffprobe)
2. Configuration (app directory, config.yaml, .env, workspace vault, workspace index)
3. Installation info (version, install type, repo path)
4. Claude Code skill (installed, version, current or outdated)
5. Available updates

> **Tip:** If you're reporting a bug or asking for help, run `anyscribe doctor` and include the output — it gives all the info needed to debug.

---

## anyscribe --version

Print the installed version.

```bash
anyscribe --version
# Output: anyscribe v0.13.0
```

---

## anyscribe --help

Show all available commands and global options.

```bash
anyscribe --help
```

Every command also has its own help:

```bash
anyscribe transcribe --help
anyscribe onboard --help
```

---

## Shell Completion

anyscribe supports tab-completion for bash, zsh, and fish. Install it once:

```bash
anyscribe --install-completion
```

After restarting your shell, you can press Tab to autocomplete commands and flags.
