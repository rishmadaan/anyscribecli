# Command Reference

## ascli onboard

Interactive setup wizard. Creates configuration and workspace.

```bash
ascli onboard           # first-time setup
ascli onboard --force   # re-run setup
```

## ascli transcribe

Download and transcribe a video/audio URL.

```bash
ascli transcribe <url>
```

### Options

| Flag | Short | Description |
|------|-------|-------------|
| `--provider` | `-p` | Override transcription provider (e.g., `openai`) |
| `--language` | `-l` | Language code (`en`, `es`, `hi`, etc.). Default: `auto` |
| `--json` | `-j` | Output result as JSON for scripting/AI agents |
| `--keep-media` | | Keep the downloaded audio file |
| `--quiet` | `-q` | Suppress progress output |

### Examples

```bash
# Basic transcription
ascli transcribe https://youtube.com/watch?v=dQw4w9WgXcQ

# Force a specific language
ascli transcribe https://youtube.com/watch?v=abc123 --language es

# JSON output for scripting
ascli transcribe https://youtube.com/watch?v=abc123 --json

# Keep the audio file
ascli transcribe https://youtube.com/watch?v=abc123 --keep-media
```

### JSON Output Format

When using `--json`, the output is:

```json
{
  "success": true,
  "file": "/path/to/transcript.md",
  "title": "Video Title",
  "platform": "youtube",
  "duration": "12:34",
  "language": "en",
  "word_count": 1500,
  "provider": "openai"
}
```

## ascli --version

Show the current version.

```bash
ascli --version
```

## Shell Completion

Install shell completion for your shell:

```bash
ascli --install-completion
```
