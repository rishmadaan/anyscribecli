---
summary: Compare transcription providers — features, languages, pricing, and when to use each.
read_when:
  - Choosing which provider to use
  - Transcribing in a specific language
  - Comparing cost vs accuracy
  - Setting up a new provider
---

# Providers

ascli supports 5 transcription providers. Here's how they compare and when to use each.

## Quick Comparison

| | OpenAI Whisper | ElevenLabs Scribe | Sarvam AI | OpenRouter | Local |
|---|---|---|---|---|---|
| **Best for** | General purpose | High accuracy | Indian languages | Model flexibility | Offline / free |
| **Languages** | 99 | 99 | 22 Indian + English | Model-dependent | 99 |
| **Timestamps** | Segment-level | Word-level | No (REST API) | No | Segment-level |
| **Pricing** | ~$0.36/hr | ~$0.22–0.40/hr | ~$0.35/hr | Varies by model | Free |
| **File limit** | 25 MB (auto-chunked) | 3 GB | 30s (auto-chunked) | ~context window | RAM only |
| **Offline** | No | No | No | No | Yes |
| **API key** | Required | Required | Required | Required | Not needed |

## Provider Details

### OpenAI Whisper (default)

The most widely used speech-to-text API. Good accuracy across most languages. Segment-level timestamps included.

```bash
ascli config set provider openai
```

- **API key env var:** `OPENAI_API_KEY`
- **Get a key:** [platform.openai.com/api-keys](https://platform.openai.com/api-keys)
- **Cost:** ~$0.006 per minute ($0.36/hour)
- **File limit:** 25 MB — ascli automatically chunks larger files into 18-minute segments
- **Model:** `whisper-1`

> **When to use:** Good default for most use cases. Best balance of cost, accuracy, and language coverage.

### ElevenLabs Scribe

High-accuracy transcription with word-level timestamps and optional speaker diarization (up to 32 speakers).

```bash
ascli config set provider elevenlabs
```

- **API key env var:** `ELEVENLABS_API_KEY`
- **Get a key:** [elevenlabs.io/app/settings/api-keys](https://elevenlabs.io/app/settings/api-keys)
- **Cost:** ~$0.22–0.40/hour depending on plan
- **File limit:** 3 GB (very generous)
- **Model:** `scribe_v1` (Scribe v2 also available)

> **When to use:** When you need the highest accuracy, word-level timestamps, or speaker identification. Slightly cheaper than OpenAI for high volumes.

### Sarvam AI

Specialized for Indian languages. Supports 22 Indian languages plus English with Indian accent optimization. Good for code-mixed audio (e.g., Hindi-English).

```bash
ascli config set provider sargam
```

- **API key env var:** `SARGAM_API_KEY`
- **Get a key:** [dashboard.sarvam.ai](https://dashboard.sarvam.ai)
- **Cost:** ~$0.35/hour; free tier: ~$12 in credits
- **File limit:** REST API limited to 30 seconds — ascli automatically chunks audio into 30-second segments
- **Model:** `saaras:v2`
- **Supported languages:** Hindi, Tamil, Telugu, Kannada, Malayalam, Bengali, Gujarati, Marathi, Punjabi, Odia, Assamese, Urdu, Sanskrit, and more

> **When to use:** Transcribing content in Indian languages. Significantly better than Whisper for Hindi, Tamil, Telugu, etc. Not suited for non-Indian languages.

### OpenRouter

Access to various AI models through a unified API. Since OpenRouter doesn't have a dedicated speech-to-text endpoint, this uses audio-capable chat models (like GPT-4o-audio-preview) with a transcription prompt.

```bash
ascli config set provider openrouter
```

- **API key env var:** `OPENROUTER_API_KEY`
- **Get a key:** [openrouter.ai/keys](https://openrouter.ai/keys)
- **Cost:** Varies by model (per-token pricing, generally more expensive than dedicated STT)
- **File limit:** Constrained by model context window
- **No timestamps** — returns plain text only
- **Model override:** Set `OPENROUTER_MODEL` env var to choose a model (default: `openai/gpt-4o-audio-preview`)

> **When to use:** When you need a specific model that's only available on OpenRouter. Not recommended as a primary transcription provider — dedicated STT APIs are faster, cheaper, and more accurate.

### Local (faster-whisper)

Runs entirely on your machine. No API key, no internet connection, no cost. Uses faster-whisper, a CTranslate2-based reimplementation of OpenAI Whisper that's up to 4x faster.

```bash
ascli config set provider local
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
ascli config set provider elevenlabs
```

Override for a single transcription:

```bash
ascli transcribe <url> --provider local
```

## Adding API Keys

The onboarding wizard (`ascli onboard`) asks for API keys. To add more later:

Edit `~/.anyscribecli/.env` directly:

```bash
OPENAI_API_KEY=sk-...
ELEVENLABS_API_KEY=xi-...
OPENROUTER_API_KEY=sk-or-...
SARGAM_API_KEY=...
```

Or re-run onboarding:

```bash
ascli onboard --force
```

Test that a provider works:

```bash
ascli providers test elevenlabs
```
