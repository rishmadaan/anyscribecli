---
summary: Compare transcription providers — features, languages, pricing, and when to use each.
read_when:
  - Choosing which provider to use
  - Choosing which model to use within a provider
  - Transcribing in a specific language
  - Comparing cost vs accuracy
  - Setting up a new provider
---

# Providers

anyscribe supports 7 transcription providers. Here's how they compare and when to use each.

> **Commands below use `anyscribe`.** The shorter aliases `scribe` and `ascli` work identically — swap in whichever you prefer.

> **Don't want to choose?** Use the **`quality`** setting — pick `accuracy`,
> `balanced`, `cost`, or `free` and anyscribe selects the provider for you. See
> [Quality presets](#quality-presets) below.

## Privacy — who sees your audio?

Worth knowing before you pick. anyscribe itself doesn't phone home — everything runs on your own machine — but your audio has to go wherever the transcription happens.

- **Local provider:** audio stays on your machine. Nothing leaves. Fully offline once the Whisper model is downloaded.
- **API providers (OpenAI / Deepgram / ElevenLabs / Sarvam / Groq / OpenRouter):** anyscribe sends your audio to the API you picked and nothing else. No intermediary, no third party, no anyscribe-operated cloud. Your trust boundary is exactly the provider you chose — same as if you called their API directly.
- **YouTube / Instagram source URLs:** downloading the video obviously requires internet, and the source host sees the request. The transcribed audio then follows the same rule above (stays local with the local provider; goes to the API provider otherwise).

If privacy is the main reason you're evaluating anyscribe, use the **Local** provider + local files for an end-to-end-offline pipeline.

## Quality presets

The easiest way to use anyscribe: pick **what you want** and it chooses the provider.

| `--quality` | Picks | Best for |
|-------------|-------|----------|
| `balanced` (default) | Deepgram `nova-3` | Strong accuracy + speaker labels |
| `accuracy` | ElevenLabs `scribe_v2` | Highest accuracy, primarily-English |
| `cost` | Groq `whisper-large-v3-turbo` | Cheapest + fastest cloud (~$0.04/hr) |
| `free` | Local faster-whisper | Offline, $0 |
| `custom` | Whatever your `provider` setting says | You picked a provider yourself |

```bash
anyscribe "<url>" --quality accuracy     # per run
anyscribe config set quality cost         # change the default
anyscribe config set provider sargam      # picks the provider directly (writes quality: custom)
```

**It's one knob, not two.** Either a tier picks the provider for you, or
`quality` is `custom` and your `provider` setting is used as-is. Setting a
provider — on the CLI, in the Web UI, or through MCP — writes `quality: custom`
in the same save, so your choice sticks instead of being overridden by the tier
on the next run.

If you pass `--provider` on a single run, it wins for that run only.

Each tier needs that provider's key (accuracy → `ELEVENLABS_API_KEY`, cost →
`GROQ_API_KEY`, …); `free` needs none. **If the key is missing, anyscribe warns and
falls back** to your configured provider rather than failing:

```
→ openai · gpt-transcribe (config)
    WARNING: quality 'balanced' wants deepgram but no DEEPGRAM_API_KEY is set — using openai instead
```

Run `anyscribe config` (no subcommand) any time to see which provider and model the
next run will actually use.

## Choosing a model within a provider

A **provider** is the company doing the transcribing. A **model** is the specific engine inside it. Each provider ships with a default model, so you can skip this section entirely and everything works.

Change it for one run:

```bash
anyscribe "<url>" -p openai -m gpt-transcribe
```

Or make it permanent:

```bash
anyscribe config set provider_models.openai gpt-transcribe
```

See what you have:

```bash
anyscribe config            # every provider, its model, and which one runs next
anyscribe providers list    # same model info, provider-focused
```

| Provider | Default model | Also available |
|----------|---------------|----------------|
| OpenAI | `gpt-transcribe` | `whisper-1`, `gpt-4o-transcribe`, `gpt-4o-mini-transcribe` |
| Deepgram | `nova-3` | `nova-2` (the previous generation) |
| ElevenLabs | `scribe_v2` | — only one |
| Sarvam | `saaras:v3` | — only one |
| Groq | `whisper-large-v3-turbo` | `whisper-large-v3` |
| OpenRouter | `openai/gpt-audio-mini` | Several listed, **plus any audio model on OpenRouter** |
| Local | — | Downloaded separately, see [Local](#local-faster-whisper) |

> **The one gotcha worth knowing: timestamps.** Some models return only plain text, with no record of *when* each sentence was said. This affects OpenAI's `gpt-transcribe`, `gpt-4o-transcribe`, and `gpt-4o-mini-transcribe`, plus Sarvam and OpenRouter generally.
>
> For OpenAI, anyscribe handles this for you: if your `output_format` is `timestamped` or `diarized` and the model can't do timestamps, it switches that run to `whisper-1` and prints a note. It only stands back if *you* named the model with `-m` — then you get exactly what you asked for, paragraphs and all. Sarvam and OpenRouter have no timestamped model to fall back to, so with those you simply get paragraphs.

> **Adding models OpenRouter offers but anyscribe doesn't list:**
>
> ```bash
> anyscribe config set extra_models.openrouter "qwen/qwen3-omni-flash"
> ```
>
> They join the pickers everywhere, marked `(custom)`. This works for OpenRouter
> only — it forwards any model name unchanged. The other providers' lists are
> curated per release because anyscribe needs code that understands each model's
> response format, so **"how do I add a model to Deepgram?" is answered by
> `anyscribe update`, not by config.**

> **In the Web UI:** a model dropdown appears on the **Transcribe** page once you explicitly pick a provider, and on the **Settings** page under your default provider. For OpenRouter it's a free-text box with your merged list as suggestions.

## Quick Comparison

| | OpenAI Whisper | Deepgram Nova | ElevenLabs Scribe | Sarvam AI | Groq | OpenRouter | Local |
|---|---|---|---|---|---|---|---|
| **Best for** | General purpose | Diarization (auto-selected) + Hinglish | Highest accuracy | Indian languages | Cheapest + fastest | Model flexibility | Offline / free |
| **Languages** | 99 | 89 | 90+ | 23 Indian + English | 99 | Model-dependent | 99 |
| **Timestamps** | Segment-level (`whisper-1`; auto-used when needed) | Word-level | Word-level | No | Segment-level | No | Segment-level |
| **Diarization** | Yes (`--diarize`) | Yes (`--diarize`) | No (via anyscribe) | No | No | No | No |
| **Pricing** | ~$0.18–0.36/hr (by model) | ~$0.30/hr | ~$0.22–0.40/hr | ~$0.35/hr | ~$0.04/hr | Varies by model | Free |
| **File limit** | 25 MB (auto-chunked) | No hard limit | 25 MB (auto-chunked) | 30s (auto-chunked) | 25 MB (auto-chunked) | 25 MB (auto-chunked) | RAM only |
| **Offline** | No | No | No | No | No | No | Yes |
| **API key** | Required | Required | Required | Required | Required | Required | Not needed |
| **Quality tier** | — | `balanced` | `accuracy` | — | `cost` | — | `free` |

## Provider Details

### OpenAI Whisper (default)

The most widely used speech-to-text API. Good accuracy across most languages. Segment-level timestamps included.

```bash
anyscribe config set provider openai
```

- **API key env var:** `OPENAI_API_KEY`
- **Get a key:** [platform.openai.com/api-keys](https://platform.openai.com/api-keys)
- **Cost:** $0.003–$0.006 per minute depending on the model (see below)
- **File limit:** 25 MB for every model — anyscribe automatically chunks larger files into 18-minute segments
- **Default model:** `gpt-transcribe`
- **Diarization:** Yes — use `--diarize` flag to enable speaker-labeled transcripts

**Models you can pick:**

| Model | Cost per minute | Timestamps? | What it's for |
|-------|-----------------|-------------|---------------|
| `gpt-transcribe` (default) | $0.0045 (~$0.27/hr) | No | OpenAI's newest and recommended transcription model. Around half the error rate of Whisper in OpenAI's own testing, and 25% cheaper |
| `whisper-1` | $0.006 (~$0.36/hr) | **Yes** | The OpenAI model that tells you *when* things were said. anyscribe falls back to it automatically for timestamped or diarized output |
| `gpt-4o-transcribe` | $0.006 | No | An older model. `gpt-transcribe` is better and cheaper ($0.0045) |
| `gpt-4o-mini-transcribe` | $0.003 (~$0.18/hr) | No | The cheapest option, at some cost to accuracy |

```bash
anyscribe config set provider_models.openai whisper-1   # if you'd rather always use Whisper
```

> **You don't have to manage the timestamp tradeoff.** `gpt-transcribe` is more accurate and cheaper than Whisper, so it's the default — but it can't produce `[mm:ss]` markers. When your `output_format` is `timestamped` or `diarized`, anyscribe switches that run to `whisper-1` and tells you:
>
> ```
> → openai · whisper-1 (config)
>     switched to whisper-1 — gpt-transcribe can't produce timestamps
> ```
>
> The one case where it doesn't intervene is when you name the model yourself with `-m` — an explicit choice is always honoured.

> **Upgrading from an older anyscribe?** OpenAI's default used to be `whisper-1`. Unpinned OpenAI runs now use `gpt-transcribe`: cheaper, more accurate, and timestamps still work because of the automatic switch above. To go back permanently: `anyscribe config set provider_models.openai whisper-1`.

> **You may have heard of `gpt-live-transcribe`.** That one is for live, streaming audio (phone calls, real-time captions). anyscribe works on finished files, so it isn't supported here.

> **Diarization is handled for you.** When you pass `--diarize`, OpenAI runs a dedicated model (`gpt-4o-transcribe-diarize`) regardless of what you've pinned. There's nothing to configure.

> **When to use:** Good default for most use cases. Best balance of cost, accuracy, and language coverage. Use `--diarize` for meetings and multi-speaker content.

### Deepgram Nova

Fast, accurate speech-to-text with native speaker diarization and Hindi Latin script (`hi-Latn`) support. **The default provider for diarization** — anyscribe auto-routes `--diarize` to Deepgram when configured.

```bash
anyscribe config set deepgram_api_key YOUR_KEY    # $200 free credit on signup
```

- **API key env var:** `DEEPGRAM_API_KEY`
- **Get a key:** [console.deepgram.com](https://console.deepgram.com/) — $200 free credit, no credit card required
- **Cost:** ~$0.30/hour
- **Default model:** `nova-3` (auto-falls back to `nova` for `hi-Latn`, which isn't supported on nova-3 yet)
- **Also available:** `nova-2` — the previous generation. Pin it only if you're comparing against older transcripts: `anyscribe config set provider_models.deepgram nova-2`
- **No file size limit** — processes files of any length in a single request (unlike OpenAI's 25MB limit)
- **Diarization:** Native — automatically detects the number of speakers from audio characteristics. No need to specify a speaker count.
- **Hindi Latin:** Set `--language hi-Latn` for romanized Hindi / Hinglish output

**Diarization language guide:**

| Your audio | Language flag | Why |
|-----------|--------------|-----|
| English (or mostly English with some Hindi) | None (auto-detect) | Auto-detect handles English well, Hindi words transcribed phonetically |
| Mostly Hindi / Hinglish (Hindi-English mix) | `--language hi-Latn` | Outputs romanized Hindi in Latin script, better code-switching |
| Pure Hindi (want Devanagari) | `--language hi` | Outputs in Devanagari script |

> **When to use:** Best choice for multi-speaker transcripts (meetings, interviews, podcasts). Handles long recordings (3+ hours) without chunking. Excellent for Hinglish content with `--language hi-Latn`. This is the provider anyscribe auto-selects when you use `--diarize`, and what the **`balanced`** quality tier (the default) selects.

### ElevenLabs Scribe

High-accuracy transcription with word-level timestamps and optional speaker diarization (up to 32 speakers).

```bash
anyscribe config set provider elevenlabs
```

- **API key env var:** `ELEVENLABS_API_KEY`
- **Get a key:** [elevenlabs.io/app/settings/api-keys](https://elevenlabs.io/app/settings/api-keys)
- **Cost:** ~$0.22–0.40/hour depending on plan
- **File limit:** The ElevenLabs API accepts up to 3 GB, but anyscribe chunks at 25 MB (same as OpenAI) for consistency
- **Model:** `scribe_v2` (the most accurate model currently measured)

> **When to use:** When you need the highest accuracy, word-level timestamps, or speaker identification. This is what the **`accuracy`** quality tier selects.

### Sarvam AI

Specialized for Indian languages. Supports 22 Indian languages plus English with Indian accent optimization.

```bash
anyscribe config set provider sargam
```

- **API key env var:** `SARGAM_API_KEY`
- **Get a key:** [dashboard.sarvam.ai](https://dashboard.sarvam.ai)
- **Cost:** ~$0.35/hour; free tier: ~$12 in credits
- **File limit:** the sync API is limited to 30 seconds (exclusive) — anyscribe automatically chunks audio into 28-second segments
- **Model:** `saaras:v3` — Sarvam's flagship model, and the only one anyscribe offers
- **Supported languages:** Hindi, Tamil, Telugu, Kannada, Malayalam, Bengali, Gujarati, Marathi, Punjabi, Odia, Assamese, Urdu, Sanskrit, and more

> **Upgrading from an older anyscribe?** The older `saaras:v2.5` model has been removed — Sarvam deprecated the endpoint it ran on. If you had it pinned, anyscribe drops the pin for you on your next transcription and prints `Sarvam saaras:v2.5 is retired — using saaras:v3`. Nothing for you to do. v3 behaves the same way — still translates to English, still chunked — just more accurately.

> **Important — Sarvam *translates to English*.** Sarvam transcribes in translate mode, so the output is an **English translation**, not a verbatim Hindi/Hinglish transcript. Use it when you want Indic audio rendered as English; use Deepgram `--language hi-Latn` (see below) when you want to keep the spoken Hinglish.

> **When to use:** Getting an English version of Indian-language audio. Not the right choice if you want to preserve the original words.

> **Hinglish — what to keep?** For Hindi-English audio, **store the verbatim transcript, not a translation** — translation is one-way (you can't recover the original) and LLMs read Hinglish fine. **Deepgram `--language hi-Latn`** (the default `balanced` tier) gives clean romanized Hinglish; **ElevenLabs** (`accuracy` tier) gives native Devanagari. Either is a lossless source of truth an LLM can summarize or translate on demand. See the [building doc](../building/journal/2026-06-29-hinglish-transcript-format-and-llm-consumption.md) for the research behind this.

### Groq

The cheapest and fastest cloud option. Runs OpenAI's Whisper `large-v3-turbo` on Groq's accelerators and returns the same Whisper output anyscribe already parses (segment timestamps included).

```bash
anyscribe config set groq_api_key gsk-...
```

- **API key env var:** `GROQ_API_KEY`
- **Get a key:** [console.groq.com/keys](https://console.groq.com/keys)
- **Cost:** ~$0.04/hour — the cheapest cloud provider
- **File limit:** 25 MB (auto-chunked, same as OpenAI)
- **Default model:** `whisper-large-v3-turbo` — the fastest and cheapest
- **Also available:** `whisper-large-v3` — more accurate, a bit slower, and Groq allows bigger uploads for it. Worth switching to if the turbo model is dropping words: `anyscribe config set provider_models.groq whisper-large-v3`
- **Diarization:** No — use the `accuracy` or `balanced` tier (or `--provider deepgram`) for speaker labels

> **When to use:** the **`cost`** quality tier maps here. Great for bulk, low-cost transcription where you don't need speaker labels. Fast enough that long files fly through.

### OpenRouter

Access to various AI models through a unified API. Since OpenRouter doesn't have a dedicated speech-to-text endpoint, this uses audio-capable chat models with a transcription prompt.

```bash
anyscribe config set provider openrouter
```

- **API key env var:** `OPENROUTER_API_KEY`
- **Get a key:** [openrouter.ai/keys](https://openrouter.ai/keys)
- **Cost:** Varies by model (per-token pricing, generally more expensive than dedicated STT)
- **File limit:** 25 MB (auto-chunked, same as OpenAI)
- **No timestamps** — returns plain text only
- **Default model:** `openai/gpt-audio-mini`
- **Also suggested:** `google/gemini-2.5-flash-lite`, `google/gemini-2.5-flash`, `google/gemini-3-flash-preview`, `mistralai/voxtral-small-24b-2507`, `openai/gpt-audio`

```bash
anyscribe config set provider_models.openrouter google/gemini-2.5-flash
```

> **OpenRouter takes any model name.** Unlike the other providers, anyscribe doesn't check your choice against a list — type any audio-capable model name from [openrouter.ai/models](https://openrouter.ai/models) and it gets passed straight through. The flip side: a typo isn't caught until OpenRouter rejects it.

> **Keep your own models in the list.** Add the ones you use so they show up in every picker instead of being retyped:
>
> ```bash
> anyscribe config set extra_models.openrouter "qwen/qwen3-omni-flash,openai/gpt-audio"
> anyscribe config set extra_models.openrouter ""     # clears them
> ```
>
> They appear next to the built-ins, marked `(custom)`. OpenRouter is the only provider that accepts this — see [configuration.md](configuration.md#extra_models).

> **The old default is gone.** anyscribe used to default to `openai/gpt-4o-audio-preview`, which OpenRouter has since removed — requests to it now fail with a "model not found" error. The default is now `openai/gpt-audio-mini`. If you pinned the old one yourself, change it to a current model name.

> **`OPENROUTER_MODEL` in `.env` is no longer read** (removed in 0.15.0). Use `anyscribe config set provider_models.openrouter <slug>` instead, and delete the line from `~/.anyscribe/.env`.

> **When to use:** When you need a specific model that's only available on OpenRouter. Not recommended as a primary transcription provider — dedicated STT APIs are faster, cheaper, and more accurate.

### Local (faster-whisper)

Runs entirely on your machine. No API key, no internet connection, no cost. Uses faster-whisper, a CTranslate2-based reimplementation of OpenAI Whisper that's up to 4x faster.

> **Also needs `ffmpeg`** on your system PATH. anyscribe uses ffmpeg to pre-process audio before handing it to Whisper — if ffmpeg isn't installed, local transcription will fail even after setup. Install via `brew install ffmpeg` (macOS), `winget install Gyan.FFmpeg` (Windows), or your distro's package manager (Linux).

**Setup is a single action** — pick whichever path fits your workflow; all four do the same thing:

```bash
anyscribe local setup --model base
```

or in the Web UI, either:
- **First-run onboarding wizard** (opens automatically on your first `anyscribe ui` launch) — pick "local" as your provider, or say Yes to the "Also enable offline transcription?" step.
- **Settings → Providers → Local → "Set up local transcription"** at any time after onboarding.

or during the terminal wizard, answer **Yes** when `anyscribe onboard` asks *"Also enable offline/local transcription?"*.

Setup installs `faster-whisper` into the same Python environment as anyscribe, downloads the Whisper model you picked, and records it as your local default. After that, local transcription is fully offline.

**Recommended model:** `base` — good quality for most use cases, ~145 MB download, runs on modest CPUs. If a recording is critical (interviews, accents, lots of names), step up to `small`, then `large-v3-turbo`.

**Switching the default model:**

```bash
anyscribe config set local_model small
```

or pick from the dropdown in the Web UI's Local provider panel. (The model has to be cached first — see next section.)

**Managing downloaded models** (after setup):

| Command | What it does |
|---------|--------------|
| `anyscribe model list` | Show all 7 sizes with cache status and disk usage |
| `anyscribe model pull small` | Download an additional model size |
| `anyscribe model rm tiny --yes` | Delete a cached model (`--yes` required — destructive) |
| `anyscribe model info large-v3-turbo` | Inspect a single size |

Or use the Models table inside **Settings → Providers → Local** in the Web UI.

**Model size guide:**

| Model | Download | RAM (peak) | Speed (CPU) | Quality |
|-------|----------|------------|-------------|---------|
| `tiny` | ~75 MB | ~400 MB | ~10x realtime | Lowest |
| `base` (recommended) | ~145 MB | ~600 MB | ~7x realtime | Good for most |
| `small` | ~480 MB | ~1.2 GB | ~4x realtime | Noticeably better than base |
| `medium` | ~1.5 GB | ~2.5 GB | ~2x realtime | Near-large for many languages |
| `large-v3` | ~3 GB | ~5 GB | ~1x realtime (CPU); fast on GPU | Highest |
| `large-v3-turbo` | ~1.6 GB | ~3 GB | ~6x realtime | Near `large-v3`, all languages |
| `distil-large-v3.5` | ~1.5 GB | ~2.8 GB | ~6x realtime | Near `large-v3` for **English**; weaker on other languages |

> **Best quality per minute of waiting: `large-v3-turbo`.** It gets close to `large-v3` accuracy while running about six times faster on a CPU, at roughly half the download. That makes it the one to reach for when `base` or `small` isn't good enough but you don't want to wait through a real-time-speed transcription.

> **`distil-large-v3.5` is English-only in practice.** It's a slimmed-down model that keeps `large-v3`-level accuracy for English but gets noticeably worse in other languages. Pick it only if everything you transcribe is English; otherwise `large-v3-turbo` is the safer choice at the same speed and size.

- **GPU:** Automatically uses NVIDIA CUDA if available; falls back to CPU.
- **Env-var override:** `ASCLI_LOCAL_MODEL=small anyscribe "<url>"` wins over the configured default for one invocation.

**Removing local transcription** (uninstalls faster-whisper and deletes every cached model):

```bash
anyscribe local teardown --yes
```

or click **"Remove local transcription"** at the bottom of the Local provider panel in the Web UI.

> **When to use:** When you're offline, want zero cost, or have privacy concerns about sending audio to cloud APIs. CPU transcription on `base` runs roughly 7x faster than real time on modern laptops — a 10-minute podcast takes ~90 seconds to transcribe.

## Switching Providers

Change your default provider:

```bash
anyscribe config set provider elevenlabs
```

Override for a single transcription:

```bash
anyscribe "<url>" --provider local
```

## Switching Models

Change the model a provider uses, permanently:

```bash
anyscribe config set provider_models.openai gpt-transcribe
```

Or just for one transcription:

```bash
anyscribe "<url>" -p openai -m gpt-transcribe
```

Check what's in effect:

```bash
anyscribe providers list
```

See [Choosing a model within a provider](#choosing-a-model-within-a-provider) for the full list and the timestamps caveat.

## Adding API Keys

The quickest way to add an API key:

```bash
anyscribe config set deepgram_api_key YOUR_KEY
anyscribe config set openai_api_key sk-proj-...
anyscribe config set elevenlabs_api_key xi-...
anyscribe config set openrouter_api_key sk-or-...
anyscribe config set sargam_api_key YOUR_KEY
anyscribe config set groq_api_key gsk-...
```

These are stored in `~/.anyscribe/.env` automatically.

Or use the onboarding wizard:

```bash
anyscribe onboard --force
```

Or edit `~/.anyscribe/.env` directly.

Test that a provider works:

```bash
anyscribe providers test elevenlabs
```

## Picking a language (Web UI)

The web UI (`anyscribe ui`) shows a per-provider language dropdown so you
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

When you use `--diarize` without specifying a provider (`-p`), anyscribe automatically switches to **Deepgram** if a Deepgram API key is configured. This is because Deepgram handles large files natively (no chunking needed) and produces the most consistent speaker labels across long recordings.

To override and use a specific provider for diarization:

```bash
anyscribe "url" --diarize --provider openai
```

> **Web UI naming:** "Diarize" appears as a `Multi-speaker` toggle in `anyscribe ui` and the `diarized` output format is labelled `with-speaker-labels` — the underlying behavior is identical.
