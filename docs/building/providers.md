# Providers

**Last updated:** 2026-03-26

## Available Providers

| Name | API | Status | Best For |
|------|-----|--------|----------|
| openai | Whisper API | Active (default) | General purpose, multilingual |
| openrouter | OpenRouter | Planned | Model flexibility, cost options |
| elevenlabs | ElevenLabs STT | Planned | TBD |
| sargam | Sargam AI | Planned | Indic languages |
| local | whisper.cpp / faster-whisper | Planned | Offline, privacy, no API cost |

## Adding a Provider

1. Create `src/anyscribecli/providers/<name>.py`
2. Implement `TranscriptionProvider` from `base.py`:
   - `name` property returning the provider name
   - `transcribe(audio_path, language)` returning `TranscriptResult`
3. Add entry to `PROVIDER_REGISTRY` in `providers/__init__.py`
4. Add any required env vars (e.g., `<NAME>_API_KEY`)
5. Update the onboarding wizard to prompt for the new key
6. Update this doc

## Provider Interface

```python
class TranscriptionProvider(ABC):
    @property
    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    def transcribe(self, audio_path: Path, language: str = "auto") -> TranscriptResult: ...
```

## TranscriptResult Fields

- `text`: Full transcript text
- `language`: Detected or specified language code
- `segments`: List of `{id, start, end, text}` dicts (optional, for timestamped output)
- `duration`: Audio duration in seconds
- `word_count`: Total word count
