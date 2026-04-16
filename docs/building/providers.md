# Providers

**Last updated:** 2026-04-16 (v0.7.2.3)

## Available Providers

| Name | API | Status | Best For | Env Var | Diarization |
|------|-----|--------|----------|---------|-------------|
| openai | Whisper / gpt-4o-transcribe-diarize | Active (default) | General purpose, multilingual | `OPENAI_API_KEY` | Yes |
| deepgram | Deepgram Nova-3 | Active | Diarization, Hinglish, hi-Latn | `DEEPGRAM_API_KEY` | Yes |
| elevenlabs | ElevenLabs Scribe v1 | Active | High accuracy, word timestamps, 99 langs | `ELEVENLABS_API_KEY` | No |
| openrouter | OpenRouter chat API | Active | Model flexibility (audio-via-chat) | `OPENROUTER_API_KEY` | No |
| sargam | Sarvam AI REST API | Active | Indic languages (Hindi, Tamil, etc.) | `SARGAM_API_KEY` | Yes |
| local | faster-whisper | Active | Offline, free, CPU/GPU | None | No |

## Provider-Specific Notes

### OpenAI (`providers/openai.py`)
- Uses `whisper-1` model (default) or `gpt-4o-transcribe-diarize` when `diarize=True`
- `verbose_json` response format, segment-level timestamps
- 25MB file limit — auto-chunked into 18-min segments (standard mode)
- Diarize mode: `gpt-4o-transcribe-diarize` model, 25MB upload limit applies (same as standard)
- Diarize response includes `speaker` field per segment
- **Note (v0.7.2):** `--diarize` auto-routes to Deepgram when no explicit `-p` is given and Deepgram key is configured. OpenAI diarize has a 25MB limit with no client-side chunking support for diarization — Deepgram handles large files natively.

### Deepgram (`providers/deepgram.py`)
- Uses `nova-3` model with `smart_format=true` (auto-falls back to `nova` for `hi-Latn` — nova-3 doesn't support that language yet)
- Raw audio POST to `https://api.deepgram.com/v1/listen`
- `Token` auth header (not `Bearer`)
- Native `diarize=true` query param — returns per-word speaker IDs
- Supports `hi-Latn` language code for romanized Hindi
- Response parsed from word-level: consecutive words by same speaker grouped into segments
- Without diarize: words grouped into ~30-word segments for timestamps

### ElevenLabs (`providers/elevenlabs.py`)
- Uses `scribe_v1` model, `xi-api-key` auth header
- Returns word-level timestamps (grouped into ~30-word segments for readability)
- ElevenLabs API accepts up to 3GB, but ascli chunks at 25MB (same `WHISPER_MAX_BYTES` threshold) for consistency

### OpenRouter (`providers/openrouter.py`)
- No dedicated STT endpoint — sends base64 audio to chat models
- Default model: `openai/gpt-4o-audio-preview` (override via `OPENROUTER_MODEL` env var)
- No timestamps returned — plain text only
- Auto-chunked at 25MB (same `WHISPER_MAX_BYTES` threshold as OpenAI/ElevenLabs)
- More expensive than dedicated STT APIs

### Sargam/Sarvam (`providers/sargam.py`)
- Uses `saaras:v2` model
- REST API limited to 30-second clips
- Auto-chunks audio into 30s segments (different from the standard 18-min Whisper chunks)
- `api-subscription-key` auth header
- Best for Indian languages; not suited for non-Indian languages
- Diarize support: `with_diarization=true` param, parses speaker turns from response
- Note: 30s chunks mean speaker IDs may restart per chunk — known limitation

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
    def transcribe(self, audio_path: Path, language: str = "auto", diarize: bool = False) -> TranscriptResult: ...
```

## TranscriptResult Fields

- `text`: Full transcript text
- `language`: Detected or specified language code
- `segments`: List of `TranscriptSegment(id, start, end, text, speaker)` (for timestamped/diarized output)
- `duration`: Audio duration in seconds
- `word_count`: Total word count (auto-calculated if not set)

## TranscriptSegment Fields

- `id`: Segment index
- `start`: Start time in seconds
- `end`: End time in seconds
- `text`: Segment text content
- `speaker`: Speaker label (e.g. "Speaker 0") or None if not diarized
