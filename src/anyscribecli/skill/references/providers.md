# Transcription Providers

scribe supports 6 providers. Each has different strengths.

## Quick Comparison

| | OpenAI Whisper | Deepgram Nova | ElevenLabs Scribe | Sarvam AI | OpenRouter | Local |
|---|---|---|---|---|---|---|
| **Best for** | General purpose | Diarization + Hinglish | Highest accuracy | Indian languages | Model variety | Offline / free |
| **Languages** | 99 | 36+ | 99 | 22 Indian + English | Varies | 99 |
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

- **Model:** nova-3
- **Cost:** ~$0.005/min ($0.30/hr). $200 free credit on signup.
- **Diarization:** Native — use `--diarize` flag for per-speaker labels
- **Hindi Latin:** Use `--language hi-Latn` for romanized Hindi (Hinglish) output
- **Get key:** https://console.deepgram.com/

**When to recommend:** Best for multi-speaker transcripts (meetings, interviews, podcasts). Ideal for Hinglish content with `--language hi-Latn`. Fast and accurate diarization.

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

Runs entirely on-device. No API key, no internet, no cost.

- **Engine:** faster-whisper (CTranslate2-based, up to 4x faster than original Whisper)
- **Models:** tiny, base (default), small, medium, large-v3
- **Model override:** Set `ASCLI_LOCAL_MODEL` env var
- **GPU:** Auto-detects NVIDIA CUDA. Falls back to CPU.
- **First run:** Model downloads from Hugging Face (~150 MB for base, ~3 GB for large-v3)
- **Install:** `pip install faster-whisper`

### Model sizes

| Model | Size | Speed (CPU) | Accuracy | RAM |
|-------|------|-------------|----------|-----|
| tiny | 75 MB | Very fast | Lower | ~1 GB |
| base | 150 MB | Fast | Good | ~1 GB |
| small | 500 MB | Medium | Better | ~2 GB |
| medium | 1.5 GB | Slow | High | ~5 GB |
| large-v3 | 3 GB | Very slow | Highest | ~10 GB |

**When to recommend:** Offline use, zero cost, privacy concerns, or testing without an API key. CPU is slower (2–5x real-time for base). GPU is fast.

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
