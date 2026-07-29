---
name: anyscribe
description: >
  Use anyscribe to transcribe video/audio from YouTube, Instagram,
  or local files into markdown. Activate when the user wants to transcribe a URL
  or file, download media, configure transcription providers, manage their anyscribe
  setup, batch-process multiple URLs, or troubleshoot anyscribe issues.
allowed-tools: Bash(anyscribe *), Bash(scribe *), Read
---

# anyscribe — Transcription CLI Operator Guide

You are an expert operator of `anyscribe`, a CLI tool that transcribes video/audio into structured markdown files in an Obsidian vault. `scribe` is a shorter, permanent alias for the same command — use whichever you like; every example here uses `anyscribe`.

## Before Running Any Command

**Pre-flight check** — on first use in a session, verify anyscribe is available:

```bash
anyscribe --version
```

If not installed: suggest `pip install anyscribe`. If installed but not configured (no `~/.anyscribe/config.yaml`): guide the user through `anyscribe onboard`.

**Windows note:** If `anyscribe` is not on PATH (common on Windows), use `python -m anyscribe` instead of `anyscribe` for all commands. Example: `python -m anyscribe "url" --json --quiet`.

## Core Principle: Use --json for Machine Output

When YOU run anyscribe commands, always use `--json --quiet` flags so you can parse structured output. Show the user a clean summary, not raw JSON.

```bash
anyscribe "URL" --json --quiet
```

Parse the JSON result and present it conversationally:
- On success: file path, title, duration, word count, provider used
- On failure: the error message in plain language, plus a fix

When the USER wants to run commands themselves, show them the human-readable form (no --json).

## Command Decision Tree

| User wants to... | Command |
|---|---|
| Transcribe a URL or local file | `anyscribe "url"` or `anyscribe /path/to/file` |
| Pick accuracy vs cost | `anyscribe "url" --quality accuracy\|balanced\|cost\|free` (default `balanced` → Deepgram; picks the provider) |
| Transcribe with speaker diarization | `anyscribe "url" --diarize` (auto-routes to Deepgram if configured) |
| Hindi / Hinglish with speakers | `anyscribe "url" --diarize --language hi-Latn` — **always use this combo for Hindi content with multiple speakers** |
| Re-transcribe a source already in the vault | `anyscribe "url" --force` (skips the "already transcribed" shortcut) |
| Transcribe multiple URLs | `anyscribe batch urls.txt` |
| Delete / remove a transcript | `anyscribe rm <path-or-slug>` |
| Download video/audio only | `anyscribe download "url"` or `anyscribe download "url" --audio-only` |
| See recent activity / what did I transcribe recently | `anyscribe logs` |
| Change settings | `anyscribe config set <key> <value>` |
| See current config | `anyscribe config show` |
| Switch provider | `anyscribe config set provider <name>` |
| Test a provider | `anyscribe providers test <name>` |
| List providers | `anyscribe providers list` |
| Set up offline transcription | `anyscribe local setup --model base --yes` *(see rule below)* |
| Check offline-transcription state | `anyscribe local status --json` |
| Download another Whisper model | `anyscribe model pull <size> --json` |
| List downloaded Whisper models | `anyscribe model list --json` |
| Delete a cached Whisper model | `anyscribe model rm <size> --yes --json` |
| Remove offline transcription | `anyscribe local teardown --yes --json` |
| Initial setup (interactive, for a human) | `anyscribe onboard` (or `--force` to re-run) |
| Initial setup (headless, agent or script) | `anyscribe onboard --provider X --api-key $KEY --yes --json` *(see rule below)* |
| Use the web UI | `anyscribe ui` (opens browser dashboard at 127.0.0.1:8457) |
| Keep anyscribe available in the menu bar / always running | `anyscribe tray` (needs `pip install "anyscribe[tray]"` first) |
| Auto-start the menu bar at login (macOS) | `anyscribe install-service` |
| Remove menu-bar auto-start | `anyscribe uninstall-service` |
| Diagnose problems | `anyscribe doctor` |
| Update anyscribe | `anyscribe update` |
| Check for updates | `anyscribe update --check` |

For complete command syntax and all flags, read [references/commands.md](references/commands.md).

## Onboarding (First-Run Setup) — Agent Rules

anyscribe has three equivalent setup paths: an interactive CLI wizard (`anyscribe onboard`), a Web UI wizard (first-run modal on `anyscribe ui`), and a headless flag-driven path (`anyscribe onboard --yes`). **You must use the headless path.** The interactive wizards need a TTY / browser — they'll either hang or produce no output in an agent context.

**Rule: do not run `anyscribe onboard` without `--yes` in agent contexts.** If the user asks you to "set up anyscribe," use:

```bash
anyscribe onboard --provider <name> --api-key "$KEY_ENV_VAR" --yes --json
```

For local/offline transcription as primary provider:

```bash
anyscribe onboard --provider local --local-model base --yes --json
```

**Prefer env vars over `--api-key` on argv** — argv leaks into shell history. Reference the env var by name (`"$OPENAI_API_KEY"`) in examples you give the user.

**Don't guess missing flags.** If the user hasn't told you which provider or model to use, ask them — don't default to one silently. The recommended model for `--provider local` is `base` per [`references/providers.md`](references/providers.md); other defaults (workspace, language, output format) are sane and the user can adjust them in Settings later.

**Already configured?** `anyscribe onboard --yes` without `--force` exits 2 when `~/.anyscribe/config.yaml` exists. If the user wants to reconfigure, pass `--force`.

## Local (Offline) Transcription Workflow

The `local` provider runs Whisper on the user's own machine via `faster-whisper` — no API, no network. It's **opt-in** and requires a one-time setup that installs `faster-whisper` and downloads a Whisper model.

**Critical rule — you must pass `--model` explicitly.** `anyscribe local setup` refuses to pick a model silently; it exits 2 with a hint if `--model` is omitted. When the user hasn't specified a size, default to the recommended model: **`base`**. It's a ~145 MB download, runs on modest CPUs, and produces good results for most content. Only escalate to `small`/`medium`/`large-v3` if the user mentions quality is insufficient, tricky accents, or critical recordings.

**Setup from agent context:**

```bash
anyscribe local setup --model base --yes --json
```

`--yes` is required in non-TTY (agent) contexts; the command refuses to run without it. Stream the NDJSON events to show progress; watch for `{"status": "failed", ...}` — the error payload carries the exact pip/pipx command that failed and the captured stderr, which you can show to the user so they can resolve it (permission errors, PEP 668, etc.).

**When to suggest local setup:**

- User asks about offline transcription, privacy, or air-gapped workflows.
- User is frustrated by API rate limits or cost.
- User asks to run without any API key.

**When NOT to set it up unprompted:** don't install faster-whisper (200+ MB of dependencies) or download a model (~145 MB minimum) unless the user asked for offline transcription. Prefer suggesting an API provider for drive-by requests.

For detailed flag coverage see [references/commands.md](references/commands.md) and [references/providers.md](references/providers.md).

## URL Handling — Critical

**Always wrap URLs in double quotes** when passing to anyscribe. Shells interpret `?` and `&` as special characters:

```bash
# Correct
anyscribe "https://www.youtube.com/watch?v=abc123"

# Wrong — shell breaks the URL
anyscribe https://www.youtube.com/watch?v=abc123
```

## Supported Sources

| Source | URL patterns | Notes |
|---|---|---|
| YouTube | `youtube.com/watch?v=`, `youtu.be/`, `youtube.com/shorts/`, `youtube.com/live/` | No auth needed |
| Instagram | `instagram.com/reel/`, `instagram.com/p/` | Public reels usually work with no setup. For private/rate-limited reels, configure browser cookies (see below) |
| Local files | `.mp3`, `.mp4`, `.m4a`, `.wav`, `.opus`, `.ogg`, `.flac`, `.webm`, `.aac`, `.wma` | No download step |

## Instagram Setup

For Instagram reels — public reels usually work with no setup.
For private reels or rate-limited cases, configure cookies from a browser:

```bash
anyscribe config set instagram.browser firefox
```

Supported values: `firefox`, `chrome`, `safari`, `brave`, `edge`, `chromium`, `vivaldi`, `opera`.

If the user asks which browser to specify, ask which browser they use when logged into Instagram.

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
4. If they use Obsidian, remind them to check their workspace location with `anyscribe config show`

## Duplicate Detection ("Already transcribed")

anyscribe scans the vault before transcribing. If a source URL or file path was already
transcribed (matched against each transcript's frontmatter `source:`), it returns the
**existing** file instead of re-transcribing — no download, no API cost.

In `--json` output this shows up as `"cached": true`; in human output as
`Already transcribed: <path> — use --force to re-transcribe.` In `anyscribe batch`
the row is marked `CACHED`.

**When the user hits this:** tell them it's already transcribed and where the file is.
Only pass `--force` / `-f` if they explicitly want a fresh re-transcription (e.g. they
changed provider or the source was updated):

```bash
anyscribe "url" --force --json --quiet
```

`--force` works on both `anyscribe` (transcribe) and `anyscribe batch`.

## Deleting a Transcript

When the user wants to remove or delete a transcript, use `anyscribe rm`:

```bash
anyscribe rm "sources/youtube/my-video.md" --yes --json   # by path
anyscribe rm my-video --yes --json                          # by slug (filename, no .md)
```

- Accepts a full path or a bare slug. If a slug matches more than one file, `rm` lists the
  matches and exits — pass a full path to disambiguate.
- `--yes` / `-y` skips the confirmation prompt (required in agent contexts — the prompt
  needs a TTY).
- The master `_index.md` row is removed automatically. Daily logs are left intact as history.

## Batch Transcription

For multiple URLs, create a temporary file and use `anyscribe batch`:

```bash
# Write URLs to a temp file (one per line)
cat > /tmp/anyscribe-urls.txt << 'EOF'
https://youtube.com/watch?v=abc123
https://youtube.com/watch?v=def456
EOF

anyscribe batch /tmp/anyscribe-urls.txt --json --quiet
```

Pass `--timeout <seconds>` to cap how long each URL is allowed to run; a timed-out
URL is marked failed (`"timed out after Ns"`) and the batch continues to the next
URL (combine with `--stop-on-error` to halt instead):

```bash
anyscribe batch /tmp/anyscribe-urls.txt --timeout 300 --json --quiet
```

## Viewing Recent Activity

When the user asks what they transcribed recently, or wants to check on failed
runs, use `anyscribe logs`:

```bash
anyscribe logs                 # last 20 entries, human-readable
anyscribe logs --limit 50 --json   # more entries, machine output
```

It reads the workspace's `daily/*.md` logs (newest first) — there's no separate
logging system, so nothing here can drift from what's actually in the vault. It
also lists any **recovery artifacts**: audio saved from a failed transcription so
it doesn't need to be re-downloaded. Point the user at `anyscribe "url"` (or
`--force`) to retry, or tell them it's safe to delete if they've moved on.

## Troubleshooting

When something goes wrong:

1. **First:** Run `anyscribe doctor` to get system diagnostics
2. **Check** the error message — most are self-explanatory
3. **Common fixes:** Read [references/troubleshooting.md](references/troubleshooting.md)

## Safety Rules

1. **Never read or display `~/.anyscribe/.env`** — it contains API keys and passwords
2. **Use `anyscribe config show`** to display settings (it masks sensitive values)
3. **Never hardcode API keys** in commands or output
4. **Don't run `anyscribe onboard`** without telling the user first — it's interactive and takes control of the terminal
5. **Warn before `anyscribe update`** — it modifies the installed package

## Configuration

App config lives at `~/.anyscribe/`. Transcripts default to `~/anyscribe/` (configurable). For details on all settings, file locations, and workspace structure, read [references/config.md](references/config.md).

Quick config changes:
```bash
anyscribe config set provider elevenlabs    # Switch provider
anyscribe config set language hi            # Set default language
anyscribe config set keep_media true        # Keep audio files
anyscribe config set deepgram_api_key KEY   # Set API key (stored in .env)
```

## What anyscribe Outputs

Each transcription creates a markdown file with YAML frontmatter (title, source URL, duration, language, word count, reading time, tags) followed by the transcript text. Files are organized by source platform:

```
~/anyscribe/sources/<platform>/<slug>.md
```

An `_index.md` file is auto-updated with links to all transcripts. Daily logs are written to `daily/YYYY-MM-DD.md`.
