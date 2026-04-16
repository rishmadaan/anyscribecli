---
summary: Compare transcription providers — features, languages, pricing, and when to use each.
read_when:
  - Choosing which provider to use
  - Transcribing in a specific language
  - Comparing cost vs accuracy
  - Setting up a new provider
---

# Providers

scribe supports 6 transcription providers. Here's how they compare and when to use each.

## Quick Comparison

| | OpenAI Whisper | Deepgram Nova | ElevenLabs Scribe | Sarvam AI | OpenRouter | Local |
|---|---|---|---|---|---|---|
| **Best for** | General purpose | Diarization (auto-selected) + Hinglish | High accuracy | Indian languages | Model flexibility | Offline / free |
| **Languages** | 99 | 36+ | 99 | 22 Indian + English | Model-dependent | 99 |
| **Timestamps** | Segment-level | Word-level | Word-level | No (REST API) | No | Segment-level |
| **Diarization** | Yes (`--diarize`) | Yes (`--diarize`) | No (via scribe) | Yes (`--diarize`) | No | No |
| **Pricing** | ~$0.36/hr | ~$0.30/hr | ~$0.22–0.40/hr | ~$0.35/hr | Varies by model | Free |
| **File limit** | 25 MB (auto-chunked) | No hard limit | 25 MB (auto-chunked) | 30s (auto-chunked) | 25 MB (auto-chunked) | RAM only |
| **Offline** | No | No | No | No | No | Yes |
| **API key** | Required | Required | Required | Required | Required | Not needed |

## Provider Details

### OpenAI Whisper (default)

The most widely used speech-to-text API. Good accuracy across most languages. Segment-level timestamps included.

```bash
scribe config set provider openai
```

- **API key env var:** `OPENAI_API_KEY`
- **Get a key:** [platform.openai.com/api-keys](https://platform.openai.com/api-keys)
- **Cost:** ~$0.006 per minute ($0.36/hour)
- **File limit:** 25 MB — scribe automatically chunks larger files into 18-minute segments
- **Model:** `whisper-1` (standard), `gpt-4o-transcribe-diarize` (with `--diarize`)
- **Diarization:** Yes — use `--diarize` flag to enable speaker-labeled transcripts

> **When to use:** Good default for most use cases. Best balance of cost, accuracy, and language coverage. Use `--diarize` for meetings and multi-speaker content.

### Deepgram Nova

Fast, accurate speech-to-text with native speaker diarization and Hindi Latin script (`hi-Latn`) support. Excellent for Hinglish (Hindi-English code-switching) transcription.

```bash
scribe config set provider deepgram
```

- **API key env var:** `DEEPGRAM_API_KEY`
- **Get a key:** [console.deepgram.com](https://console.deepgram.com/)
- **Cost:** ~$0.30/hour ($200 free credit on signup)
- **Model:** `nova-3`
- **Diarization:** Native — use `--diarize` flag
- **Hindi Latin:** Set `--language hi-Latn` for romanized Hindi output

> **When to use:** Best choice for multi-speaker transcripts (meetings, interviews, podcasts). Excellent for Hinglish content with `--language hi-Latn`. Native diarization is faster and more accurate than post-processing approaches.

### ElevenLabs Scribe

High-accuracy transcription with word-level timestamps and optional speaker diarization (up to 32 speakers).

```bash
scribe config set provider elevenlabs
```

- **API key env var:** `ELEVENLABS_API_KEY`
- **Get a key:** [elevenlabs.io/app/settings/api-keys](https://elevenlabs.io/app/settings/api-keys)
- **Cost:** ~$0.22–0.40/hour depending on plan
- **File limit:** The ElevenLabs API accepts up to 3 GB, but scribe chunks at 25 MB (same as OpenAI) for consistency
- **Model:** `scribe_v1`

> **When to use:** When you need the highest accuracy, word-level timestamps, or speaker identification. Slightly cheaper than OpenAI for high volumes.

### Sarvam AI

Specialized for Indian languages. Supports 22 Indian languages plus English with Indian accent optimization. Good for code-mixed audio (e.g., Hindi-English).

```bash
scribe config set provider sargam
```

- **API key env var:** `SARGAM_API_KEY`
- **Get a key:** [dashboard.sarvam.ai](https://dashboard.sarvam.ai)
- **Cost:** ~$0.35/hour; free tier: ~$12 in credits
- **File limit:** REST API limited to 30 seconds — scribe automatically chunks audio into 30-second segments
- **Model:** `saaras:v2`
- **Supported languages:** Hindi, Tamil, Telugu, Kannada, Malayalam, Bengali, Gujarati, Marathi, Punjabi, Odia, Assamese, Urdu, Sanskrit, and more

> **When to use:** Transcribing content in Indian languages. Significantly better than Whisper for Hindi, Tamil, Telugu, etc. Not suited for non-Indian languages.

### OpenRouter

Access to various AI models through a unified API. Since OpenRouter doesn't have a dedicated speech-to-text endpoint, this uses audio-capable chat models (like GPT-4o-audio-preview) with a transcription prompt.

```bash
scribe config set provider openrouter
```

- **API key env var:** `OPENROUTER_API_KEY`
- **Get a key:** [openrouter.ai/keys](https://openrouter.ai/keys)
- **Cost:** Varies by model (per-token pricing, generally more expensive than dedicated STT)
- **File limit:** 25 MB (auto-chunked, same as OpenAI)
- **No timestamps** — returns plain text only
- **Model override:** Set `OPENROUTER_MODEL` env var to choose a model (default: `openai/gpt-4o-audio-preview`)

> **When to use:** When you need a specific model that's only available on OpenRouter. Not recommended as a primary transcription provider — dedicated STT APIs are faster, cheaper, and more accurate.

### Local (faster-whisper)

Runs entirely on your machine. No API key, no internet connection, no cost. Uses faster-whisper, a CTranslate2-based reimplementation of OpenAI Whisper that's up to 4x faster.

```bash
scribe config set provider local
```

**Setup:**
```bash
pip install faster-whisper
```

- **No API key needed**
- **Models:** `tiny`, `base` (default), `small`, `medium`, `large-v3`
- **Model override:** Set `ASCLI_LOCAL_MODEL` env var (default: `base`)
- **GPU:** Automatically uses NVIDIA CUDA if available. Falls back to CPU.
- **First run:** Model downloads automatically from Hugging Face (~150 MB for `base`, ~3 GB for `large-v3`)

> **When to use:** When you're offline, want zero cost, or have privacy concerns about sending audio to cloud APIs. CPU transcription is slower (expect ~2–5x real-time for `base` model). GPU is fast.

**Model size guide:**

| Model | Size | Speed (CPU) | Accuracy | RAM |
|-------|------|-------------|----------|-----|
| `tiny` | 75 MB | Very fast | Lower | ~1 GB |
| `base` | 150 MB | Fast | Good | ~1 GB |
| `small` | 500 MB | Medium | Better | ~2 GB |
| `medium` | 1.5 GB | Slow | High | ~5 GB |
| `large-v3` | 3 GB | Very slow | Highest | ~10 GB |

## Switching Providers

Change your default provider:

```bash
scribe config set provider elevenlabs
```

Override for a single transcription:

```bash
scribe "<url>" --provider local
```

## Adding API Keys

The quickest way to add an API key:

```bash
scribe config set deepgram_api_key YOUR_KEY
scribe config set openai_api_key sk-proj-...
scribe config set elevenlabs_api_key xi-...
scribe config set openrouter_api_key sk-or-...
scribe config set sargam_api_key YOUR_KEY
```

These are stored in `~/.anyscribecli/.env` automatically.

Or use the onboarding wizard:

```bash
scribe onboard --force
```

Or edit `~/.anyscribecli/.env` directly.

Test that a provider works:

```bash
scribe providers test elevenlabs
```

## Diarization Auto-Routing

When you use `--diarize` without specifying a provider (`-p`), scribe automatically switches to **Deepgram** if a Deepgram API key is configured. This is because Deepgram handles large files natively (no chunking needed) and produces the most consistent speaker labels across long recordings.

To override and use a specific provider for diarization:

```bash
scribe "url" --diarize --provider openai
```
