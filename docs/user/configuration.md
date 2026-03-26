# Configuration

## Files

| File | Location | Purpose |
|------|----------|---------|
| `config.yaml` | `~/.anyscribecli/config.yaml` | All settings |
| `.env` | `~/.anyscribecli/.env` | API keys |

## config.yaml Options

```yaml
provider: openai        # Transcription provider (openai, openrouter, elevenlabs, sargam)
language: auto           # Default language (auto, en, es, hi, etc.)
keep_media: false        # Keep downloaded audio/video files
output_format: clean     # Transcript format (clean, timestamped)
instagram:
  username: ""           # Instagram username (for downloading reels/posts)
  password: ""           # Instagram password
```

### provider

The transcription API to use. Default: `openai`.

Available providers:
- `openai` — OpenAI Whisper API (default, general purpose)
- More providers coming: `openrouter`, `elevenlabs`, `sargam`, local models

### language

Language for transcription. Default: `auto` (auto-detect).

Use ISO 639-1 codes: `en`, `es`, `fr`, `hi`, `ar`, `zh`, `ja`, etc.

### keep_media

Whether to keep the downloaded audio file alongside the transcript. Default: `false`.

When `true`, audio files are saved to `~/.anyscribecli/workspace/media/YYYY-MM-DD/`.

### output_format

How to format the transcript. Default: `clean`.

- `clean` — plain text transcript
- `timestamped` — transcript with segment timestamps (planned)

## Environment Variables (.env)

```
OPENAI_API_KEY=sk-...
```

Each provider requires its own API key. The onboarding wizard prompts for the active provider's key.

## Workspace Structure

```
~/.anyscribecli/workspace/
├── .obsidian/                    # Obsidian configuration
├── _index.md                     # Master index (newest first)
├── sources/
│   ├── youtube/YYYY-MM-DD/       # YouTube transcripts by date
│   └── instagram/YYYY-MM-DD/     # Instagram transcripts by date
├── daily/YYYY-MM-DD.md           # Daily processing logs
└── media/YYYY-MM-DD/             # Audio files (if keep_media=true)
```
