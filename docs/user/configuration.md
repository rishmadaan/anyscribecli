---
summary: All configuration options, file locations, and how to change settings.
read_when:
  - You want to change your default provider, model, or language
  - You need to find where config files are stored
  - You want to understand what each setting does
---

# Configuration

anyscribe uses two locations: a visible workspace for your transcripts and a hidden directory for app internals.

> **`scribe` and `ascli` are shorter aliases for `anyscribe`** — all three commands are interchangeable everywhere in this guide.

## File Locations

| File | Path | What it stores |
|------|------|---------------|
| **Workspace** | `~/anyscribe/` | Your Obsidian vault with all transcripts (configurable) |
| Config | `~/.anyscribe/config.yaml` | Your preferences (provider, language, etc.) |
| API Keys | `~/.anyscribe/.env` | Secret API keys (never committed to git) |
| Downloads | `~/.anyscribe/downloads/` | Downloaded audio/video files |
| Logs | `~/.anyscribe/logs/` | Processing logs |
| Sessions | `~/.anyscribe/sessions/` | Cached sessions (legacy; no longer used for Instagram) |
| Temp | `~/.anyscribe/tmp/` | Temporary downloads (auto-cleaned) |

> **Upgrading from an older version?** If you have transcripts at `~/.anyscribe/workspace/`, anyscribe will automatically move them to `~/anyscribe/` on your next transcription.

> **Upgrading from the old `anyscribecli` package?** The app folder moved from `~/.anyscribecli/` to `~/.anyscribe/`. This normally happens automatically on your next transcription, but if your keys ever seem to have vanished after upgrading, run `anyscribe migrate` (add `--dry-run` first to preview). It moves your config, keys, and downloads across without ever overwriting anything already in the new folder. See [Commands → anyscribe migrate](commands.md#anyscribe-migrate).

> **Tip:** Run `anyscribe doctor` to see if all these exist and are healthy.

## config.yaml

This is your main settings file. The onboarding wizard creates it, but you can also edit it directly.

```yaml
# ~/.anyscribe/config.yaml

provider: openai          # Explicit provider (used when quality is `custom`)
provider_models: {}        # Which model each provider should use (empty = defaults)
extra_models: {}           # Your own OpenRouter model names, added to the picker
quality: balanced          # accuracy | balanced | cost | free | custom — picks the provider
language: auto             # Language for transcription
local_model: base          # Offline Whisper size (local provider only)
keep_media: false          # Whether to save audio files
output_format: clean       # How to format transcripts
diarize: false             # Enable speaker diarization by default
prompt_download: never     # Ask to download video after transcription
local_file_media: skip     # What to do with local files after transcription
workspace_path: ""         # Empty = ~/anyscribe (default), or set a custom path
instagram:                 # Instagram settings
  browser: ""             # Browser to read cookies from (e.g. firefox, chrome)
```

> **Note:** API keys are stored in `~/.anyscribe/.env`, not in config.yaml. Secrets never go in config.

> **Adding and removing keys:** Set a key with `anyscribe config set openai_api_key sk-…`, or in the Web UI under **Settings → Providers** (expand a provider to paste one). To **remove** a saved key, open that provider in the Web UI and click **Remove key → Remove?** — it's deleted from `.env`. You can also just delete the line from `~/.anyscribe/.env` by hand. A key you set through your shell environment (e.g. `export OPENAI_API_KEY=…` in your shell profile) isn't stored in `.env`, so the Web UI can't remove it — unset it in your shell.

> **Everything here is also editable in the Web UI** (`anyscribe ui` → Settings) —
> the page opens with a "Next run" banner showing exactly what your next
> transcription will use and why, the provider and model controls are always
> visible (a tier just pre-selects them), and a "Downloads & media" section
> covers download prompting, local-file handling, kept media, and the
> Instagram cookie browser. Nothing needs the terminal.

### Settings Explained

#### One knob picks the provider

`quality` and `provider` are not two competing settings — they are one knob with
two positions. `quality` is either a **tier** (`accuracy`, `balanced`, `cost`,
`free`), in which case the tier picks the provider, or it is `custom`, in which
case your `provider` line is used as-is.

```bash
anyscribe config set quality accuracy      # tier picks the provider (ElevenLabs)
anyscribe config set provider deepgram     # also sets quality = custom, so it sticks
```

> **Setting a provider always writes `quality: custom` in the same save.** That's
> deliberate: without it, the next run would go back to the tier's provider and
> your choice would silently vanish. This happens wherever you set a provider —
> `anyscribe config set provider`, the Web UI Settings page, the MCP `set_config`
> tool.

To see which one is winning right now, run [`anyscribe config`](commands.md#anyscribe-config)
with no subcommand:

```
Next run: deepgram · nova-3 (quality: balanced)
```

The `(...)` at the end names the reason: `config` (your `provider` line),
`quality: <tier>`, `flag` (a `--provider` you passed), or `diarize`.

#### provider

Which API to use for transcription when `quality` is `custom`. Default: `openai`.

| Value | Service | What you need |
|-------|---------|---------------|
| `openai` | OpenAI Whisper API | `OPENAI_API_KEY` in .env |
| `deepgram` | Deepgram Nova (diarization + hi-Latn) | `DEEPGRAM_API_KEY` |
| `openrouter` | OpenRouter (audio-via-chat models) | `OPENROUTER_API_KEY` |
| `elevenlabs` | ElevenLabs Scribe v2 (highest accuracy, 90+ languages) | `ELEVENLABS_API_KEY` |
| `sargam` | Sarvam AI (23 Indic languages + English) | `SARGAM_API_KEY` |
| `groq` | Groq (fast, cheap Whisper large-v3-turbo) | `GROQ_API_KEY` |
| `local` | faster-whisper (offline, free) | None needed |

> **Tip:** If you don't have a strong opinion, leave `quality` on a tier (below)
> and don't touch `provider` at all — the tier chooses for you.

> **Why multiple providers?** Different services handle different languages better. OpenAI Whisper is a good default, ElevenLabs has high accuracy across 90+ languages, Sarvam excels at Indian languages, and the local provider is free and works offline.

> **Local provider** requires `pip install faster-whisper`. Models download automatically on first use. Works on CPU (slower) or GPU (fast with CUDA).

#### provider_models

Which **model** each provider should use. A provider is the service (OpenAI, Groq...); a model is the specific engine inside it. Every provider has a sensible default, so this setting starts empty and most people never touch it.

Set one with `anyscribe config set`:

```bash
anyscribe config set provider_models.openai gpt-transcribe
anyscribe config set provider_models.groq whisper-large-v3
```

Which produces:

```yaml
provider_models:
  openai: gpt-transcribe
  groq: whisper-large-v3
```

Each provider gets its own line, so switching providers keeps each one's chosen model. Any provider not listed uses its default.

**To see the options,** run `anyscribe config` (no subcommand) or `anyscribe providers list` — both show every provider, the model it would use, and the alternatives.

**To go back to the default,** delete that line from `config.yaml`.

**For one run only,** skip config entirely and use the `--model` flag: `anyscribe "url" -p openai -m gpt-transcribe`. That wins over whatever is in `provider_models`.

If you set a model a provider doesn't have, anyscribe refuses and prints the valid list. (OpenRouter is the exception — it takes any audio-capable model name, so anyscribe passes yours straight through. See `extra_models` below to keep your own names in the picker.)

> **Timestamps are handled for you.** OpenAI's default model, `gpt-transcribe`,
> is cheaper and more accurate than `whisper-1` — but it can't tell you *when*
> something was said. If your `output_format` is `timestamped` or `diarized`,
> anyscribe quietly switches that run to `whisper-1` and prints a note saying so:
>
> ```
> → openai · whisper-1 (config)
>     switched to whisper-1 — gpt-transcribe can't produce timestamps
> ```
>
> The switch only happens when anyscribe picked the model. If **you** passed
> `-m gpt-transcribe` for that run, anyscribe respects it and you get plain
> paragraphs — you asked for that model explicitly.

> **The `local` provider isn't set here.** Its models are files on your machine, so they live in `local_model` (below).

#### extra_models

Your own model names for **OpenRouter**, merged into every model picker
(the `anyscribe config` dashboard, `anyscribe providers list`, the Web UI dropdown).

```bash
anyscribe config set extra_models.openrouter "qwen/qwen3-omni-flash,openai/gpt-audio"
anyscribe config set extra_models.openrouter ""      # empty value clears the list
```

```yaml
extra_models:
  openrouter:
    - qwen/qwen3-omni-flash
    - openai/gpt-audio
```

They show up alongside the built-in suggestions, marked `(custom)` so you can
tell yours apart. In the Web UI, the OpenRouter model box is a free-text field
with the same merged list as suggestions.

> **Only OpenRouter accepts this.** `anyscribe config set extra_models.deepgram …`
> is rejected on purpose. OpenRouter is a router — it will forward any model name
> and the model does the rest. Every other provider needs code that knows how to
> read *that specific model's* response, so their lists are curated and shipped
> with anyscribe releases. **If a provider added a model you want, that's an anyscribe
> update, not a config change** — run `anyscribe update`.

#### quality

Pick **what you want** — higher accuracy or lower cost — and anyscribe chooses the
provider for you. Default: `balanced` (Deepgram). This is the easiest way to use
anyscribe; you rarely need to touch `provider` directly.

| Value | Picks | Best for |
|-------|-------|----------|
| `balanced` (default) | Deepgram `nova-3` | Strong accuracy + native speaker labels |
| `accuracy` | ElevenLabs `scribe_v2` | Highest accuracy, primarily-English |
| `cost` | Groq `whisper-large-v3-turbo` | Cheapest + fastest cloud (~$0.04/hr) |
| `free` | Local faster-whisper | Offline, $0 (needs `anyscribe local setup`) |
| `custom` | Whatever `provider` says | You picked a provider yourself |

Change it with `anyscribe config set quality cost`, per-run with
`anyscribe transcribe <url> --quality cost`, or from the picker in the Web UI.

> **How it works:** the tier picks a provider. If you pass `--provider` (or pick
> one in the Web UI), that wins for that run. `custom` isn't a tier — it's the
> "hands off, use my `provider`" setting, and anyscribe writes it for you whenever
> you set a provider.

> **Need a key:** each tier needs that provider's key in `.env` —
> `accuracy` needs `ELEVENLABS_API_KEY`, `cost` needs `GROQ_API_KEY`, etc.
> `free` needs no key.
>
> **If the tier's key is missing, anyscribe says so and keeps going** with your
> configured `provider` instead of failing:
>
> ```
> → openai · gpt-transcribe (config)
>     WARNING: quality 'balanced' wants deepgram but no DEEPGRAM_API_KEY is set — using openai instead
> ```
>
> Either add the key (`anyscribe config set deepgram_api_key …`) or pick a tier you
> have a key for. The warning appears on every surface — CLI runs, `anyscribe config`,
> the Web UI, and MCP results.

#### language

What language to expect in the audio. Default: `auto` (let the API auto-detect).

Use standard language codes: `en` (English), `es` (Spanish), `fr` (French), `hi` (Hindi), `ar` (Arabic), `zh` (Chinese), `ja` (Japanese), `ko` (Korean), etc.

Each provider expects codes in a slightly different format — Whisper-family providers (`openai`, `local`) use ISO 639-1 like `en`, Deepgram uses BCP-47 codes (a standard format for language tags, like `en-US` or `hi-Latn`), and Sarvam uses BCP-47 with `-IN` suffixes like `hi-IN`. If you're unsure, the web UI (`anyscribe ui`) shows a per-provider dropdown of every supported code on the Transcribe page Options panel.

> **When to set this explicitly:** Auto-detection works well for most videos, but if you're transcribing content in a specific language and getting wrong results, setting the language explicitly helps. You can also override per-video: `anyscribe transcribe <url> --language hi`

#### keep_media

Whether to save the downloaded audio file alongside the transcript. Default: `false`.

When `true`, audio files are saved to `~/.anyscribe/downloads/audio/<platform>/` (separate from the Obsidian workspace). This uses more disk space but lets you re-listen or re-transcribe later without downloading again.

> **Disk space:** A 10-minute video at 64kbps mono is about 5MB of audio. If you transcribe a lot, this adds up.

#### output_format

How to format the transcript text. Default: `clean`.

| Value | Description |
|-------|-------------|
| `clean` | Plain text transcript, paragraphs only |
| `timestamped` | Transcript with `[mm:ss]` timestamps per segment |
| `diarized` | Speaker-grouped turns with timestamps (for multi-speaker audio) |

> **Tip:** When you use `--diarize`, the output format is automatically set to `diarized` unless you've explicitly set it to `timestamped`.

> **Web UI label:** The `diarized` value is shown as `with-speaker-labels` in `anyscribe ui`. The wire value (what gets stored in `config.yaml`) is unchanged — picking either spelling produces the same output.

#### diarize

Whether to enable speaker diarization (identifying who said what) by default. Default: `false`.

When enabled, providers that support diarization (OpenAI, Deepgram, Sarvam) will label each speaker in the transcript. You can also enable per-transcription with `--diarize` without changing this default.

> **Auto-routing:** When `--diarize` is used (or this is set to `true`) without an explicit `--provider`, anyscribe automatically switches to Deepgram if a Deepgram API key is configured. Deepgram handles large files natively and produces the most consistent speaker labels. Override with `--provider openai` if needed.

> **Automatic speaker detection:** The number of speakers is detected automatically from the audio — you never need to specify how many speakers are in the recording. Deepgram analyzes voice characteristics (pitch, tone, cadence) to distinguish speakers.

> **Language tip:** For mostly-English meetings, auto-detect works well. For Hindi or Hinglish (Hindi-English mix), add `--language hi-Latn` for romanized Latin script output. See [Providers](providers.md) for the full language guide.

> **When to enable:** If you primarily transcribe meetings, interviews, or podcasts with multiple speakers. Leave off for single-speaker content like YouTube videos.

#### prompt_download

Whether to offer downloading the video/audio file after each transcription. Default: `never`.

| Value | Description |
|-------|-------------|
| `never` | Don't ask — just transcribe (default) |
| `ask` | Ask after each transcription if you want the video/audio too |
| `always` | Always download the full video after transcription |

> **Tip:** You can always download manually with `anyscribe download "<url>"` regardless of this setting.

#### local_file_media

What to do with the original file when transcribing local audio/video files. Default: `skip`.

| Value | Description |
|-------|-------------|
| `skip` | Leave the original file where it is (default) |
| `copy` | Copy to `~/.anyscribe/downloads/audio/local/` for organization |
| `move` | Move to the downloads directory (removes the original) |
| `ask` | Ask each time what to do |

> **Why skip by default?** Unlike URL downloads where audio is temporary, local files already exist on your disk. Copying them wastes space unless you want everything organized in one place.

#### local_model

Which Whisper model the `local` provider uses when transcribing. Default: `base`.

| Value | Download | RAM | Quality |
|-------|----------|-----|---------|
| `tiny` | ~75 MB | ~400 MB | lowest |
| `base` (default) | ~145 MB | ~600 MB | good for most |
| `small` | ~480 MB | ~1.2 GB | noticeably better |
| `medium` | ~1.5 GB | ~2.5 GB | near-large for many languages |
| `large-v3` | ~3 GB | ~5 GB | highest |
| `large-v3-turbo` | ~1.6 GB | ~3 GB | near `large-v3`, ~6x faster on CPU |
| `distil-large-v3.5` | ~1.5 GB | ~2.8 GB | near `large-v3` for English; weaker on other languages |

> **Want better quality without the wait?** `large-v3-turbo` is the sweet spot — close to `large-v3` accuracy at roughly six times the speed on a CPU, and half the download. Pick `distil-large-v3.5` only if everything you transcribe is in English.

Change it with `anyscribe config set local_model small` or from the default-model dropdown inside the Local provider panel in the Web UI. You can only select a model that's been cached — pull others with `anyscribe model pull <size>`. A one-off override is available via `ASCLI_LOCAL_MODEL=medium anyscribe "<url>"` (`ASCLI_` is the legacy env prefix, still honored).

> **Not set until setup.** This field has no effect until you run `anyscribe local setup --model <size>` (or the equivalent Web UI button). The field is still present in `config.yaml` with the default value of `base`.

### Instagram cookies (`instagram.browser`)

Tells anyscribe which browser to read Instagram cookies from. Cookies let anyscribe
download reels that need a logged-in session — including private reels and
reels that are getting rate-limited for anonymous users.

**Most common values:** `firefox`, `chrome`, `safari`. Also supported: `brave`,
`edge`, `chromium`, `vivaldi`, `opera`. Leave empty (the default) to skip
cookies — many public reels work fine without them.

```bash
anyscribe config set instagram.browser firefox
```

> **What anyscribe actually does:** When you set this, anyscribe tells yt-dlp to read
> cookies from the browser's profile directory. yt-dlp handles the extraction
> using the browser's built-in decryption — your password is never asked for or
> stored.

> **Pre-0.8.3 upgrade note:** Older versions of anyscribe asked for an Instagram <!-- version-pin-ok -->
> username and password and stored the password in `~/.anyscribe/.env`.
> Those are no longer used — you can safely remove the `INSTAGRAM_PASSWORD`
> line from your `.env` file when convenient.

## .env (API Keys and Secrets)

API keys and passwords are stored separately from config for security:

```bash
# ~/.anyscribe/.env
OPENAI_API_KEY=sk-proj-...
DEEPGRAM_API_KEY=...
# ELEVENLABS_API_KEY=xi-...
# OPENROUTER_API_KEY=sk-or-...
# SARGAM_API_KEY=...
# GROQ_API_KEY=gsk-...
```

> **Important:** This file contains secrets. It's excluded from git by default. Never share it or commit it to a repository.

> **`OPENROUTER_MODEL` no longer does anything.** Older versions read that line to
> choose an OpenRouter model. Since 0.15.0 the model lives with every other model <!-- version-pin-ok -->
> choice — run `anyscribe config set provider_models.openrouter <slug>` and delete the
> `OPENROUTER_MODEL` line from `.env`.

> **Pre-0.8.3 upgrade note:** <!-- version-pin-ok --> Older versions of anyscribe stored `INSTAGRAM_PASSWORD` in this file. It's no longer used — you can safely remove the `INSTAGRAM_PASSWORD` line when convenient. Instagram downloads now use browser cookies instead (see `instagram.browser` below).

### Changing your API key

The easiest way is to use `anyscribe config set`:

```bash
anyscribe config set openai_api_key sk-proj-...
anyscribe config set deepgram_api_key YOUR_KEY
anyscribe config set elevenlabs_api_key xi-...
anyscribe config set sargam_api_key YOUR_KEY
anyscribe config set openrouter_api_key sk-or-...
anyscribe config set groq_api_key gsk-...
```

These are stored in `~/.anyscribe/.env` automatically.

Or re-run onboarding:

```bash
anyscribe onboard --force
```

This shows your current settings (API keys masked) and lets you change only what you need — no need to re-enter everything.

Or edit the file directly with any text editor — here's `nano` as an example:

```bash
nano ~/.anyscribe/.env
```

## Workspace Structure

Your transcripts live in the workspace (pure markdown, no binaries). Downloaded files are stored separately in the app directory.

```
~/anyscribe/                               # Obsidian vault (configurable)
├── .obsidian/                             # Obsidian app config
├── _index.md                              # Master index — newest first
├── sources/
│   ├── youtube/                           # YouTube transcripts
│   ├── instagram/                         # Instagram transcripts
│   └── local/                             # Local file transcripts
└── daily/YYYY-MM-DD.md                   # Daily processing log

~/.anyscribe/                           # App internals (hidden)
├── downloads/                             # Downloads (separate from vault)
│   ├── audio/<platform>/                  # Audio files (if keep_media=true)
│   └── video/<platform>/                  # Video files (anyscribe download)
├── sessions/                              # Cached sessions (legacy; no longer used for Instagram)
└── logs/                                  # Processing logs
```

> **Why are downloads separate?** Keeping binaries out of the Obsidian vault means the vault stays lightweight and fast — even with hundreds of transcripts.

#### workspace_path

Where to store your transcript workspace. Default: `~/anyscribe/` (when set to empty string or omitted).

Set a custom path to use an existing Obsidian vault or a different location:
```bash
anyscribe config set workspace_path ~/Documents/transcripts
```

> **Tip:** Leave this empty to use the default `~/anyscribe/`. The workspace is visible in Finder/file managers — no need to navigate to hidden folders.

### How files are named

- **File names:** A "slug" of the video title — lowercase, hyphens instead of spaces, max 60 characters
- **Collisions:** If two videos have the same slug, the second gets `-2` appended

### Transcript frontmatter

Each markdown file has YAML properties at the top that Obsidian can search and filter:

```yaml
---
source: https://youtube.com/watch?v=...    # Original URL
platform: youtube                           # Where it came from
title: "Video Title"                        # Video title
duration: "12:34"                           # Length of the video
language: en                                # Detected language
provider: openai                            # Which API transcribed it
date_processed: 2026-03-26                  # When you ran the transcription
word_count: 1500                            # Total words in transcript
reading_time: "8 min"                       # Estimated reading time
tags:                                       # For Obsidian tag filtering
  - transcript
  - youtube
tldr: "Video Title"                         # Quick summary
---
```

## What you can change vs what's fixed

Most things you'd want to adjust are settings you can change anytime. A few
things are **fixed in the code** — they're tuned defaults that keep transcription
reliable, and changing them means editing anyscribe's source and reinstalling.

```
   things you set (knobs)                things baked in (constants)
   ┌──────────────────────────┐         ┌──────────────────────────────┐
   │ config.yaml settings     │         │ audio quality (16kHz/mono)   │
   │ .env API keys + secrets  │         │ how big files get split up   │
   │ --flags on commands      │         │ where app files live         │
   │ the Web UI settings page │         │ Web UI is localhost-only     │
   └──────────────────────────┘         └──────────────────────────────┘
   change anytime, no restart            changing these needs a code edit
```

**You can change anytime** (this whole page): your provider, the model that
provider uses, language, output format, diarization, whether media is kept, your
workspace location, the local model, and all your API keys.

**Fixed in the code** (and why):

| What's fixed | Current value | Why it's not a setting |
|--------------|---------------|------------------------|
| Audio quality | 16 kHz, mono, 64 kbps mp3 | Tuned for the best transcription accuracy per megabyte. Higher quality wouldn't improve the text. |
| File-splitting limits | Split if over 25 MB or 30 min, into 18-min pieces | Driven by the transcription APIs' own upload and timeout limits, not your preference. |
| The list of models you can pick from | e.g. OpenAI offers `gpt-transcribe`, `whisper-1`, `gpt-4o-transcribe`, `gpt-4o-mini-transcribe` | Each provider's list is curated to models anyscribe knows how to read. You choose freely *within* the list via `provider_models` or `--model`; new entries arrive with anyscribe releases (`anyscribe update`). **OpenRouter is the exception** — it forwards any model name, so you can add your own with `extra_models.openrouter`. |
| App folder location | `~/.anyscribe` | The fixed home for config, logs, and downloads. Your transcripts' location (`workspace_path`) *is* configurable. |
| Web UI address | `127.0.0.1` (your machine only) | The Web UI has no password, so it only listens to your own computer. The port is changeable with `anyscribe ui --port 9000`. |

> **Want one of these to be a real setting?** These are deliberate defaults, not
> oversights — see the developer note in
> [docs/building/architecture.md](https://github.com/rishmadaan/anyscribe/blob/main/docs/building/architecture.md) for which ones are
> candidates to become configurable. If you have a concrete need (say, a custom
> audio bitrate), that's a reasonable feature request.

## Resetting Everything

To start fresh, delete the app directory and re-run onboarding:

> **Warning:** This deletes your config, API keys, and transcripts. Back up `~/anyscribe/` first if you want to keep your transcripts. If you used a custom workspace path, back up that location instead.

```bash
rm -rf ~/.anyscribe ~/anyscribe
anyscribe onboard
```
