# Providers

**Last updated:** 2026-07-29

## Model Picker

Every cloud provider has a pickable model list in
`providers/__init__.py::PROVIDER_MODELS` (first entry = default; single-entry
lists render no picker; `OPEN_MODEL_PROVIDERS` marks openrouter as freeform).
Pin per-run with `--model/-m`, persistently via
`settings.provider_models` (`scribe config set provider_models.<provider> <model>`),
or in the Web UI (Transcribe + Settings). `get_provider(name, model)` validates
and sets `provider.model`; providers read `self.model or <default>`.

| Provider | Default | Also pickable | Notes |
|----------|---------|---------------|-------|
| openai | whisper-1 | gpt-transcribe, gpt-4o-transcribe, gpt-4o-mini-transcribe | Non-whisper models have **no segment timestamps** (json-only) — whisper-1 stays default for timestamped/diarized output; gpt-transcribe is cheaper ($0.0045/min) + more accurate for clean text |
| deepgram | nova-3 | — | hi-Latn still auto-routes to legacy `nova` |
| elevenlabs | scribe_v2 | — | |
| sargam | saaras:v3 | saaras:v2.5 | v3 on `/speech-to-text` + `mode=translate`; v2.5 pins the legacy deprecated endpoint |
| openrouter | openai/gpt-audio-mini | gemini flash family, voxtral, gpt-audio + any slug (freeform) | old default `gpt-4o-audio-preview` was removed by OpenRouter |
| groq | whisper-large-v3-turbo | whisper-large-v3 | |
| local | (settings.local_model) | tiny…large-v3, large-v3-turbo, distil-large-v3.5 | separate lifecycle: `scribe model pull`, HF cache |

## Language Lists

Per-provider supported-language lists live in `src/anyscribecli/providers/languages.py`
and are exposed via `GET /api/providers/{name}/languages`. The web UI's
language picker (Transcribe + Settings pages) consumes that endpoint and
renders a native HTML `<datalist>` — suggestions drop down, but free
typing is also accepted.

OpenRouter is the exception (`freeform: true`) — it accepts a prose
language instruction in the prompt rather than a code, so the UI shows a
plain text input for that provider.

To update a list when upstream changes, see CLAUDE.md → "Updating Provider
Language Lists".

## Available Providers

| Name | API | Status | Best For | Env Var | Diarization |
|------|-----|--------|----------|---------|-------------|
| openai | Whisper / gpt-4o-transcribe-diarize | Active (default) | General purpose, multilingual | `OPENAI_API_KEY` | Yes |
| deepgram | Deepgram Nova-3 | Active | Diarization, Hinglish, hi-Latn | `DEEPGRAM_API_KEY` | Yes |
| elevenlabs | ElevenLabs Scribe v2 | Active | Highest accuracy, word timestamps, 90+ langs | `ELEVENLABS_API_KEY` | No |
| openrouter | OpenRouter chat API | Active | Model flexibility (audio-via-chat) | `OPENROUTER_API_KEY` | No |
| sargam | Sarvam AI REST API | Active | Indic languages (Hindi, Tamil, etc.) | `SARGAM_API_KEY` | No (Batch API only, not integrated) |
| groq | Groq whisper-large-v3-turbo | Active | Cheapest + fastest cloud | `GROQ_API_KEY` | No |
| local | faster-whisper | Active | Offline, free, CPU/GPU | None | No |

## Quality Routing

`quality` (accuracy/balanced/cost/free) is a friendly alias that resolves to a
provider in `core/quality.py::apply_quality`, mirroring the `--diarize → deepgram`
auto-routing. `QUALITY_TIERS` maps: accuracy→elevenlabs, balanced→deepgram,
cost→groq, free→local. Precedence: explicit `--provider` → `--diarize` →
`quality` → configured provider. If the tier's provider has no key, it falls back
to the configured provider (graceful, keyless users still work).

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
- Uses `scribe_v2` model, `xi-api-key` auth header (migrated from `scribe_v1`, which ElevenLabs removed 2026-07-09; v2 is the current top-accuracy model)
- Returns word-level timestamps (grouped into ~30-word segments for readability)
- ElevenLabs API accepts up to 3GB, but ascli chunks at 25MB (same `WHISPER_MAX_BYTES` threshold) for consistency
- This is the provider the `accuracy` quality tier (default) selects

### OpenRouter (`providers/openrouter.py`)
- No dedicated STT endpoint — sends base64 audio to chat models
- Default model: `openai/gpt-audio-mini` (pin any slug via the model picker; `OPENROUTER_MODEL` env var still honored, pinned model wins)
- No timestamps returned — plain text only
- Auto-chunked at 25MB (same `WHISPER_MAX_BYTES` threshold as OpenAI/ElevenLabs)
- More expensive than dedicated STT APIs

### Sargam/Sarvam (`providers/sargam.py`)
- Uses `saaras:v3` on `/speech-to-text` with `mode=translate`, so output is an **English translation**, not verbatim Hindi/Hinglish (same behaviour as the legacy `/speech-to-text-translate` endpoint, which Sarvam deprecated and which a `saaras:v2.5` pin still reaches).
- REST sync API limited to 30 seconds **exclusive** — a clip of exactly 30.0s is rejected. `SARVAM_MAX_DURATION = 28` chunks just under the boundary (raised from 30 in 0.10.1 after `v2.5` enforced the limit strictly).
- Auto-chunks audio into 28s segments (different from the standard 18-min Whisper chunks)
- `api-subscription-key` auth header
- Best for Indian languages; not suited for non-Indian languages
- Diarize support: `with_diarization=true` param, parses speaker turns from response
- Note: 28s chunks mean speaker IDs may restart per chunk — known limitation
- **Future:** adopt Sarvam's batch API (no 30s cap, native diarization, 2hr/file) to escape sync chunking — see the [landscape audit](journal/2026-06-27-transcription-landscape-and-config-audit.md).

### Groq (`providers/groq.py`)
- Subclass of `OpenAIProvider` — Groq's STT API is OpenAI-compatible (same multipart request, `verbose_json` + segment timestamps, same response shape)
- Only overrides `name`, `API_URL` (`https://api.groq.com/openai/v1/audio/transcriptions`), `_get_api_key` (`GROQ_API_KEY`), and `MODEL` (`whisper-large-v3-turbo`)
- Chunking and `_parse_response` inherited unchanged
- Diarize path overridden to raise — Groq has no diarization model
- This is the provider the `cost` quality tier selects

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
