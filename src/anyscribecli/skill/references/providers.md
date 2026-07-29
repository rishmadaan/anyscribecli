# Transcription Providers

scribe supports 7 providers. Each has different strengths.

## Quality presets (prefer this over picking a provider)

Most users should set `quality` instead of a provider — it picks the provider.
Recommend `--quality` first; only name a provider when the user wants a specific one.

| `--quality` | Picks | Best for |
|-------------|-------|----------|
| `balanced` (default) | Deepgram `nova-3` | Strong accuracy + speaker labels |
| `accuracy` | ElevenLabs `scribe_v2` | Highest accuracy, primarily-English |
| `cost` | Groq `whisper-large-v3-turbo` | Cheapest + fastest (~$0.04/hr) |
| `free` | Local faster-whisper | Offline, $0 |

`--provider` overrides the tier. If the tier's provider has no key, scribe falls back to the configured provider.

## Picking a model within a provider

Every cloud provider has a small list of pickable models. **The first is the default** — most users never touch this. Three ways to change it:

```bash
scribe "url" -p openai -m gpt-transcribe             # this run only
scribe config set provider_models.openai gpt-transcribe   # persistent, per provider
scribe providers list --json                          # what's in effect + alternatives
```

Precedence: `-m` > `provider_models.<provider>` in config > provider default.

| Provider | Default | Also available |
|---|---|---|
| `openai` | `whisper-1` | `gpt-transcribe`, `gpt-4o-transcribe`, `gpt-4o-mini-transcribe` |
| `deepgram` | `nova-3` | — (single model) |
| `elevenlabs` | `scribe_v2` | — (single model) |
| `sargam` | `saaras:v3` | `saaras:v2.5` (legacy) |
| `groq` | `whisper-large-v3-turbo` | `whisper-large-v3` |
| `openrouter` | `openai/gpt-audio-mini` | 5 listed below, **plus any audio-capable OpenRouter slug** |
| `local` | — | Sizes are downloaded, not picked with `-m`. See the local section. |

Unknown models are rejected up front with the valid list. `openrouter` is the exception — any slug passes through and only fails at the API.

> **Timestamps warning.** Only `whisper-1` (of the OpenAI models), `deepgram`, `elevenlabs`, `groq`, and `local` return segment timestamps. `gpt-transcribe`, `gpt-4o-transcribe`, `gpt-4o-mini-transcribe`, `sargam`, and `openrouter` return plain text — with `output_format: timestamped` or `diarized` you get paragraphs and no `[mm:ss]` markers. Check `scribe config show` before pinning one.

## Quick Comparison

| | OpenAI Whisper | Deepgram Nova | ElevenLabs Scribe | Sarvam AI | Groq | OpenRouter | Local |
|---|---|---|---|---|---|---|---|
| **Best for** | General purpose | Diarization + Hinglish | Highest accuracy | Indian languages | Cheapest + fastest | Model variety | Offline / free |
| **Languages** | 99 | 89 | 90+ | 23 Indian + English | 99 | Varies | 99 |
| **Timestamps** | Segment-level (`whisper-1` only) | Word-level | Word-level | No | Segment-level | No | Segment-level |
| **Diarization** | Yes (`--diarize`) | Yes (`--diarize`) | No | No (Sarvam Batch API only — not integrated) | No | No | No |
| **Cost** | ~$0.18–0.36/hr (by model) | ~$0.30/hr | ~$0.22–0.40/hr | ~$0.35/hr | ~$0.04/hr | Varies | Free |
| **File limit** | 25 MB | No hard limit | 25 MB | 30 sec | 25 MB | 25 MB | RAM only |
| **Offline** | No | No | No | No | No | No | Yes |
| **API key env** | `OPENAI_API_KEY` | `DEEPGRAM_API_KEY` | `ELEVENLABS_API_KEY` | `SARGAM_API_KEY` | `GROQ_API_KEY` | `OPENROUTER_API_KEY` | None |
| **Quality tier** | — | `balanced` | `accuracy` | — | `cost` | — | `free` |

## OpenAI Whisper (provider: `openai`)

Default provider. Reliable, well-documented, good across most languages. Supports diarization. Four pickable models — this is the only provider where the model choice really matters.

- **Default model:** `whisper-1`
- **Auto-chunking:** Files >25 MB split into 18-min segments (all models share the 25 MB limit). Diarize mode uses server-side chunking.
- **Diarization:** Yes — `--diarize` routes to `gpt-4o-transcribe-diarize` automatically, whatever model is pinned. Not part of the picker.
- **Get key:** https://platform.openai.com/api-keys

| Model | Cost | Segment timestamps | Notes |
|---|---|---|---|
| `whisper-1` **(default)** | $0.006/min (~$0.36/hr) | **Yes** | The only OpenAI model that returns timestamps — that's why it's still the default |
| `gpt-transcribe` | $0.0045/min (~$0.27/hr) | No | OpenAI's newest and recommended file-transcription model (released 2026-07-28). Roughly half Whisper's error rate in OpenAI's benchmarks, and 25% cheaper |
| `gpt-4o-transcribe` | $0.006/min | No | Older 4o-family model; `gpt-transcribe` beats it at a lower price ($0.0045) |
| `gpt-4o-mini-transcribe` | $0.003/min | No | Cheapest OpenAI option, lowest accuracy of the three |

**When to recommend:** Default choice. Best cost/accuracy/language balance. Use `--diarize` for multi-speaker content.

**When to recommend `gpt-transcribe`:** the user wants `clean` output (the default format) and asks for better accuracy, lower cost, or both. Do **not** suggest it if their `output_format` is `timestamped` or `diarized`, or if they want `[mm:ss]` markers — it can't produce them (`verbose_json` is unsupported), and the output silently falls back to plain text.

> OpenAI also shipped `gpt-live-transcribe`. It's a realtime/streaming Realtime-API model; scribe transcribes files, so it isn't supported and isn't in the picker.

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

- **Model:** scribe_v2 (top-accuracy model; replaced scribe_v1 which ElevenLabs removed 2026-07-09)
- **Cost:** ~$0.22–0.40/hr depending on plan
- **Features:** Word-level timestamps, up to 32 speaker identification
- **Get key:** https://elevenlabs.io/app/settings/api-keys

**When to recommend:** User needs highest accuracy or precise word-level timestamps. This is what the `accuracy` quality tier selects (the default is `balanced` → Deepgram).

## Sarvam AI (provider: `sargam`)

Specialized for Indian languages. Dramatically better than Whisper for Hindi, Tamil, Telugu, and 19 other Indian languages.

- **Default model:** `saaras:v3` — Sarvam's Feb-2026 flagship, on `/speech-to-text` with `mode=translate`. Notably better accuracy across the 22 Indic languages than v2.5.
- **Legacy model:** `saaras:v2.5` — the older `/speech-to-text-translate` endpoint, which Sarvam has marked deprecated. Pin it only if the user explicitly wants the old endpoint: `scribe config set provider_models.sargam saaras:v2.5`
- **Cost:** ~$0.35/hr; free tier ~$12 in credits
- **Supported:** Hindi, Tamil, Telugu, Kannada, Malayalam, Bengali, Gujarati, Marathi, Punjabi, Odia, Assamese, Urdu, Sanskrit, and more
- **Chunking:** sync API limited to 30 seconds — scribe auto-chunks into 30-sec segments (unchanged on v3)
- **Behavior:** both models translate to English; v3 is the same behavior, better accuracy
- **Get key:** https://dashboard.sarvam.ai

**When to recommend:** Any content in Indian languages. Handles code-mixed audio (e.g., Hindi-English) well. Not suited for non-Indian languages. Leave the model on `saaras:v3`.

## Groq (provider: `groq`)

Cheapest and fastest cloud option. Runs Whisper `large-v3-turbo` on Groq accelerators; OpenAI-compatible output (segment timestamps included).

- **Default model:** `whisper-large-v3-turbo` — cheapest and fastest
- **Also available:** `whisper-large-v3` — higher accuracy, and Groq allows a larger upstream file limit for it. Pin with `-m whisper-large-v3` when the turbo output is missing words.
- **Cost:** ~$0.04/hr — the cheapest cloud provider
- **Chunking:** 25 MB auto-chunked (same as OpenAI)
- **Diarization:** No — use the `accuracy`/`balanced` tier or `--provider deepgram`
- **Get key:** https://console.groq.com/keys
- **Quick setup:** `scribe config set groq_api_key gsk-...`

**When to recommend:** The `cost` quality tier maps here. Bulk/low-cost transcription where speaker labels aren't needed.

## OpenRouter (provider: `openrouter`)

Routes to various AI models via a unified API. Uses audio-capable chat models with a transcription prompt.

- **Default model:** `openai/gpt-audio-mini`
- **Listed models:** `openai/gpt-audio-mini`, `google/gemini-2.5-flash-lite`, `google/gemini-2.5-flash`, `google/gemini-3-flash-preview`, `mistralai/voxtral-small-24b-2507`, `openai/gpt-audio`
- **Any slug works:** OpenRouter is the one provider where `-m` isn't validated — pass any audio-capable slug and scribe forwards it. A wrong slug fails at the API (404), not at scribe.
- **Env var:** `OPENROUTER_MODEL` still works as a default, but `-m` and `provider_models.openrouter` both win over it
- **Cost:** Per-token pricing, generally more expensive than dedicated STT
- **No timestamps** — returns plain text only
- **Get key:** https://openrouter.ai/keys

> **The old default is gone.** `openai/gpt-4o-audio-preview` was removed from OpenRouter — requests to it now 404. If a user has it pinned (config or `OPENROUTER_MODEL`), clear the pin or set a current slug.

**When to recommend:** Only when user needs a specific model available through OpenRouter. Not recommended as primary — dedicated STT APIs are faster, cheaper, more accurate.

## Local / faster-whisper (provider: `local`)

Runs entirely on-device. No API key, no internet, no cost. **Opt-in** — nothing is installed or downloaded unless the user runs setup.

- **Engine:** faster-whisper (CTranslate2-based, up to 4x faster than original Whisper)
- **Recommended model:** `base` (~145 MB, good quality for most use cases)
- **All sizes:** `tiny`, `base`, `small`, `medium`, `large-v3`, `large-v3-turbo`, `distil-large-v3.5`
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
| `large-v3-turbo` | ~1.6 GB | ~3 GB | ~6x realtime | near `large-v3`, all languages — best quality-per-second on CPU |
| `distil-large-v3.5` | ~1.5 GB | ~2.8 GB | ~6x realtime | near `large-v3` **for English**; weaker multilingual |

**Default guidance:** `base`. Only escalate if the user specifically mentions accents, low-quality audio, critical recordings, or a non-English language the user cares about — try `small` first, then `large-v3-turbo`, which is roughly `large-v3` quality at ~6x the CPU speed and half the download. Pick `distil-large-v3.5` only for English-only workloads; it's weaker on other languages. Reserve `large-v3` for a GPU or when nothing else is good enough — on CPU it's ~1x realtime.

### Cache management (after setup)

| Task | Command |
|------|---------|
| See what's cached | `scribe model list --json` |
| Add another size | `scribe model pull <size> --json` |
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
scribe transcribe "url" -p openai -m gpt-transcribe    # provider + model
```

**Pin a model for a provider:**
```bash
scribe config set provider_models.openai gpt-transcribe
scribe providers list                                   # confirm what's in effect
```

**Add/update API keys:**
```bash
scribe config set deepgram_api_key YOUR_KEY     # Quick — stored in .env
scribe onboard --force                           # Interactive — re-enter keys
```

Or edit `~/.anyscribecli/.env` directly (never display this file to the user).

**Diarization auto-routing:** When `--diarize` is used without `-p`, scribe auto-switches to Deepgram if configured. Deepgram handles large files natively with consistent speaker labels.
