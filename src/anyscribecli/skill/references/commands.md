# ascli Command Reference

## ascli transcribe

Transcribe a URL or local audio/video file to markdown.

```bash
ascli transcribe "<url>"              # YouTube/Instagram URL (always quote)
ascli transcribe /path/to/file.mp3    # Local audio/video file
ascli transcribe                      # Interactive prompt (no quoting needed)
ascli transcribe --clipboard          # Read URL from clipboard
```

### Flags

| Flag | Short | Description | Default |
|------|-------|-------------|---------|
| `--provider` | `-p` | Override provider: openai, elevenlabs, sargam, openrouter, local | From config |
| `--language` | `-l` | Language code (en, es, fr, hi, ar, etc.) or "auto" | From config (auto) |
| `--json` | `-j` | Output result as JSON | Off |
| `--keep-media` | | Keep downloaded audio in `~/.anyscribecli/media/audio/` | From config |
| `--quiet` | `-q` | Suppress progress output | Off |
| `--clipboard` | `-c` | Read URL from system clipboard | Off |

### Supported local file types

`.mp3`, `.mp4`, `.m4a`, `.wav`, `.opus`, `.ogg`, `.flac`, `.webm`, `.aac`, `.wma`

### JSON output

```json
{
  "success": true,
  "file": "/Users/you/.anyscribecli/workspace/sources/youtube/2026-03-26/title.md",
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
# YouTube video
ascli transcribe "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

# YouTube short
ascli transcribe "https://www.youtube.com/shorts/abc123"

# Instagram reel
ascli transcribe "https://www.instagram.com/reel/C17LiBLyIOe/"

# Local file
ascli transcribe /path/to/podcast.mp3
ascli transcribe ~/recordings/meeting.m4a

# Override provider for one transcription
ascli transcribe "https://youtube.com/watch?v=abc123" --provider elevenlabs

# Force language detection
ascli transcribe "https://youtube.com/watch?v=abc123" --language hi

# Machine-readable output for scripting
ascli transcribe "https://youtube.com/watch?v=abc123" --json --quiet

# From clipboard
ascli transcribe --clipboard
```

---

## ascli download

Download video or audio without transcribing.

```bash
ascli download "<url>"                 # Download video
ascli download "<url>" --audio-only    # Download audio only
ascli download                         # Interactive prompt
ascli download --clipboard             # From clipboard
```

### Flags

| Flag | Short | Description | Default |
|------|-------|-------------|---------|
| `--video` / `--audio-only` | | Download video (default) or audio only | `--video` |
| `--json` | `-j` | Output as JSON | Off |
| `--quiet` | `-q` | Suppress progress | Off |
| `--clipboard` | `-c` | Read URL from clipboard | Off |

### Output locations

- Video: `~/.anyscribecli/media/video/<platform>/YYYY-MM-DD/`
- Audio: `~/.anyscribecli/media/audio/<platform>/YYYY-MM-DD/`

---

## ascli batch

Transcribe multiple URLs or files from a list.

```bash
ascli batch urls.txt
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

## ascli config

View and change settings.

```bash
ascli config show                      # Display all settings
ascli config show --json               # Output as JSON
ascli config set <key> <value>         # Change a setting
ascli config path                      # Print config file location
```

### Settable keys

| Key | Values | Description |
|-----|--------|-------------|
| `provider` | openai, elevenlabs, sargam, openrouter, local | Default transcription provider |
| `language` | auto, en, es, fr, hi, ar, zh, ja, ko, ... | Default language |
| `keep_media` | true, false | Keep audio after transcription |
| `output_format` | clean, timestamped | Transcript format |
| `prompt_download` | never, ask, always | Download video after transcription |
| `local_file_media` | skip, copy, move, ask | Handle local file originals |
| `instagram.username` | string | Instagram username |
| `instagram.password` | string | Instagram password |

Use dot-notation for nested keys: `ascli config set instagram.username myuser`

---

## ascli providers

Manage transcription providers.

```bash
ascli providers list                   # Show available providers
ascli providers list --json            # Output as JSON
ascli providers test                   # Test active provider
ascli providers test <name>            # Test a specific provider
```

---

## ascli onboard

Interactive setup wizard. Configures providers, API keys, preferences.

```bash
ascli onboard                          # First-time setup
ascli onboard --force                  # Re-run everything
ascli onboard --skip-deps              # Skip dependency check
ascli onboard --force --skip-deps      # Reconfigure, skip deps
```

**Note:** This is interactive — it takes over the terminal with arrow-key selectors. Don't run it programmatically.

---

## ascli doctor

Run diagnostic checks. Reports on dependencies, config, installation, and updates.

```bash
ascli doctor
```

Output includes everything needed for debugging. Suggest this when users report issues.

---

## ascli update

Update ascli to the latest version.

```bash
ascli update                           # Update to latest
ascli update --check                   # Check without installing
ascli update --force                   # Force update (stashes local changes)
```

---

## ascli --version

```bash
ascli --version
# Output: ascli v0.4.0
```

---

## ascli --help

```bash
ascli --help                           # All commands
ascli transcribe --help                # Command-specific help
```

---

## Shell Completion

```bash
ascli --install-completion             # Install tab completion for your shell
```

Restart your shell after installing.
