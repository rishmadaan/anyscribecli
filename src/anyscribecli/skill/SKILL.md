---
name: scribe
description: >
  Use scribe (anyscribecli) to transcribe video/audio from YouTube, Instagram,
  or local files into markdown. Activate when the user wants to transcribe a URL
  or file, download media, configure transcription providers, manage their scribe
  setup, batch-process multiple URLs, or troubleshoot scribe issues.
allowed-tools: Bash(scribe *), Read
---

# scribe — Transcription CLI Operator Guide

You are an expert operator of `scribe` (anyscribecli), a CLI tool that transcribes video/audio into structured markdown files in an Obsidian vault.

## Before Running Any Command

**Pre-flight check** — on first use in a session, verify scribe is available:

```bash
scribe --version
```

If not installed: suggest `pip install anyscribecli`. If installed but not configured (no `~/.anyscribecli/config.yaml`): guide the user through `scribe onboard`.

**Windows note:** If `scribe` is not on PATH (common on Windows), use `python -m anyscribecli` instead of `scribe` for all commands. Example: `python -m anyscribecli "url" --json --quiet`.

## Core Principle: Use --json for Machine Output

When YOU run scribe commands, always use `--json --quiet` flags so you can parse structured output. Show the user a clean summary, not raw JSON.

```bash
scribe "URL" --json --quiet
```

Parse the JSON result and present it conversationally:
- On success: file path, title, duration, word count, provider used
- On failure: the error message in plain language, plus a fix

When the USER wants to run commands themselves, show them the human-readable form (no --json).

## Command Decision Tree

| User wants to... | Command |
|---|---|
| Transcribe a URL or local file | `scribe "url"` or `scribe /path/to/file` |
| Transcribe with speaker diarization | `scribe "url" --diarize` (auto-routes to Deepgram if configured) |
| Hindi / Hinglish with speakers | `scribe "url" --diarize --language hi-Latn` — **always use this combo for Hindi content with multiple speakers** |
| Transcribe multiple URLs | `scribe batch urls.txt` |
| Download video/audio only | `scribe download "url"` or `scribe download "url" --audio-only` |
| Change settings | `scribe config set <key> <value>` |
| See current config | `scribe config show` |
| Switch provider | `scribe config set provider <name>` |
| Test a provider | `scribe providers test <name>` |
| List providers | `scribe providers list` |
| Set up offline transcription | `scribe local setup --model base --yes` *(see rule below)* |
| Check offline-transcription state | `scribe local status --json` |
| Download another Whisper model | `scribe model pull <size> --json` |
| List downloaded Whisper models | `scribe model list --json` |
| Delete a cached Whisper model | `scribe model rm <size> --yes --json` |
| Remove offline transcription | `scribe local teardown --yes --json` |
| Initial setup (interactive, for a human) | `scribe onboard` (or `--force` to re-run) |
| Initial setup (headless, agent or script) | `scribe onboard --provider X --api-key $KEY --yes --json` *(see rule below)* |
| Use the web UI | `scribe ui` (opens browser dashboard at 127.0.0.1:8457) |
| Diagnose problems | `scribe doctor` |
| Update scribe | `scribe update` |
| Check for updates | `scribe update --check` |

For complete command syntax and all flags, read [references/commands.md](references/commands.md).

## Onboarding (First-Run Setup) — Agent Rules

scribe has three equivalent setup paths: an interactive CLI wizard (`scribe onboard`), a Web UI wizard (first-run modal on `scribe ui`), and a headless flag-driven path (`scribe onboard --yes`). **You must use the headless path.** The interactive wizards need a TTY / browser — they'll either hang or produce no output in an agent context.

**Rule: do not run `scribe onboard` without `--yes` in agent contexts.** If the user asks you to "set up scribe," use:

```bash
scribe onboard --provider <name> --api-key "$KEY_ENV_VAR" --yes --json
```

For local/offline transcription as primary provider:

```bash
scribe onboard --provider local --local-model base --yes --json
```

**Prefer env vars over `--api-key` on argv** — argv leaks into shell history. Reference the env var by name (`"$OPENAI_API_KEY"`) in examples you give the user.

**Don't guess missing flags.** If the user hasn't told you which provider or model to use, ask them — don't default to one silently. The recommended model for `--provider local` is `base` per [`references/providers.md`](references/providers.md); other defaults (workspace, language, output format) are sane and the user can adjust them in Settings later.

**Already configured?** `scribe onboard --yes` without `--force` exits 2 when `~/.anyscribecli/config.yaml` exists. If the user wants to reconfigure, pass `--force`.

## Local (Offline) Transcription Workflow

The `local` provider runs Whisper on the user's own machine via `faster-whisper` — no API, no network. It's **opt-in** and requires a one-time setup that installs `faster-whisper` and downloads a Whisper model.

**Critical rule — you must pass `--model` explicitly.** `scribe local setup` refuses to pick a model silently; it exits 2 with a hint if `--model` is omitted. When the user hasn't specified a size, default to the recommended model: **`base`**. It's a ~145 MB download, runs on modest CPUs, and produces good results for most content. Only escalate to `small`/`medium`/`large-v3` if the user mentions quality is insufficient, tricky accents, or critical recordings.

**Setup from agent context:**

```bash
scribe local setup --model base --yes --json
```

`--yes` is required in non-TTY (agent) contexts; the command refuses to run without it. Stream the NDJSON events to show progress; watch for `{"status": "failed", ...}` — the error payload carries the exact pip/pipx command that failed and the captured stderr, which you can show to the user so they can resolve it (permission errors, PEP 668, etc.).

**When to suggest local setup:**

- User asks about offline transcription, privacy, or air-gapped workflows.
- User is frustrated by API rate limits or cost.
- User asks to run without any API key.

**When NOT to set it up unprompted:** don't install faster-whisper (200+ MB of dependencies) or download a model (~145 MB minimum) unless the user asked for offline transcription. Prefer suggesting an API provider for drive-by requests.

For detailed flag coverage see [references/commands.md](references/commands.md) and [references/providers.md](references/providers.md).

## URL Handling — Critical

**Always wrap URLs in double quotes** when passing to scribe. Shells interpret `?` and `&` as special characters:

```bash
# Correct
scribe "https://www.youtube.com/watch?v=abc123"

# Wrong — shell breaks the URL
scribe https://www.youtube.com/watch?v=abc123
```

## Supported Sources

| Source | URL patterns | Notes |
|---|---|---|
| YouTube | `youtube.com/watch?v=`, `youtu.be/`, `youtube.com/shorts/`, `youtube.com/live/` | No auth needed |
| Instagram | `instagram.com/reel/`, `instagram.com/p/` | Requires Instagram credentials in config |
| Local files | `.mp3`, `.mp4`, `.m4a`, `.wav`, `.opus`, `.ogg`, `.flac`, `.webm`, `.aac`, `.wma` | No download step |

## Provider Selection Guidance

When the user asks which provider to use, or when you need to suggest one:

| Scenario | Recommend | Why |
|---|---|---|
| General purpose, most languages | **openai** | Best balance of cost, accuracy, language coverage |
| Multi-speaker (meetings, interviews) | `--diarize` (auto-routes to **deepgram**) | Native diarization, auto-detects speaker count, no file size limit |
| Hindi with speakers (meetings, calls) | `--diarize --language hi-Latn` | **Default for any Hindi/Hinglish multi-speaker content.** Romanized Latin script output, speaker labels, auto-routes to Deepgram Nova |
| Mostly English + some Hindi | `--diarize` (no language flag needed) | Auto-detect handles English well, Hindi words transcribed phonetically |
| Indian languages (Hindi, Tamil, Telugu...) | **sargam** | Specialized for 22 Indian languages, much better than Whisper |
| Highest accuracy, word timestamps | **elevenlabs** | Word-level timestamps, 99 languages |
| Offline / no API key / free | **local** | Runs locally with faster-whisper, zero cost |
| Specific model needed | **openrouter** | Access to various models, but slower and pricier |

For detailed provider comparison (pricing, limits, setup), read [references/providers.md](references/providers.md).

## Handling Transcription Results

After a successful transcription:
1. Tell the user the file path
2. Offer to read the transcript: `Read the file at the output path`
3. Mention the word count and duration
4. If they use Obsidian, remind them to check their workspace location with `scribe config show`

## Batch Transcription

For multiple URLs, create a temporary file and use `scribe batch`:

```bash
# Write URLs to a temp file (one per line)
cat > /tmp/scribe-urls.txt << 'EOF'
https://youtube.com/watch?v=abc123
https://youtube.com/watch?v=def456
EOF

scribe batch /tmp/scribe-urls.txt --json --quiet
```

## Troubleshooting

When something goes wrong:

1. **First:** Run `scribe doctor` to get system diagnostics
2. **Check** the error message — most are self-explanatory
3. **Common fixes:** Read [references/troubleshooting.md](references/troubleshooting.md)

## Safety Rules

1. **Never read or display `~/.anyscribecli/.env`** — it contains API keys and passwords
2. **Use `scribe config show`** to display settings (it masks sensitive values)
3. **Never hardcode API keys** in commands or output
4. **Don't run `scribe onboard`** without telling the user first — it's interactive and takes control of the terminal
5. **Warn before `scribe update`** — it modifies the installed package

## Configuration

App config lives at `~/.anyscribecli/`. Transcripts default to `~/anyscribe/` (configurable). For details on all settings, file locations, and workspace structure, read [references/config.md](references/config.md).

Quick config changes:
```bash
scribe config set provider elevenlabs    # Switch provider
scribe config set language hi            # Set default language
scribe config set keep_media true        # Keep audio files
scribe config set deepgram_api_key KEY   # Set API key (stored in .env)
```

## What scribe Outputs

Each transcription creates a markdown file with YAML frontmatter (title, source URL, duration, language, word count, reading time, tags) followed by the transcript text. Files are organized by source platform:

```
~/anyscribe/sources/<platform>/<slug>.md
```

An `_index.md` file is auto-updated with links to all transcripts. Daily logs are written to `daily/YYYY-MM-DD.md`.
