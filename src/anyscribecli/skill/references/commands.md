# scribe Command Reference

## scribe (default: transcribe)

Transcribe a URL or local audio/video file to markdown. A bare URL routes to transcribe automatically — no subcommand needed.

```bash
scribe "<url>"                         # YouTube/Instagram URL (always quote)
scribe /path/to/file.mp3              # Local audio/video file
scribe transcribe                     # Interactive prompt (no quoting needed)
scribe --clipboard                    # Read URL from clipboard
scribe transcribe "<url>"             # Explicit subcommand (also works)
```

### Flags

| Flag | Short | Description | Default |
|------|-------|-------------|---------|
| `--quality` | | Quality preset: accuracy \| balanced \| cost \| free (picks a provider) | From config (accuracy) |
| `--provider` | `-p` | Override provider: openai, deepgram, elevenlabs, sargam, groq, openrouter, local (wins over `--quality`) | From config |
| `--language` | `-l` | Language code (en, es, fr, hi, hi-Latn, etc.) or "auto" | From config (auto) |
| `--json` | `-j` | Output result as JSON | Off |
| `--keep-media` | | Keep downloaded audio in `~/.anyscribecli/downloads/audio/` | From config |
| `--diarize` | `-d` | Enable speaker diarization (auto-routes to Deepgram if configured) | Off |
| `--force` | `-f` | Re-transcribe even if this source was already transcribed | Off |
| `--quiet` | `-q` | Suppress progress output | Off |
| `--clipboard` | `-c` | Read URL from system clipboard | Off |

### Duplicate detection

Before transcribing, scribe scans the vault for a transcript whose frontmatter `source:` matches the URL/path. If found, it returns that existing file instead of re-transcribing — no download, no API cost. JSON output carries `"cached": true`; human output prints `Already transcribed: <path> — use --force to re-transcribe.` Pass `--force` / `-f` to override and transcribe fresh.

### Supported local file types

`.mp3`, `.mp4`, `.m4a`, `.wav`, `.opus`, `.ogg`, `.flac`, `.webm`, `.aac`, `.wma`

### JSON output

```json
{
  "success": true,
  "file": "/Users/you/anyscribe/sources/youtube/title.md",
  "title": "Video Title",
  "platform": "youtube",
  "duration": "12:34",
  "language": "en",
  "word_count": 1500,
  "provider": "openai",
  "cached": false
}
```

When the source was already in the vault, the same shape comes back with `"cached": true` and the existing file's path.

On error:
```json
{
  "success": false,
  "error": "yt-dlp download failed: Video unavailable"
}
```

### Examples

```bash
# YouTube video (bare URL — transcribes directly)
scribe "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

# YouTube short
scribe "https://www.youtube.com/shorts/abc123"

# Instagram reel
scribe "https://www.instagram.com/reel/C17LiBLyIOe/"

# Local file
scribe /path/to/podcast.mp3
scribe ~/recordings/meeting.m4a

# Override provider for one transcription
scribe "https://youtube.com/watch?v=abc123" --provider elevenlabs

# Force language detection
scribe "https://youtube.com/watch?v=abc123" --language hi

# Machine-readable output for scripting
scribe "https://youtube.com/watch?v=abc123" --json --quiet

# Re-transcribe a source already in the vault (skip the cache shortcut)
scribe "https://youtube.com/watch?v=abc123" --force

# From clipboard
scribe --clipboard
```

---

## scribe download

Download video or audio without transcribing.

```bash
scribe download "<url>"                 # Download video
scribe download "<url>" --audio-only    # Download audio only
scribe download                         # Interactive prompt
scribe download --clipboard             # From clipboard
```

### Flags

| Flag | Short | Description | Default |
|------|-------|-------------|---------|
| `--video` / `--audio-only` | | Download video (default) or audio only | `--video` |
| `--json` | `-j` | Output as JSON | Off |
| `--quiet` | `-q` | Suppress progress | Off |
| `--clipboard` | `-c` | Read URL from clipboard | Off |

### Output locations

- Video: `~/.anyscribecli/downloads/video/<platform>/`
- Audio: `~/.anyscribecli/downloads/audio/<platform>/`

---

## scribe batch

Transcribe multiple URLs or files from a list.

```bash
scribe batch urls.txt
```

### Input file format

One URL or file path per line. Blank lines and `#comments` are skipped.

```
https://youtube.com/watch?v=abc123
https://youtube.com/watch?v=def456
# this line is skipped
/path/to/local-recording.mp3
```

### Flags

| Flag | Short | Description | Default |
|------|-------|-------------|---------|
| `--provider` | `-p` | Override provider | From config |
| `--language` | `-l` | Override language | auto |
| `--json` | `-j` | Output as JSON | Off |
| `--keep-media` | | Keep audio files | From config |
| `--force` | `-f` | Re-transcribe sources already in the vault | Off |
| `--quiet` | `-q` | Suppress progress | Off |
| `--stop-on-error` | | Stop at first failure | Off (continues) |
| `--timeout` | | Per-URL timeout in seconds. A timed-out URL is marked failed (`"timed out after Ns"`) and the batch moves to the next URL | None (no timeout) |

Sources already in the vault are skipped (returned from cache) unless `--force` is passed. The summary table marks those rows `CACHED`, and each such result carries `"cached": true`.

### JSON output

```json
{
  "total": 3,
  "succeeded": 2,
  "failed": 1,
  "results": [
    {"success": true, "url": "...", "file": "...", "title": "...", "cached": false, ...},
    {"success": false, "url": "...", "error": "..."}
  ]
}
```

### Examples

```bash
# Cap each URL at 5 minutes; stop-on-error not set, so it moves to the next one
scribe batch urls.txt --timeout 300
```

---

## scribe rm

Delete a transcript from the workspace and resync the master `_index.md`.

```bash
scribe rm "sources/youtube/my-video.md"    # by path
scribe rm my-video                          # by slug (filename without .md)
scribe rm my-video --yes --json             # skip prompt, machine output
```

Accepts a full file path or a bare slug. If a slug matches more than one transcript, `rm` prints the matches and exits — pass a full path to disambiguate. Daily logs under `daily/` are left untouched as history; only the transcript file and its master-index row are removed.

### Flags

| Flag | Short | Description | Default |
|------|-------|-------------|---------|
| `--yes` | `-y` | Skip the confirmation prompt (required in non-TTY / agent contexts) | Off |
| `--json` | `-j` | Output result as JSON | Off |

### JSON output

```json
{ "success": true, "data": { "deleted": "sources/youtube/my-video.md" }, "error": null }
```

Exits 1 (with `error` set) when no transcript matches, the slug is ambiguous, or the file cannot be deleted.

---

## scribe logs

View recent transcription activity and any recovery artifacts left behind by failed runs.

```bash
scribe logs                     # last 20 entries, newest first
scribe logs --limit 50          # more entries
scribe logs --json              # machine-readable
```

Reads the workspace's `daily/*.md` logs — there's no separate log store, so this is
always in sync with what's actually in the vault. Also lists files in the recovery
directory (audio saved from a failed transcription) so you know what's safe to
retry or delete.

### Flags

| Flag | Short | Description | Default |
|------|-------|-------------|---------|
| `--limit` | `-n` | Number of log entries to show | `20` |
| `--json` | `-j` | Output result as JSON | Off |

### JSON output

```json
{
  "success": true,
  "data": {
    "entries": [
      {"date": "2026-07-04", "time": "09:12", "platform": "youtube", "entry": "[[sources/youtube/title.md|Video Title]]", "duration": "12:34"}
    ],
    "recovery": [
      {"name": "youtube/abc123.mp3", "size": 4821932, "mtime": "2026-07-03T22:14:01"}
    ]
  },
  "error": null
}
```

Empty state (human output): `No activity logged yet.`

### Examples

```bash
# Quick check on what was transcribed today
scribe logs --limit 5

# Machine-readable for a status dashboard
scribe logs --json --limit 100
```

---

## scribe ui

Launch a local web dashboard in the browser. Visual interface for transcribing, browsing history, and managing settings.

```bash
scribe ui                  # opens browser at http://127.0.0.1:8457
scribe ui --port 9000      # custom port
scribe ui --no-open        # don't auto-open browser
```

### Flags

| Flag | Short | Description | Default |
|------|-------|-------------|---------|
| `--port` | `-p` | Port to listen on | `8457` |
| `--no-open` | | Don't auto-open browser | Off |

Local only (127.0.0.1). Stop with Ctrl+C.

---

## scribe config

View and change settings.

```bash
scribe config show                      # Display all settings
scribe config show --json               # Output as JSON
scribe config set <key> <value>         # Change a setting
scribe config path                      # Print config file location
```

### Settable keys

| Key | Values | Description |
|-----|--------|-------------|
| `provider` | openai, deepgram, elevenlabs, sargam, groq, openrouter, local | Default transcription provider |
| `language` | auto, en, es, fr, hi, ar, zh, ja, ko, ... | Default language |
| `keep_media` | true, false | Keep audio after transcription |
| `output_format` | clean, timestamped, diarized | Transcript format |
| `prompt_download` | never, ask, always | Download video after transcription |
| `local_file_media` | skip, copy, move, ask | Handle local file originals |
| `instagram.browser` | string | Browser to read IG cookies from. Optional — only needed for private reels. Supported: `firefox`, `chrome`, `safari`, `brave`, `edge`, `chromium`, `vivaldi`, `opera` |
| `openai_api_key` | string | OpenAI API key (stored in .env) |
| `deepgram_api_key` | string | Deepgram API key (stored in .env) |
| `elevenlabs_api_key` | string | ElevenLabs API key (stored in .env) |
| `sargam_api_key` | string | Sarvam AI API key (stored in .env) |
| `groq_api_key` | string | Groq API key (stored in .env) |
| `openrouter_api_key` | string | OpenRouter API key (stored in .env) |

Use dot-notation for nested keys: `scribe config set instagram.browser firefox`

```bash
# Configure browser for IG cookies (only if needed for private/rate-limited reels)
scribe config set instagram.browser firefox
```

API key names are also accepted — they are stored in `~/.anyscribecli/.env`, not config.yaml:
```bash
scribe config set deepgram_api_key YOUR_KEY
```

---

## scribe providers

Manage transcription providers.

```bash
scribe providers list                   # Show available providers
scribe providers list --json            # Output as JSON
scribe providers test                   # Test active provider
scribe providers test <name>            # Test a specific provider
```

---

## scribe local

Lifecycle for offline transcription — installs / uninstalls faster-whisper and the first Whisper model. All three subcommands accept `--json`.

```bash
scribe local setup --model base --yes --json     # Install + download + persist
scribe local status --json                       # Report readiness, cached sizes
scribe local teardown --yes --json               # Reverse setup
```

### scribe local setup

| Flag | Short | Description | Default |
|------|-------|-------------|---------|
| `--model` | `-m` | **Required.** `tiny`, `base`, `small`, `medium`, `large-v3`. Recommended: `base`. | *none — must specify* |
| `--yes` | `-y` | Skip confirmation. Required in non-TTY contexts. | Off |
| `--json` | `-j` | NDJSON progress events on stdout. | Off |

**Agent rule:** always pass `--model` — the CLI refuses to pick one silently. Default to `base` unless the user asks otherwise.

**Exit codes:**
- `0` — set up (or already set up).
- `1` — install/download failure. JSON stderr carries the exact command that failed and its stderr.
- `2` — usage error (missing `--model`, unknown size, non-TTY without `--yes`).

### scribe local status

Always exits 0. Reports `set_up`, `faster_whisper_installed`, `faster_whisper_version`, `ffmpeg_ok`, `default_model`, `models` (cache state per size), `total_disk_bytes`, `install_method`.

### scribe local teardown

`--yes` is required. Uninstalls faster-whisper, deletes every cached model, resets `settings.provider` to `openai` if it was `local`.

---

## scribe model

Cache management for Whisper models. All subcommands accept `--json`.

```bash
scribe model list --json                      # Show every size + cache state
scribe model pull <size> --yes --json         # Download (idempotent)
scribe model rm <size> --yes --json           # Delete cached weights
scribe model reinstall <size> --yes --json    # Delete + re-download (corrupted weights)
scribe model info <size> --json               # Inspect a single size
```

**Not set up?** `pull`/`rm` exit 2 with `{error: "local transcription not set up", hint: "run scribe local setup ..."}`. `list` still works (shows everything as `cached: false`).

**Size-already-cached semantics:** `pull` returns `{status: "already_present"}` with exit 0. `rm` on a non-cached size returns `{status: "not_present"}` with exit 0.

---

## scribe onboard

Configures providers, API keys, and preferences. Two modes:

```bash
# Interactive TUI — for humans typing in a terminal.
scribe onboard
scribe onboard --force                  # Re-run over existing config
scribe onboard --skip-deps              # Skip dependency check

# Headless — for agents / CI / scripts.
scribe onboard --provider openai --api-key "$OPENAI_API_KEY" --yes --json
scribe onboard --provider local --local-model base --yes --json
```

**Agent rule:** always use the headless form. The interactive TUI uses arrow-key selectors and blocks on stdin — it cannot be driven programmatically.

| Flag | Required with `--yes` | Default | Description |
|------|-----------------------|---------|-------------|
| `--yes` / `-y` | yes (to opt in) | off | Turn on headless mode. |
| `--provider` / `-p` | yes | none | `openai`, `deepgram`, `elevenlabs`, `sargam`, `openrouter`, `local`. |
| `--api-key` | for API providers (or env var) | none | Stored in `.env`. Prefer the env-var form. |
| `--local-model` | yes when `--provider=local` | none | `tiny`, `base`, `small`, `medium`, `large-v3`. Recommended: `base`. |
| `--workspace` | no | `~/anyscribe` | Obsidian vault path. |
| `--language` | no | `auto` | Default language code. |
| `--keep-media` / `--no-keep-media` | no | off | Keep downloaded audio after transcription. |
| `--output-format` | no | `clean` | `clean`, `timestamped`, `diarized`. |
| `--instagram-browser` | no | — | Browser to read IG cookies from. Optional — only needed for private reels. |
| `--force` / `-f` | no | off | Re-run over existing config. |
| `--json` / `-j` | no | off | Emit the result as a single JSON object on stdout. |

**Exit codes:** 0 success · 1 setup failure (e.g., local install failed — stderr carries pip command + captured stderr) · 2 usage error (missing `--provider`, unknown provider, already configured without `--force`, etc.).

---

## scribe doctor

Run diagnostic checks. Reports on dependencies, config, installation, and updates.

```bash
scribe doctor
```

Output includes everything needed for debugging. Suggest this when users report issues.

---

## scribe update

Update scribe to the latest version.

```bash
scribe update                           # Update to latest
scribe update --check                   # Check without installing
scribe update --force                   # Force update (stashes local changes)
```

---

## scribe --version

```bash
scribe --version
# Output: scribe v0.12.0
```

---

## scribe --help

```bash
scribe --help                           # All commands
scribe transcribe --help                # Command-specific help
```

---

## Shell Completion

```bash
scribe --install-completion             # Install tab completion for your shell
```

Restart your shell after installing.
