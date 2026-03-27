# Providers

**Last updated:** 2026-03-27 (v0.3.0)

## Available Providers

| Name | API | Status | Best For | Env Var |
|------|-----|--------|----------|---------|
| openai | Whisper API | Active (default) | General purpose, multilingual | `OPENAI_API_KEY` |
| elevenlabs | ElevenLabs Scribe v1 | Active | High accuracy, word timestamps, 99 langs | `ELEVENLABS_API_KEY` |
| openrouter | OpenRouter chat API | Active | Model flexibility (audio-via-chat) | `OPENROUTER_API_KEY` |
| sargam | Sarvam AI REST API | Active | Indic languages (Hindi, Tamil, etc.) | `SARGAM_API_KEY` |
| local | faster-whisper | Active | Offline, free, CPU/GPU | None |

## Provider-Specific Notes

### OpenAI (`providers/openai.py`)
- Uses `whisper-1` model, `verbose_json` response format
- Returns segment-level timestamps
- 25MB file limit — auto-chunked into 18-min segments

### ElevenLabs (`providers/elevenlabs.py`)
- Uses `scribe_v1` model, `xi-api-key` auth header
- Returns word-level timestamps (grouped into ~30-word segments for readability)
- 3GB file limit — very generous

### OpenRouter (`providers/openrouter.py`)
- No dedicated STT endpoint — sends base64 audio to chat models
- Default model: `openai/gpt-4o-audio-preview` (override via `OPENROUTER_MODEL` env var)
- No timestamps returned — plain text only
- More expensive than dedicated STT APIs

### Sargam/Sarvam (`providers/sargam.py`)
- REST API limited to 30-second clips
- Auto-chunks audio into 30s segments (different from the standard 18-min Whisper chunks)
- `api-subscription-key` auth header
- Best for Indian languages; not suited for non-Indian languages

### Local (`providers/local.py`)
- Uses `faster-whisper` (CTranslate2-based, up to 4x faster than original Whisper)
- Auto-detects GPU (CUDA) or falls back to CPU with int8
- Default model: `base` (override via `ASCLI_LOCAL_MODEL` env var)
- Available models: tiny, base, small, medium, large-v3
- VAD filtering enabled for speed
- Requires: `pip install faster-whisper`

## Adding a Provider

1. Create `src/anyscribecli/providers/<name>.py`
2. Implement `TranscriptionProvider` from `base.py`:
   - `name` property returning the provider name
   - `transcribe(audio_path, language)` returning `TranscriptResult`
3. Add entry to `PROVIDER_REGISTRY` in `providers/__init__.py`
4. Add provider info to `PROVIDER_INFO` in `cli/onboard.py`
5. Add any required env vars (e.g., `<NAME>_API_KEY`)
6. Update `docs/user/providers.md` and `docs/user/commands.md`
7. Update this doc

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
- `segments`: List of `TranscriptSegment(id, start, end, text)` (for timestamped output)
- `duration`: Audio duration in seconds
- `word_count`: Total word count (auto-calculated if not set)
