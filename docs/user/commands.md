---
summary: Complete reference for all scribe commands, flags, and options.
read_when:
  - You want to know what flags are available
  - You need the exact syntax for a command
  - You're scripting or automating with scribe
---

# Command Reference

Every scribe command. Copy-paste friendly.

> **Agentic-first CLI.** scribe's CLI is designed to be usable by AI agents, CI jobs, and scripts — not just humans. Consequential commands follow the same contract:
>
> - **`--json` on every command** — machine-parseable output; agents parse this, humans ignore it.
> - **`--yes` for non-interactive runs** — commands that would normally prompt for confirmation refuse to run without `--yes` when there's no TTY (i.e., when invoked from an agent or script).
> - **No silent defaults for choices agents might make** — e.g., `scribe local setup` requires `--model` explicitly; the CLI never picks a size on your behalf. The recommended value is documented so agents know what to pass.
> - **Structured exit codes** — `0` success, `1` operational failure, `2` usage error. Stderr on exit 2 carries a JSON payload with the missing field(s).
> - **Prefer env vars for secrets** — passing `--api-key` on argv leaks to shell history; set `$OPENAI_API_KEY` etc. in the environment instead.
>
> Humans running scribe interactively can mostly ignore these rules — the defaults are friendly without flags. They're called out here so script authors and agent skills know what to expect.

## Quick Overview

| Command | What it does |
|---------|-------------|
| `scribe "<url or file>"` | Transcribe a URL or local file (default action) |
| `scribe onboard` | First-time setup wizard (interactive TUI) |
| `scribe onboard --yes --provider X ...` | Headless setup (for agents / scripts) |
| `scribe download "<url>"` | Download video or audio only (no transcription) |
| `scribe batch <file>` | Batch transcribe URLs or file paths from a file |
| `scribe config show` | View current settings |
| `scribe config set <key> <value>` | Change a setting |
| `scribe config path` | Print config file location |
| `scribe providers list` | Show available providers |
| `scribe providers test [name]` | Test a provider's API key |
| `scribe local setup --model <size>` | Install faster-whisper + download a Whisper model |
| `scribe local status` | Report local-transcription readiness |
| `scribe local teardown --yes` | Uninstall faster-whisper + delete all cached models |
| `scribe model list` | List Whisper models with cache status |
| `scribe model pull <size>` | Download an additional Whisper model |
| `scribe model rm <size> --yes` | Delete a cached Whisper model |
| `scribe model reinstall <size> --yes` | Delete + re-download in one step (for corrupted weights) |
| `scribe model info <size>` | Inspect a single Whisper model |
| `scribe ui` | Launch the web UI in your browser |
| `scribe install-skill` | Install/update Claude Code skill |
| `scribe update` | Update to the latest version |
| `scribe doctor` | Check system health |
| `scribe --version` | Show version |
| `scribe --help` | Show help |

---

## scribe onboard

Interactive setup wizard. Run this once after installing, or again to change settings.

```bash
scribe onboard
```

> **Prefer clicking to typing?** `scribe ui` opens the Web UI with the same onboarding flow as a modal wizard. Both paths set up the same config — pick whichever feels faster. See [getting-started.md](getting-started.md) for the Web UI walk-through.

**What the TUI does** (arrow-key selectors throughout):
1. Checks system dependencies (Python, yt-dlp, ffmpeg) — offers to install missing ones
2. Choose transcription provider (5 options, arrow keys)
3. Enter API key for your chosen provider
4. Optionally add API keys for other providers
5. Optionally configure Instagram browser (for cookie-based downloads)
6. Choose default language (arrow-key selector with common options)
7. Choose whether to keep audio files after transcription
8. Choose post-transcription download behavior (never/ask/always)
9. Choose workspace location (default: `~/anyscribe/`)
10. Creates your Obsidian workspace

### Headless mode (for agents + scripts)

Pass `--yes` with the settings you want and skip the interactive flow entirely. Required for automation and CI — arrow-key TUIs don't work without a tty.

```bash
scribe onboard \
  --provider openai \
  --api-key "$OPENAI_API_KEY" \
  --yes --json
```

For offline/local transcription as the primary provider:

```bash
scribe onboard \
  --provider local \
  --local-model base \
  --yes --json
```

| Flag | Required with `--yes` | Default | Description |
|------|-----------------------|---------|-------------|
| `--yes` / `-y` | yes | off | Opt into headless mode. Without this, `scribe onboard` runs the interactive TUI. |
| `--provider` / `-p` | **yes** | none | One of `openai`, `deepgram`, `elevenlabs`, `sargam`, `openrouter`, `local`. |
| `--api-key` | for API providers (or use env var) | none | Stored in `~/.anyscribecli/.env`. Prefer setting the env var (e.g. `OPENAI_API_KEY`) to avoid leaking keys into shell history. |
| `--local-model` | **yes when `--provider=local`** | none | Whisper size. Recommended: `base`. |
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
scribe onboard

# Re-run to change settings (e.g., switch provider or update API key)
scribe onboard --force

# Skip dependency check (you know they're installed)
scribe onboard --force --skip-deps
```

---

## scribe (default: transcribe)

The main command. Transcribes a URL or local audio/video file and saves a formatted markdown file. **A bare URL routes to transcribe automatically — no subcommand needed.**

```bash
scribe "<url>"                          # bare URL — just works
scribe /path/to/file.mp3               # local file — just works
scribe transcribe "<url>"              # explicit subcommand (also works)
```

> **Important:** Always wrap URLs in quotes. Shells like zsh treat `?` as a special character, which breaks unquoted YouTube URLs. Local file paths don't need quotes.

### Ways to provide input

```bash
# 1. Pass a URL as an argument (always use quotes)
scribe "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

# 2. Pass a local audio/video file
scribe /path/to/podcast.mp3
scribe ~/recordings/meeting.m4a

# 3. Run without input — you'll be prompted to paste a URL or file path
scribe transcribe

# 4. Copy a URL to your clipboard, then:
scribe --clipboard
```

### Flags

| Flag | Short | Description | Default |
|------|-------|-------------|---------|
| `--provider` | `-p` | Transcription provider to use | From config (openai) |
| `--language` | `-l` | Language code for transcription | `auto` (auto-detect) |
| `--json` | `-j` | Output result as JSON | Off |
| `--keep-media` | | Keep the downloaded audio file | From config (false) |
| `--diarize` | `-d` | Enable speaker diarization (auto-routes to Deepgram if configured) | Off |
| `--quiet` | `-q` | No progress output (just the result) | Off |
| `--clipboard` | `-c` | Read URL from system clipboard | Off |

### Examples

```bash
# YouTube video (always quote the URL)
scribe "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

# Instagram reel
scribe "https://www.instagram.com/reel/C17LiBLyIOe/"

# Local audio/video file
scribe /path/to/podcast.mp3
scribe ~/recordings/meeting.m4a
scribe ./interview.opus

# Interactive — paste URL or file path when prompted
scribe transcribe

# From clipboard
scribe --clipboard

# Specify language (skip auto-detection)
scribe "https://youtube.com/watch?v=abc123" --language es

# Keep the audio file alongside the transcript
scribe "https://youtube.com/watch?v=abc123" --keep-media

# Enable speaker diarization (auto-switches to Deepgram if configured)
# Deepgram auto-detects the number of speakers — no need to specify a count
scribe "https://youtube.com/watch?v=abc123" --diarize

# Diarize with a specific provider (overrides auto-routing)
scribe "https://youtube.com/watch?v=abc123" --diarize --provider openai

# Diarize a mostly-Hindi or Hinglish recording (romanized Latin script output)
scribe "https://youtube.com/watch?v=abc123" --diarize --language hi-Latn

# JSON output — for scripts, AI agents, or piping to other tools
scribe "https://youtube.com/watch?v=abc123" --json
```

### JSON Output

When you use `--json`, scribe prints structured JSON to stdout (progress goes to stderr):

```json
{
  "success": true,
  "file": "/Users/you/anyscribe/sources/youtube/video-title.md",
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

> **Scripting tip:** Use `--json --quiet` together to get clean JSON with no extra output. Pipe to `jq` for filtering: `scribe "url" --json -q | jq '.file'`

### Speaker Diarization

The `--diarize` flag enables multi-speaker transcription — scribe identifies who said what and labels each turn.

**How it works:**
- **Automatic speaker detection** — the number of speakers is detected automatically from audio characteristics (pitch, tone, cadence). You never need to specify how many speakers are in the recording.
- **Speaker labels** — each speaker gets a label (`Speaker 0`, `Speaker 1`, `Speaker 2`, etc.) assigned in the order they first appear.
- **Auto-routing to Deepgram** — when `--diarize` is used without `-p`, scribe automatically switches to Deepgram if a Deepgram API key is configured. Deepgram handles files of any size natively and produces consistent speaker labels. Override with `-p openai` if needed.
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
scribe config set deepgram_api_key YOUR_KEY

# 2. Transcribe with speakers
scribe "url" --diarize                        # English / auto-detect
scribe "url" --diarize --language hi-Latn     # Hindi / Hinglish
```

### Supported Inputs

| Source | Patterns | Status |
|--------|----------|--------|
| YouTube | `youtube.com/watch?v=`, `youtu.be/`, `youtube.com/shorts/`, `youtube.com/live/` | Working |
| Instagram | `instagram.com/reel/`, `instagram.com/p/` | Working (public reels out of the box; set `instagram.browser` for rate-limited or private reels) |
| Local files | `.mp3`, `.mp4`, `.m4a`, `.wav`, `.opus`, `.ogg`, `.flac`, `.webm`, `.aac`, `.wma` | Working |

---

## scribe batch

Transcribe multiple URLs or local files from a list. One entry per line, blank lines and `#comments` are skipped.

```bash
scribe batch urls.txt
```

### Flags

| Flag | Short | Description | Default |
|------|-------|-------------|---------|
| `--provider` | `-p` | Override provider | From config |
| `--language` | `-l` | Override language | `auto` |
| `--json` | `-j` | Output results as JSON | Off |
| `--keep-media` | | Keep audio files | From config |
| `--diarize` | `-d` | Enable speaker diarization | Off |
| `--quiet` | `-q` | Suppress progress | Off |
| `--stop-on-error` | | Stop at first failure | Off (continues) |

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
scribe batch urls.txt

# Stop if any fail
scribe batch urls.txt --stop-on-error

# JSON output for scripting
scribe batch urls.txt --json
```

---

## scribe download

Download video or audio from a URL — no transcription. Useful when you just want the file.

```bash
scribe download "<url>"
```

Saves to `~/.anyscribecli/downloads/video/<platform>/` (default) or `~/.anyscribecli/downloads/audio/<platform>/` with `--audio-only`.

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
scribe download "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

# Download audio only (no video)
scribe download "https://www.youtube.com/watch?v=dQw4w9WgXcQ" --audio-only

# From clipboard
scribe download --clipboard

# Interactive (paste URL when prompted)
scribe download

# JSON output
scribe download "https://youtube.com/watch?v=abc123" --json
```

---

## scribe config

View and change settings.

```bash
scribe config show           # display all settings
scribe config set key value  # change a setting
scribe config path           # print config file location
```

### Flags

| Command | Flag | Short | Description |
|---------|------|-------|-------------|
| `config show` | `--json` | `-j` | Output settings as JSON |

### Examples

```bash
# Show current config
scribe config show

# Change provider
scribe config set provider elevenlabs

# Change language
scribe config set language hi

# Set an API key (stored in .env, not config.yaml)
scribe config set deepgram_api_key YOUR_KEY
scribe config set openai_api_key YOUR_KEY

# Set Instagram browser (for cookie-based downloads)
scribe config set instagram.browser firefox

# Get JSON output
scribe config show --json
```

> **Dot-notation:** Use dots for nested keys like `instagram.browser`.
>
> **API keys:** `scribe config set` also accepts API key names (e.g., `deepgram_api_key`, `openai_api_key`, `elevenlabs_api_key`, `sargam_api_key`, `openrouter_api_key`). These are stored in `~/.anyscribecli/.env`, not in config.yaml.

---

## scribe providers

Manage transcription providers.

```bash
scribe providers list          # show all providers
scribe providers test          # test active provider
scribe providers test openai   # test a specific provider
```

### Flags

| Command | Flag | Short | Description |
|---------|------|-------|-------------|
| `providers list` | `--json` | `-j` | Output provider list as JSON |

### Available Providers

| Provider | API Key Env Var | Best For |
|----------|-----------------|----------|
| `openai` | `OPENAI_API_KEY` | General purpose, multilingual, diarization (default) |
| `deepgram` | `DEEPGRAM_API_KEY` | Fast, accurate, native diarization + Hindi Latin |
| `openrouter` | `OPENROUTER_API_KEY` | Access to various models |
| `elevenlabs` | `ELEVENLABS_API_KEY` | High accuracy, 99 languages |
| `sargam` | `SARGAM_API_KEY` | Indic languages (Hindi, Tamil, Telugu, etc.) |
| `local` | None needed | Offline, free, runs on your machine |

> **Local provider** requires a one-time setup: `scribe local setup --model base` (or click "Set up local transcription" in the Web UI). See `scribe local` and `scribe model` below.

---

## scribe local

Three subcommands that manage offline transcription as a single opt-in lifecycle: install faster-whisper, download a model, persist the default; or reverse the whole thing. See also [providers.md → Local](providers.md).

### scribe local setup

```bash
scribe local setup --model base --yes
```

Installs faster-whisper into the same Python environment as scribe, downloads the Whisper model you picked, and saves it as your default. **Idempotent** — re-running with a model that's already cached just updates the default-model setting.

| Flag | Description |
|------|-------------|
| `--model`, `-m` | **Required.** Whisper size: `tiny`, `base`, `small`, `medium`, `large-v3`. Recommended: `base`. No default — the CLI refuses to pick silently. |
| `--yes`, `-y` | Skip the confirmation prompt. Required in non-TTY (agent) contexts. |
| `--json`, `-j` | Stream NDJSON progress events to stdout (one JSON object per phase). |

### scribe local status

```bash
scribe local status --json
```

Reports faster-whisper version, ffmpeg presence, cached models, disk usage, and the detected install method (pip-venv / pipx / system). Always exits 0 — safe to call before setup.

### scribe local teardown

```bash
scribe local teardown --yes
```

Uninstalls faster-whisper via the same method it was installed with, deletes every cached Whisper model, and resets `settings.provider` to `openai` if it was currently `local`. `--yes` is required.

---

## scribe model

Day-to-day management of the Whisper cache. Requires `scribe local setup` to have run first (otherwise `pull` and `rm` error out with a hint pointing you at setup).

### scribe model list

```bash
scribe model list
scribe model list --json
```

Shows every size with cache status, disk usage, and which one is your default.

### scribe model pull

```bash
scribe model pull small
scribe model pull large-v3 --json
```

Downloads an additional model into the cache. Idempotent — re-running on a cached size returns `{status: "already_present"}`.

### scribe model rm

```bash
scribe model rm tiny --yes
```

Deletes a cached model from disk. `--yes` required (destructive action).

### scribe model reinstall

```bash
scribe model reinstall base --yes --json
```

Delete + re-download in one call. Use when cached weights look corrupted or when you want to force a fresh copy. If the model wasn't cached to begin with, this is equivalent to `scribe model pull`. `--yes` is required (destructive).

Returns `{status: "reinstalled", bytes_freed, bytes_downloaded}` when weights were replaced, or `{status: "downloaded_only"}` when the model wasn't cached.

### scribe model info

```bash
scribe model info base --json
```

Inspects a single size — repo id, cache status, disk bytes, spec (download size / RAM / speed / quality).

---

## scribe ui

Launch a local web dashboard in your browser. Provides a visual interface for transcribing, browsing history, and managing settings — same functionality as the CLI, in a browser window.

```bash
scribe ui
```

Opens your browser at `http://127.0.0.1:8457` with three views:

- **Transcribe** — paste a URL, choose options (provider, language, multi-speaker mode), watch real-time progress, see results
- **History** — browse past transcripts from your vault, grouped by date, with search
- **Settings** — change config, view provider status, test API keys, check system health

> **Web UI label conventions:** the `--diarize` CLI flag appears as a `Multi-speaker` toggle, and the `diarized` output format is labelled `with-speaker-labels`. Wire values (what gets sent to the API and saved to config) are unchanged — only the display labels are friendlier. The provider dropdown also disables unconfigured providers with a `· needs key` suffix and a one-click link to Settings, and the language input is a per-provider dropdown of every supported code (clear the field on focus to see the full list).

### Flags

| Flag | Short | Description | Default |
|------|-------|-------------|---------|
| `--port` | `-p` | Port to listen on | `8457` |
| `--no-open` | | Don't auto-open browser | Off (opens automatically) |

### Examples

```bash
# Launch web UI (opens browser automatically)
scribe ui

# Use a different port
scribe ui --port 9000

# Start without opening browser
scribe ui --no-open
```

> **Local only.** The web UI binds to `127.0.0.1` — it's only accessible from your machine. No auth needed. Stop it with Ctrl+C.

---

## scribe install-skill

Manually install or update the scribe skill for [Claude Code](https://docs.anthropic.com/en/docs/claude-code). This teaches Claude how to transcribe, configure providers, and troubleshoot scribe on your behalf.

```bash
scribe install-skill
```

Copies skill files from the scribe package to `~/.claude/skills/scribe/`. Requires Claude Code to be installed (`~/.claude/` must exist).

### Flags

| Flag | Short | Description |
|------|-------|-------------|
| `--force` | `-f` | Overwrite existing skill files |

> **Tip:** You usually don't need to run this manually. The skill **auto-installs** when Claude Code is detected and **auto-updates** on every CLI invocation when the version changes. Use `--force` only if you need to repair a corrupted install.

---

## scribe update

Update scribe to the latest version by pulling from git and reinstalling.

```bash
scribe update
```

### Flags

| Flag | Short | Description |
|------|-------|-------------|
| `--force` | `-f` | Update even if you have local changes (stashes them first) |
| `--check` | `-c` | Only check if an update is available, don't install |

### Examples

```bash
# Check for updates without installing
scribe update --check

# Update to latest
scribe update

# Force update (stashes any local changes)
scribe update --force
```

---

## scribe doctor

Run diagnostic checks on your system. Useful when something isn't working.

```bash
scribe doctor
```

**What it checks:**
1. System dependencies (Python, yt-dlp, ffmpeg, ffprobe)
2. Configuration (app directory, config.yaml, .env, workspace vault, workspace index)
3. Installation info (version, install type, repo path)
4. Claude Code skill (installed, version, current or outdated)
5. Available updates

> **Tip:** If you're reporting a bug or asking for help, run `scribe doctor` and include the output — it gives all the info needed to debug.

---

## scribe --version

Print the installed version.

```bash
scribe --version
# Output: scribe v0.8.3
```

---

## scribe --help

Show all available commands and global options.

```bash
scribe --help
```

Every command also has its own help:

```bash
scribe transcribe --help
scribe onboard --help
```

---

## Shell Completion

scribe supports tab-completion for bash, zsh, and fish. Install it once:

```bash
scribe --install-completion
```

After restarting your shell, you can press Tab to autocomplete commands and flags.
