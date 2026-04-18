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
| **Languages** | 99 | 89 | 92 | 23 Indian + English | Model-dependent | 99 |
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

Fast, accurate speech-to-text with native speaker diarization and Hindi Latin script (`hi-Latn`) support. **The default provider for diarization** — scribe auto-routes `--diarize` to Deepgram when configured.

```bash
scribe config set deepgram_api_key YOUR_KEY    # $200 free credit on signup
```

- **API key env var:** `DEEPGRAM_API_KEY`
- **Get a key:** [console.deepgram.com](https://console.deepgram.com/) — $200 free credit, no credit card required
- **Cost:** ~$0.30/hour
- **Model:** `nova-3` (auto-falls back to `nova` for `hi-Latn`, which isn't supported on nova-3 yet)
- **No file size limit** — processes files of any length in a single request (unlike OpenAI's 25MB limit)
- **Diarization:** Native — automatically detects the number of speakers from audio characteristics. No need to specify a speaker count.
- **Hindi Latin:** Set `--language hi-Latn` for romanized Hindi / Hinglish output

**Diarization language guide:**

| Your audio | Language flag | Why |
|-----------|--------------|-----|
| English (or mostly English with some Hindi) | None (auto-detect) | Auto-detect handles English well, Hindi words transcribed phonetically |
| Mostly Hindi / Hinglish (Hindi-English mix) | `--language hi-Latn` | Outputs romanized Hindi in Latin script, better code-switching |
| Pure Hindi (want Devanagari) | `--language hi` | Outputs in Devanagari script |

> **When to use:** Best choice for multi-speaker transcripts (meetings, interviews, podcasts). Handles long recordings (3+ hours) without chunking. Excellent for Hinglish content with `--language hi-Latn`. This is the provider scribe auto-selects when you use `--diarize`.

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

> **Also needs `ffmpeg`** on your system PATH. scribe uses ffmpeg to pre-process audio before handing it to Whisper — if ffmpeg isn't installed, local transcription will fail even after setup. Install via `brew install ffmpeg` (macOS), `winget install Gyan.FFmpeg` (Windows), or your distro's package manager (Linux).

**Setup is a single action** — pick whichever path fits your workflow; all four do the same thing:

```bash
scribe local setup --model base
```

or in the Web UI, either:
- **First-run onboarding wizard** (opens automatically on your first `scribe ui` launch) — pick "local" as your provider, or say Yes to the "Also enable offline transcription?" step.
- **Settings → Providers → Local → "Set up local transcription"** at any time after onboarding.

or during the terminal wizard, answer **Yes** when `scribe onboard` asks *"Also enable offline/local transcription?"*.

Setup installs `faster-whisper` into the same Python environment as scribe, downloads the Whisper model you picked, and records it as your local default. After that, local transcription is fully offline.

**Recommended model:** `base` — good quality for most use cases, ~145 MB download, runs on modest CPUs. If a recording is critical (interviews, accents, lots of names), step up to `small` or `medium`.

**Switching the default model:**

```bash
scribe config set local_model small
```

or pick from the dropdown in the Web UI's Local provider panel. (The model has to be cached first — see next section.)

**Managing downloaded models** (after setup):

| Command | What it does |
|---------|--------------|
| `scribe model list` | Show all 5 sizes with cache status and disk usage |
| `scribe model pull small` | Download an additional model size |
| `scribe model rm tiny --yes` | Delete a cached model (`--yes` required — destructive) |
| `scribe model info large-v3` | Inspect a single size |

Or use the Models table inside **Settings → Providers → Local** in the Web UI.

**Model size guide:**

| Model | Download | RAM (peak) | Speed (CPU) | Quality |
|-------|----------|------------|-------------|---------|
| `tiny` | ~75 MB | ~400 MB | ~10x realtime | Lowest |
| `base` (recommended) | ~145 MB | ~600 MB | ~7x realtime | Good for most |
| `small` | ~480 MB | ~1.2 GB | ~4x realtime | Noticeably better than base |
| `medium` | ~1.5 GB | ~2.5 GB | ~2x realtime | Near-large for many languages |
| `large-v3` | ~3 GB | ~5 GB | ~1x realtime (CPU); fast on GPU | Highest |

- **GPU:** Automatically uses NVIDIA CUDA if available; falls back to CPU.
- **Env-var override:** `ASCLI_LOCAL_MODEL=small scribe "<url>"` wins over the configured default for one invocation.

**Removing local transcription** (uninstalls faster-whisper and deletes every cached model):

```bash
scribe local teardown --yes
```

or click **"Remove local transcription"** at the bottom of the Local provider panel in the Web UI.

> **When to use:** When you're offline, want zero cost, or have privacy concerns about sending audio to cloud APIs. CPU transcription on `base` runs roughly 7x faster than real time on modern laptops — a 10-minute podcast takes ~90 seconds to transcribe.

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

## Picking a language (Web UI)

The web UI (`scribe ui`) shows a per-provider language dropdown so you
don't have to guess the right code. Open the **Options** accordion on the
Transcribe page and the language input becomes a combobox listing every
language that provider supports — `auto` at the top, then the full list.
You can still type any code, including ones that aren't in the dropdown
(useful if a provider added a language we haven't refreshed yet).

OpenRouter is the exception: it accepts a prose instruction in the prompt
("Spanish", "French"), not a code, so the input stays free-text for that
provider.

The same dropdown drives the **Default language** field on the Settings
page — it follows whichever provider you pick as default.

## Diarization Auto-Routing

When you use `--diarize` without specifying a provider (`-p`), scribe automatically switches to **Deepgram** if a Deepgram API key is configured. This is because Deepgram handles large files natively (no chunking needed) and produces the most consistent speaker labels across long recordings.

To override and use a specific provider for diarization:

```bash
scribe "url" --diarize --provider openai
```

> **Web UI naming:** "Diarize" appears as a `Multi-speaker` toggle in `scribe ui` and the `diarized` output format is labelled `with-speaker-labels` — the underlying behavior is identical.
