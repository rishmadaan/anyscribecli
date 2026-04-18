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
| `--provider` | `-p` | Override provider: openai, deepgram, elevenlabs, sargam, openrouter, local | From config |
| `--language` | `-l` | Language code (en, es, fr, hi, hi-Latn, etc.) or "auto" | From config (auto) |
| `--json` | `-j` | Output result as JSON | Off |
| `--keep-media` | | Keep downloaded audio in `~/.anyscribecli/downloads/audio/` | From config |
| `--diarize` | `-d` | Enable speaker diarization (auto-routes to Deepgram if configured) | Off |
| `--quiet` | `-q` | Suppress progress output | Off |
| `--clipboard` | `-c` | Read URL from system clipboard | Off |

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
| `--quiet` | `-q` | Suppress progress | Off |
| `--stop-on-error` | | Stop at first failure | Off (continues) |

### JSON output

```json
{
  "total": 3,
  "succeeded": 2,
  "failed": 1,
  "results": [
    {"success": true, "url": "...", "file": "...", "title": "...", ...},
    {"success": false, "url": "...", "error": "..."}
  ]
}
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
| `provider` | openai, deepgram, elevenlabs, sargam, openrouter, local | Default transcription provider |
| `language` | auto, en, es, fr, hi, ar, zh, ja, ko, ... | Default language |
| `keep_media` | true, false | Keep audio after transcription |
| `output_format` | clean, timestamped, diarized | Transcript format |
| `prompt_download` | never, ask, always | Download video after transcription |
| `local_file_media` | skip, copy, move, ask | Handle local file originals |
| `instagram.username` | string | Instagram username |
| `instagram.password` | string | Instagram password |
| `openai_api_key` | string | OpenAI API key (stored in .env) |
| `deepgram_api_key` | string | Deepgram API key (stored in .env) |
| `elevenlabs_api_key` | string | ElevenLabs API key (stored in .env) |
| `sargam_api_key` | string | Sarvam AI API key (stored in .env) |
| `openrouter_api_key` | string | OpenRouter API key (stored in .env) |

Use dot-notation for nested keys: `scribe config set instagram.username myuser`

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
scribe model list --json                  # Show every size + cache state
scribe model pull <size> --yes --json     # Download (idempotent)
scribe model rm <size> --yes --json       # Delete cached weights
scribe model info <size> --json           # Inspect a single size
```

**Not set up?** `pull`/`rm` exit 2 with `{error: "local transcription not set up", hint: "run scribe local setup ..."}`. `list` still works (shows everything as `cached: false`).

**Size-already-cached semantics:** `pull` returns `{status: "already_present"}` with exit 0. `rm` on a non-cached size returns `{status: "not_present"}` with exit 0.

---

## scribe onboard

Interactive setup wizard. Configures providers, API keys, preferences.

```bash
scribe onboard                          # First-time setup
scribe onboard --force                  # Re-run everything
scribe onboard --skip-deps              # Skip dependency check
scribe onboard --force --skip-deps      # Reconfigure, skip deps
```

**Note:** This is interactive — it takes over the terminal with arrow-key selectors. Don't run it programmatically.

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
# Output: scribe v0.7.2.3
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
