# Transcription Providers

scribe supports 6 providers. Each has different strengths.

## Quick Comparison

| | OpenAI Whisper | Deepgram Nova | ElevenLabs Scribe | Sarvam AI | OpenRouter | Local |
|---|---|---|---|---|---|---|
| **Best for** | General purpose | Diarization + Hinglish | Highest accuracy | Indian languages | Model variety | Offline / free |
| **Languages** | 99 | 89 | 92 | 23 Indian + English | Varies | 99 |
| **Timestamps** | Segment-level | Word-level | Word-level | No | No | Segment-level |
| **Diarization** | Yes (`--diarize`) | Yes (`--diarize`) | No | Yes (`--diarize`) | No | No |
| **Cost** | ~$0.36/hr | ~$0.30/hr | ~$0.22–0.40/hr | ~$0.35/hr | Varies | Free |
| **File limit** | 25 MB | No hard limit | 25 MB | 30 sec | 25 MB | RAM only |
| **Offline** | No | No | No | No | No | Yes |
| **API key env** | `OPENAI_API_KEY` | `DEEPGRAM_API_KEY` | `ELEVENLABS_API_KEY` | `SARGAM_API_KEY` | `OPENROUTER_API_KEY` | None |

## OpenAI Whisper (provider: `openai`)

Default provider. Reliable, well-documented, good across most languages. Supports diarization.

- **Model:** whisper-1 (standard) or gpt-4o-transcribe-diarize (with `--diarize`)
- **Cost:** ~$0.006/min ($0.36/hr). A 10-min video costs ~6 cents.
- **Auto-chunking:** Files >25 MB split into 18-min segments (standard mode). Diarize mode uses server-side chunking.
- **Diarization:** Yes — use `--diarize` flag for speaker-labeled transcripts
- **Get key:** https://platform.openai.com/api-keys

**When to recommend:** Default choice. Best cost/accuracy/language balance. Use `--diarize` for multi-speaker content.

## Deepgram Nova (provider: `deepgram`)

Fast, accurate transcription with native speaker diarization and Hindi Latin script support.

- **Model:** nova-3 (auto-falls back to nova for hi-Latn, which isn't supported on nova-3 yet)
- **Cost:** ~$0.005/min ($0.30/hr). $200 free credit on signup, no credit card needed.
- **No file size limit** — processes files of any length in a single request
- **Diarization:** Native — automatically detects the number of speakers from audio. No need to specify a speaker count.
- **Hindi Latin:** Use `--language hi-Latn` for romanized Hindi (Hinglish) output — this is the recommended default for any Hindi multi-speaker content
- **Get key:** https://console.deepgram.com/
- **Quick setup:** `scribe config set deepgram_api_key YOUR_KEY`

**Language guide for diarization:**
- Mostly English (with some Hindi words) → no language flag needed, auto-detect works
- Mostly Hindi / Hinglish → `--language hi-Latn` for romanized Latin script
- Pure Hindi (Devanagari) → `--language hi`

**When to recommend:** Best for multi-speaker transcripts (meetings, interviews, podcasts). Handles long recordings (3+ hours) without chunking. Ideal for Hinglish content with `--language hi-Latn`. This is the provider scribe auto-selects when `--diarize` is used.

## ElevenLabs Scribe (provider: `elevenlabs`)

Premium accuracy with word-level timestamps and speaker diarization.

- **Model:** scribe_v1
- **Cost:** ~$0.22–0.40/hr depending on plan
- **Features:** Word-level timestamps, up to 32 speaker identification
- **Get key:** https://elevenlabs.io/app/settings/api-keys

**When to recommend:** User needs highest accuracy, wants to know who said what (speaker ID), or needs precise word-level timestamps.

## Sarvam AI (provider: `sargam`)

Specialized for Indian languages. Dramatically better than Whisper for Hindi, Tamil, Telugu, and 19 other Indian languages.

- **Model:** saaras:v2
- **Cost:** ~$0.35/hr; free tier ~$12 in credits
- **Supported:** Hindi, Tamil, Telugu, Kannada, Malayalam, Bengali, Gujarati, Marathi, Punjabi, Odia, Assamese, Urdu, Sanskrit, and more
- **Chunking:** REST API limited to 30 seconds — scribe auto-chunks into 30-sec segments
- **Get key:** https://dashboard.sarvam.ai

**When to recommend:** Any content in Indian languages. Handles code-mixed audio (e.g., Hindi-English) well. Not suited for non-Indian languages.

## OpenRouter (provider: `openrouter`)

Routes to various AI models via a unified API. Uses audio-capable chat models with a transcription prompt.

- **Default model:** openai/gpt-4o-audio-preview (override with `OPENROUTER_MODEL` env var)
- **Cost:** Per-token pricing, generally more expensive than dedicated STT
- **No timestamps** — returns plain text only
- **Get key:** https://openrouter.ai/keys

**When to recommend:** Only when user needs a specific model available through OpenRouter. Not recommended as primary — dedicated STT APIs are faster, cheaper, more accurate.

## Local / faster-whisper (provider: `local`)

Runs entirely on-device. No API key, no internet, no cost. **Opt-in** — nothing is installed or downloaded unless the user runs setup.

- **Engine:** faster-whisper (CTranslate2-based, up to 4x faster than original Whisper)
- **Recommended model:** `base` (~145 MB, good quality for most use cases)
- **All sizes:** `tiny`, `base`, `small`, `medium`, `large-v3`
- **Also needs:** `ffmpeg` on the system PATH (local setup does not install ffmpeg)
- **GPU:** auto-detects NVIDIA CUDA; falls back to CPU

### Setup — one command, one action

```bash
scribe local setup --model base --yes --json
```

`--model` is **required**. The CLI never picks a model silently. In a non-TTY (agent) context, `--yes` is also required. Setup:

1. Detects the install method (pipx / venv-pip / system pip).
2. Installs `faster-whisper` into the same Python env as scribe.
3. Downloads the chosen Whisper model from HuggingFace.
4. Persists `local_model` in `config.yaml`.

Idempotent — re-running with an already-set-up model just updates the default.

### Model sizes — use this to advise the user

| Size | Download | RAM (peak) | Relative speed (CPU) | Quality |
|------|----------|------------|----------------------|---------|
| `tiny` | ~75 MB | ~400 MB | ~10x realtime | lowest — only use for drafts |
| `base` **(recommended)** | ~145 MB | ~600 MB | ~7x realtime | good for most podcasts/interviews |
| `small` | ~480 MB | ~1.2 GB | ~4x realtime | noticeably better for accents / fast speech |
| `medium` | ~1.5 GB | ~2.5 GB | ~2x realtime | near-large for many languages |
| `large-v3` | ~3 GB | ~5 GB | ~1x realtime (CPU); fast on GPU | highest quality |

**Default guidance:** `base`. Only escalate if the user specifically mentions accents, low-quality audio, critical recordings, or a non-English language the user cares about (try `small` first; `medium` or `large-v3` only if `small` is insufficient).

### Cache management (after setup)

| Task | Command |
|------|---------|
| See what's cached | `scribe model list --json` |
| Add another size | `scribe model pull <size> --yes --json` |
| Delete a cached size | `scribe model rm <size> --yes --json` |
| Inspect a size | `scribe model info <size> --json` |
| Switch default model | `scribe config set local_model <size>` (must already be cached) |

### Teardown

```bash
scribe local teardown --yes --json
```

Uninstalls faster-whisper, deletes every cached model, resets `settings.provider` to `openai` if it was `local`.

**When to recommend local:** offline workflows, privacy-sensitive content, bulk processing where API cost matters, or users without API keys. Don't push it for casual one-off transcriptions — the API providers are simpler and the model download is big.

## Switching Providers

**Change default:**
```bash
scribe config set provider elevenlabs
```

**Override for one transcription:**
```bash
scribe transcribe "url" --provider local
```

**Add/update API keys:**
```bash
scribe config set deepgram_api_key YOUR_KEY     # Quick — stored in .env
scribe onboard --force                           # Interactive — re-enter keys
```

Or edit `~/.anyscribecli/.env` directly (never display this file to the user).

**Diarization auto-routing:** When `--diarize` is used without `-p`, scribe auto-switches to Deepgram if configured. Deepgram handles large files natively with consistent speaker labels.
