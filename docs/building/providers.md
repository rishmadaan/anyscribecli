# Providers

**Last updated:** 2026-07-29

## Model Picker

Every cloud provider has a pickable model list in
`providers/__init__.py::PROVIDER_MODELS` (first entry = default;
`OPEN_MODEL_PROVIDERS` marks openrouter as freeform). Read it through
`get_models(name, settings.extra_models)`, never `PROVIDER_MODELS` directly —
that merge is what makes user-added openrouter slugs visible in the pickers.
Pin per-run with `--model/-m`, persistently via
`settings.provider_models` (`scribe config set provider_models.<provider> <model>`),
or in the Web UI (Transcribe + Settings). `validate_model(name, model, extra)`
raises on an unknown model; `get_provider(name, model)` calls it and sets
`provider.model`; providers read `self.model or <default>`.

`settings.extra_models` is a `provider -> [slug]` map, **openrouter only** by
owner decision (`core/config_set.py` rejects every other key). Rationale: an
open-model provider forwards any slug, while a closed provider needs
response-parsing code per model, so its catalog belongs to a release.

| Provider | Default | Also pickable | Notes |
|----------|---------|---------------|-------|
| openai | gpt-transcribe | whisper-1, gpt-4o-transcribe, gpt-4o-mini-transcribe | Non-whisper models have **no segment timestamps** (json-only). `core/resolve.py` auto-switches to whisper-1 when `output_format ∈ {timestamped, diarized}` and no per-run `-m` was given |
| deepgram | nova-3 | nova-2 | hi-Latn still auto-routes to legacy `nova` |
| elevenlabs | scribe_v2 | — | scribe_v1 removed upstream 2026-07-09, excluded |
| sargam | saaras:v3 | — | always `/speech-to-text` + `mode=translate`; saaras:v2.5 and the legacy endpoint deleted, migration drops old pins |
| openrouter | openai/gpt-audio-mini | gemini flash family, voxtral, gpt-audio + any slug (freeform) + `extra_models.openrouter` | old default `gpt-4o-audio-preview` was removed by OpenRouter; `OPENROUTER_MODEL` env var removed in 0.15.0 |
| groq | whisper-large-v3-turbo | whisper-large-v3 | |
| local | (settings.local_model) | tiny…large-v3, large-v3-turbo, distil-large-v3.5 | `PROVIDER_MODELS["local"] = []`; separate lifecycle: `scribe model pull`, HF cache |

## Language Lists

Per-provider supported-language lists live in `src/anyscribe/providers/languages.py`
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
provider; `custom` is the sentinel meaning "respect `settings.provider`".
`QUALITY_TIERS` (`core/quality.py`) maps: accuracy→elevenlabs,
balanced→deepgram, cost→groq, free→local.

The whole ladder lives in **`core/resolve.py::resolve_run`** — one function, four
surfaces (CLI, batch, web, MCP). Precedence: explicit `--provider` → `--diarize`
→ `quality` tier → configured provider. It returns a `RunPlan(provider, model,
via, notes)`; `via` ∈ `flag | diarize | quality: <tier> | config`. Nothing else
should reimplement this ladder — that duplication is exactly what it replaced
(`apply_quality` is gone).

If the tier's provider has no key, `resolve_run` keeps `settings.provider` and
appends a WARNING note (keyless users still run, but the fallback is now visible
instead of silent).

**The provider→custom invariant:** any write that sets a provider also sets
`quality="custom"` in the same save — `core/config_set.py::set_value("provider", …)`
(CLI/web/MCP all route through it) and `core/onboard_headless.py`. Without it a
tier would silently re-override the user's choice on the next run.

## Provider-Specific Notes

### OpenAI (`providers/openai.py`)
- `MODEL = "gpt-transcribe"` (default) or `gpt-4o-transcribe-diarize` when `diarize=True`
- `NO_SEGMENT_MODELS` is the set `resolve_run` checks before falling back to `whisper-1` for timestamped/diarized output — keep it in sync when the catalog changes
- `verbose_json` response format (whisper-1 only; the gpt-* models are json-only), segment-level timestamps
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
- ElevenLabs API accepts up to 3GB, but anyscribe chunks at 25MB (same `WHISPER_MAX_BYTES` threshold) for consistency
- This is the provider the `accuracy` quality tier (default) selects

### OpenRouter (`providers/openrouter.py`)
- No dedicated STT endpoint — sends base64 audio to chat models
- Default model: `openai/gpt-audio-mini` (pin any slug via the model picker; `settings.extra_models["openrouter"]` keeps user slugs in the picker). The `OPENROUTER_MODEL` env var was removed in 0.15.0 — the pin supersedes it
- No timestamps returned — plain text only
- Auto-chunked at 25MB (same `WHISPER_MAX_BYTES` threshold as OpenAI/ElevenLabs)
- More expensive than dedicated STT APIs

### Sargam/Sarvam (`providers/sargam.py`)
- Always `saaras:v3` on `/speech-to-text` with `mode=translate`, so output is an **English translation**, not verbatim Hindi/Hinglish (same behaviour as the legacy `/speech-to-text-translate` endpoint, which Sarvam deprecated). That legacy path and `LEGACY_API_URL` are deleted; `core/migrate.py::maybe_migrate_sargam_model` drops a stale `saaras:v2.5` pin on first run.
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

1. Create `src/anyscribe/providers/<name>.py`
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
