# anyscribe Command Reference

## anyscribe (default: transcribe)

Transcribe a URL or local audio/video file to markdown. A bare URL routes to transcribe automatically — no subcommand needed.

```bash
anyscribe "<url>"                         # YouTube/Instagram URL (always quote)
anyscribe /path/to/file.mp3              # Local audio/video file
anyscribe transcribe                     # Interactive prompt (no quoting needed)
anyscribe --clipboard                    # Read URL from clipboard
anyscribe transcribe "<url>"             # Explicit subcommand (also works)
```

### Flags

| Flag | Short | Description | Default |
|------|-------|-------------|---------|
| `--quality` | | Quality preset: accuracy \| balanced \| cost \| free (picks a provider) | From config (accuracy) |
| `--provider` | `-p` | Override provider: openai, deepgram, elevenlabs, sargam, groq, openrouter, local (wins over `--quality`) | From config |
| `--model` | `-m` | Pin the model for this run (see [providers.md](providers.md) for each provider's list) | Provider default, or `provider_models` in config |
| `--language` | `-l` | Language code (en, es, fr, hi, hi-Latn, etc.) or "auto" | From config (auto) |
| `--json` | `-j` | Output result as JSON | Off |
| `--keep-media` | | Keep downloaded audio in `~/.anyscribe/downloads/audio/` | From config |
| `--diarize` | `-d` | Enable speaker diarization (auto-routes to Deepgram if configured) | Off |
| `--force` | `-f` | Re-transcribe even if this source was already transcribed | Off |
| `--quiet` | `-q` | Suppress progress output | Off |
| `--clipboard` | `-c` | Read URL from system clipboard | Off |

### Model selection (`--model` / `-m`)

`-m` pins the model on whichever provider ends up handling the run — the one from `-p`, from `--quality`, or from config. Precedence, highest first:

1. `-m` on the command line
2. `provider_models.<provider>` in `config.yaml`
3. The provider's built-in default (first entry in its model list)

```bash
scribe "url" -p openai -m whisper-1               # force Whisper (default is gpt-transcribe)
scribe "url" -p groq -m whisper-large-v3          # higher accuracy than the turbo default
scribe "url" -p openrouter -m google/gemini-2.5-flash
```

Unknown models are rejected before any download or API call, with the valid list in the error — **except `openrouter`**, which accepts any slug (including anything in `extra_models.openrouter`) and only fails at the API. Providers with one model (`elevenlabs`, `sargam`) accept only that model. `local` has no `-m`: use `scribe local setup --model <size>` or `scribe config set local_model <size>`.

**Timestamp caveat — and why you usually do nothing.** `gpt-transcribe` (the OpenAI default), `gpt-4o-transcribe`, and `gpt-4o-mini-transcribe` don't return segment timestamps. When `output_format` is `timestamped` / `diarized`, scribe switches the run to `whisper-1` itself and emits `switched to whisper-1 — gpt-transcribe can't produce timestamps`. **Passing `-m` suppresses that switch** — an explicit per-run model always wins — so don't pass `-m gpt-transcribe` for a user who wants timestamps. A config pin does not suppress it.

### The plan line

Every run prints `→ <provider> · <model> (<via>)` to **stderr**, with one indented line per note:

```
→ openai · whisper-1 (config)
    WARNING: quality 'balanced' wants deepgram but no DEEPGRAM_API_KEY is set — using openai instead
    switched to whisper-1 — gpt-transcribe can't produce timestamps
```

`via` ∈ `flag` | `diarize` | `quality: <tier>` | `config`. It's stderr, so it never contaminates `--json` stdout; `--quiet` suppresses it. Surface the notes to the user — they are the only place fallbacks and auto-switches are announced.

### Duplicate detection

Before transcribing, anyscribe scans the vault for a transcript whose frontmatter `source:` matches the URL/path. If found, it returns that existing file instead of re-transcribing — no download, no API cost. JSON output carries `"cached": true`; human output prints `Already transcribed: <path> — use --force to re-transcribe.` Pass `--force` / `-f` to override and transcribe fresh.

### Supported local file types

`.mp3`, `.mp4`, `.m4a`, `.wav`, `.opus`, `.ogg`, `.flac`, `.webm`, `.aac`, `.wma`

### JSON output

```json
{
  "success": true,
  "file": "/Users/you/anyscribe/sources/youtube/title.md",
  "title": "Video Title",
  "platform": "youtube",
  "duration": "12:34",
  "language": "en",
  "word_count": 1500,
  "provider": "openai",
  "model": "gpt-transcribe",
  "via": "config",
  "notes": [],
  "cached": false
}
```

`model` is the model that actually ran — read it rather than assuming the pin, since scribe may have switched it (timestamps) or the provider may have come from a tier. `via` says which rung picked the provider (`flag` | `diarize` | `quality: <tier>` | `config`), and `notes` carries every swap or warning in machine-readable form (keyless-tier fallback, whisper-1 timestamp switch, diarize routing) — surface any `WARNING:` note to the user even in `--quiet` runs. Batch `--json` carries the same two fields at the top level.

When the source was already in the vault, the same shape comes back with `"cached": true` and the existing file's path.

On error:
```json
{
  "success": false,
  "error": "yt-dlp download failed: Video unavailable"
}
```

### Examples

```bash
# YouTube video (bare URL — transcribes directly)
anyscribe "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

# YouTube short
anyscribe "https://www.youtube.com/shorts/abc123"

# Instagram reel
anyscribe "https://www.instagram.com/reel/C17LiBLyIOe/"

# Local file
anyscribe /path/to/podcast.mp3
anyscribe ~/recordings/meeting.m4a

# Override provider for one transcription
anyscribe "https://youtube.com/watch?v=abc123" --provider elevenlabs

# Override provider AND model for one transcription
scribe "https://youtube.com/watch?v=abc123" -p openai -m gpt-transcribe

# Force language detection
anyscribe "https://youtube.com/watch?v=abc123" --language hi

# Machine-readable output for scripting
anyscribe "https://youtube.com/watch?v=abc123" --json --quiet

# Re-transcribe a source already in the vault (skip the cache shortcut)
anyscribe "https://youtube.com/watch?v=abc123" --force

# From clipboard
anyscribe --clipboard
```

---

## anyscribe download

Download video or audio without transcribing.

```bash
anyscribe download "<url>"                 # Download video
anyscribe download "<url>" --audio-only    # Download audio only
anyscribe download                         # Interactive prompt
anyscribe download --clipboard             # From clipboard
```

### Flags

| Flag | Short | Description | Default |
|------|-------|-------------|---------|
| `--video` / `--audio-only` | | Download video (default) or audio only | `--video` |
| `--json` | `-j` | Output as JSON | Off |
| `--quiet` | `-q` | Suppress progress | Off |
| `--clipboard` | `-c` | Read URL from clipboard | Off |

### Output locations

- Video: `~/.anyscribe/downloads/video/<platform>/`
- Audio: `~/.anyscribe/downloads/audio/<platform>/`

---

## anyscribe batch

Transcribe multiple URLs or files from a list.

```bash
anyscribe batch urls.txt
```

### Input file format

One URL or file path per line. Blank lines and `#comments` are skipped.

```
https://youtube.com/watch?v=abc123
https://youtube.com/watch?v=def456
# this line is skipped
/path/to/local-recording.mp3
```

### Flags

| Flag | Short | Description | Default |
|------|-------|-------------|---------|
| `--provider` | `-p` | Override provider | From config |
| `--model` | `-m` | Pin the model for every URL in the batch | Provider default, or `provider_models` in config |
| `--language` | `-l` | Override language | auto |
| `--json` | `-j` | Output as JSON | Off |
| `--keep-media` | | Keep audio files | From config |
| `--force` | `-f` | Re-transcribe sources already in the vault | Off |
| `--quiet` | `-q` | Suppress progress | Off |
| `--stop-on-error` | | Stop at first failure | Off (continues) |
| `--timeout` | | Per-URL timeout in seconds. A timed-out URL is marked failed (`"timed out after Ns"`) and the batch moves to the next URL | None (no timeout) |

Sources already in the vault are skipped (returned from cache) unless `--force` is passed. The summary table marks those rows `CACHED`, and each such result carries `"cached": true`.

### JSON output

```json
{
  "total": 3,
  "succeeded": 2,
  "failed": 1,
  "results": [
    {"success": true, "url": "...", "file": "...", "title": "...", "cached": false, ...},
    {"success": false, "url": "...", "error": "..."}
  ]
}
```

### Examples

```bash
# Cap each URL at 5 minutes; stop-on-error not set, so it moves to the next one
anyscribe batch urls.txt --timeout 300

# Run the whole batch on a cheaper model
anyscribe batch urls.txt -p openai -m gpt-4o-mini-transcribe --json --quiet
```

---

## anyscribe rm

Delete a transcript from the workspace and resync the master `_index.md`.

```bash
anyscribe rm "sources/youtube/my-video.md"    # by path
anyscribe rm my-video                          # by slug (filename without .md)
anyscribe rm my-video --yes --json             # skip prompt, machine output
```

Accepts a full file path or a bare slug. If a slug matches more than one transcript, `rm` prints the matches and exits — pass a full path to disambiguate. Daily logs under `daily/` are left untouched as history; only the transcript file and its master-index row are removed.

### Flags

| Flag | Short | Description | Default |
|------|-------|-------------|---------|
| `--yes` | `-y` | Skip the confirmation prompt (required in non-TTY / agent contexts) | Off |
| `--json` | `-j` | Output result as JSON | Off |

### JSON output

```json
{ "success": true, "data": { "deleted": "sources/youtube/my-video.md" }, "error": null }
```

Exits 1 (with `error` set) when no transcript matches, the slug is ambiguous, or the file cannot be deleted.

---

## anyscribe logs

View recent transcription activity and any recovery artifacts left behind by failed runs.

```bash
anyscribe logs                     # last 20 entries, newest first
anyscribe logs --limit 50          # more entries
anyscribe logs --json              # machine-readable
```

Reads the workspace's `daily/*.md` logs — there's no separate log store, so this is
always in sync with what's actually in the vault. Also lists files in the recovery
directory (audio saved from a failed transcription) so you know what's safe to
retry or delete.

### Flags

| Flag | Short | Description | Default |
|------|-------|-------------|---------|
| `--limit` | `-n` | Number of log entries to show | `20` |
| `--json` | `-j` | Output result as JSON | Off |

### JSON output

```json
{
  "success": true,
  "data": {
    "entries": [
      {"date": "2026-07-04", "time": "09:12", "platform": "youtube", "entry": "[[sources/youtube/title.md|Video Title]]", "duration": "12:34"}
    ],
    "recovery": [
      {"name": "youtube/abc123.mp3", "size": 4821932, "mtime": "2026-07-03T22:14:01"}
    ]
  },
  "error": null
}
```

Empty state (human output): `No activity logged yet.`

### Examples

```bash
# Quick check on what was transcribed today
anyscribe logs --limit 5

# Machine-readable for a status dashboard
anyscribe logs --json --limit 100
```

---

## anyscribe ui

Launch a local web dashboard in the browser. Visual interface for transcribing, browsing history, and managing settings.

```bash
anyscribe ui                  # opens browser at http://127.0.0.1:8457
anyscribe ui --port 9000      # custom port
anyscribe ui --no-open        # don't auto-open browser
```

### Flags

| Flag | Short | Description | Default |
|------|-------|-------------|---------|
| `--port` | `-p` | Port to listen on | `8457` |
| `--no-open` | | Don't auto-open browser | Off |

Local only (127.0.0.1). Stop with Ctrl+C.

---

## anyscribe tray

Menu-bar/tray icon that supervises `anyscribe ui` as a subprocess — click to open instead of running a command. **Needs the `[tray]` extra**: `pip install -U "anyscribe[tray]"` (pystray, Pillow, pyobjc on macOS). Without it, the command prints an install hint and exits 1 instead of crashing.

```bash
anyscribe tray                # start the tray, default port 8457
anyscribe tray --port 9000    # supervise a server on a different port
```

Menu: Open UI, Status (running/stopped), Restart server, Check for updates… (opens the GitHub releases page), Quit.

- If a server is already listening on the port, `anyscribe tray` attaches to it instead of starting a second one.
- If a tray is already running (pidfile at `~/.anyscribe/tray.pid`), a second `anyscribe tray` refuses to start rather than colliding.
- Quit / SIGTERM / SIGINT all run the same teardown: stop the server *if the tray started it*, remove the pidfile.

### Flags

| Flag | Short | Description | Default |
|------|-------|-------------|---------|
| `--port` | `-p` | Port the supervised web server listens on | `8457` |

---

## anyscribe install-service / anyscribe uninstall-service

Auto-start `anyscribe tray` at login. **macOS only for now** — other platforms get a clean "not supported yet" error, not a crash.

```bash
anyscribe install-service --yes --json     # writes + loads ~/Library/LaunchAgents/com.anyscribe.tray.plist
anyscribe uninstall-service --yes --json   # unloads + deletes it
```

### Flags

| Flag | Short | Description |
|------|-------|-------------|
| `--yes` | `-y` | Skip confirmation prompt. Required in non-TTY (agent) contexts. |
| `--json` | `-j` | Output result as JSON: `{"success": true, "data": {...}, "error": null}` |

`install-service` returns `{"plist": "<path>"}`; `uninstall-service` returns `{"removed": true|false}`. This only toggles login auto-start — it doesn't stop a tray that's currently running (quit that from its menu) and doesn't uninstall anyscribe itself.

---

## anyscribe config

View and change settings.

```bash
anyscribe config                           # Defaults dashboard — what the next run uses
anyscribe config --json                    # Same, machine-readable (settings + resolved + providers)
anyscribe config show                      # Display all settings
anyscribe config show --json               # Output as JSON
anyscribe config set <key> <value>         # Change a setting
anyscribe config list-keys --json          # Every settable key + current value
anyscribe config path                      # Print config file location
```

### `scribe config` (no subcommand) — the discovery call

**This is the one command to run when you need to know what scribe will do.** Human output:

```
Next run: deepgram · nova-3 (quality: balanced)

Provider      Default model           Alternatives      Key      Notes
→ deepgram    nova-3                  nova-2            ✓        balanced
  elevenlabs  scribe_v2                                 missing  accuracy
  groq        whisper-large-v3-turbo  whisper-large-v3  missing  cost
  local       —                                         —        free, local_model: base
  openai      gpt-transcribe          3 more            missing
  openrouter  openai/gpt-audio-mini   5 more            missing
  sargam      saaras:v3                                 missing

Missing keys:    elevenlabs, groq, openai, openrouter, sargam  (scribe config set <provider>_api_key <key>)
Change provider: scribe config set provider <name>  (also sets quality = custom, so it sticks)
Pin a model:     scribe config set provider_models.<provider> <model>
Or pick a tier:  scribe config set quality accuracy|balanced|cost|free|custom
```

`--json` returns every setting plus:

```json
{
  "resolved": {"provider": "deepgram", "model": "nova-3", "via": "quality: balanced", "notes": []},
  "providers": [
    {"name": "deepgram", "default_model": "nova-3", "models": ["nova-3", "nova-2"],
     "has_key": true, "tier": "balanced", "pinned": false, "custom_models": []}
  ]
}
```

`resolved` answers "what runs next and why"; `providers` answers "what can I change it to". `→` in the table marks `resolved.provider`, which is **not** always `provider` in the settings — a quality tier can override it. `scribe config show --json` is the raw settings file only (plus `_resolved_workspace`); prefer `scribe config --json` for anything decision-shaped.

### Settable keys

| Key | Values | Description |
|-----|--------|-------------|
| `provider` | openai, deepgram, elevenlabs, sargam, groq, openrouter, local | Provider used when `quality` is `custom`. **Setting it also writes `quality=custom`** |
| `quality` | accuracy, balanced, cost, free, custom | Tier that picks the provider, or `custom` to use `provider` |
| `provider_models.<provider>` | a model id from that provider's list | Pin a model for one provider (see below) |
| `extra_models.openrouter` | comma-separated slugs (empty clears) | Add your own OpenRouter models to the pickers. Openrouter only |
| `local_model` | tiny, base, small, medium, large-v3, large-v3-turbo, distil-large-v3.5 | Default offline Whisper size (must already be cached) |
| `language` | auto, en, es, fr, hi, ar, zh, ja, ko, ... | Default language |
| `keep_media` | true, false | Keep audio after transcription |
| `output_format` | clean, timestamped, diarized | Transcript format |
| `prompt_download` | never, ask, always | Download video after transcription |
| `local_file_media` | skip, copy, move, ask | Handle local file originals |
| `instagram.browser` | string | Browser to read IG cookies from. Optional — only needed for private reels. Supported: `firefox`, `chrome`, `safari`, `brave`, `edge`, `chromium`, `vivaldi`, `opera` |
| `openai_api_key` | string | OpenAI API key (stored in .env) |
| `deepgram_api_key` | string | Deepgram API key (stored in .env) |
| `elevenlabs_api_key` | string | ElevenLabs API key (stored in .env) |
| `sargam_api_key` | string | Sarvam AI API key (stored in .env) |
| `groq_api_key` | string | Groq API key (stored in .env) |
| `openrouter_api_key` | string | OpenRouter API key (stored in .env) |

Use dot-notation for nested keys: `anyscribe config set instagram.browser firefox`

```bash
# Configure browser for IG cookies (only if needed for private/rate-limited reels)
anyscribe config set instagram.browser firefox
```

API key names are also accepted — they are stored in `~/.anyscribe/.env`, not config.yaml:
```bash
anyscribe config set deepgram_api_key YOUR_KEY
```

### Pinning a model per provider

```bash
scribe config set provider_models.openai whisper-1
scribe config set provider_models.groq whisper-large-v3
scribe config set provider_models.deepgram nova-2
```

The key is `provider_models.<provider>` — one pin per provider, so switching providers keeps each one's chosen model. A provider with no entry uses its built-in default. Invalid models exit 1 with the valid list; `openrouter` accepts any slug. `elevenlabs` and `sargam` have exactly one model, so pinning is a no-op. `provider_models.local` is rejected — use `local_model`.

### Adding models (openrouter only)

```bash
scribe config set extra_models.openrouter "qwen/qwen3-omni-flash,openai/gpt-audio"
scribe config set extra_models.openrouter ""     # empty value removes the entry
```

Comma-separated or a JSON list (MCP/web). Added slugs merge into every picker and are marked `(custom)` in `providers list`. `extra_models.<anything else>` exits 1: *custom models are only supported for openrouter (curated lists elsewhere)*. Don't work around it — new models for the other providers arrive via `scribe update`.

See [config.md](config.md) for the resulting `config.yaml` shape and [providers.md](providers.md) for each provider's models.

---

## anyscribe providers

Manage transcription providers.

```bash
anyscribe providers list                   # Show available providers
anyscribe providers list --json            # Output as JSON
anyscribe providers test                   # Test active provider
anyscribe providers test <name>            # Test a specific provider
```

`providers list` prints four columns: **Provider**, **Model** (the one in effect — the pin from `provider_models` if set, otherwise the provider's default), **Also available** (its other models, with user-added slugs suffixed ` (custom)`), and **Active**.

`--json` gives you the same thing per provider — use this instead of guessing model names:

```json
[
  {
    "name": "openai",
    "active": true,
    "model": "gpt-transcribe",
    "models": ["gpt-transcribe", "whisper-1", "gpt-4o-transcribe", "gpt-4o-mini-transcribe"],
    "custom_models": []
  }
]
```

`model` is that provider's effective model; `models` is the full pickable list including `extra_models` (empty for `local`, whose sizes come from `scribe model list`); `custom_models` is just the user-added slugs.

> **`active` is the `provider` setting, not necessarily what runs** — a quality tier can override it. For the effective provider, use `scribe config --json` → `resolved`.

---

## anyscribe local

Lifecycle for offline transcription — installs / uninstalls faster-whisper and the first Whisper model. All three subcommands accept `--json`.

```bash
anyscribe local setup --model base --yes --json     # Install + download + persist
anyscribe local status --json                       # Report readiness, cached sizes
anyscribe local teardown --yes --json               # Reverse setup
```

### anyscribe local setup

| Flag | Short | Description | Default |
|------|-------|-------------|---------|
| `--model` | `-m` | **Required.** `tiny`, `base`, `small`, `medium`, `large-v3`, `large-v3-turbo`, `distil-large-v3.5`. Recommended: `base`. | *none — must specify* |
| `--yes` | `-y` | Skip confirmation. Required in non-TTY contexts. | Off |
| `--json` | `-j` | NDJSON progress events on stdout. | Off |

**Agent rule:** always pass `--model` — the CLI refuses to pick one silently. Default to `base` unless the user asks otherwise.

**Exit codes:**
- `0` — set up (or already set up).
- `1` — install/download failure. JSON stderr carries the exact command that failed and its stderr.
- `2` — usage error (missing `--model`, unknown size, non-TTY without `--yes`).

### anyscribe local status

Always exits 0. Reports `set_up`, `faster_whisper_installed`, `faster_whisper_version`, `ffmpeg_ok`, `default_model`, `models` (cache state per size), `total_disk_bytes`, `install_method`.

### anyscribe local teardown

`--yes` is required. Uninstalls faster-whisper, deletes every cached model, resets `settings.provider` to `openai` if it was `local`.

---

## anyscribe model

Cache management for offline Whisper models. All subcommands accept `--json`.

Valid sizes: `tiny`, `base`, `small`, `medium`, `large-v3`, `large-v3-turbo`, `distil-large-v3.5`. See [providers.md](providers.md) for the size/RAM/speed table.

> This is the **local** provider only. Cloud provider models are picked with `-m` / `provider_models` — nothing to download.

```bash
anyscribe model list --json                      # Show every size + cache state
anyscribe model pull <size> --json               # Download (idempotent)
anyscribe model rm <size> --yes --json           # Delete cached weights
anyscribe model reinstall <size> --yes --json    # Delete + re-download (corrupted weights)
anyscribe model info <size> --json               # Inspect a single size
```

**Not set up?** `pull`/`rm` exit 2 with `{error: "local transcription not set up", hint: "run anyscribe local setup ..."}`. `list` still works (shows everything as `cached: false`).

**Size-already-cached semantics:** `pull` returns `{status: "already_present"}` with exit 0. `rm` on a non-cached size returns `{status: "not_present"}` with exit 0.

---

## anyscribe onboard

Configures providers, API keys, and preferences. Two modes:

```bash
# Interactive TUI — for humans typing in a terminal.
anyscribe onboard
anyscribe onboard --force                  # Re-run over existing config
anyscribe onboard --skip-deps              # Skip dependency check

# Headless — for agents / CI / scripts.
anyscribe onboard --provider openai --api-key "$OPENAI_API_KEY" --yes --json
anyscribe onboard --provider local --local-model base --yes --json
anyscribe onboard --provider openai --model whisper-1 --yes --json   # pin a model at setup
anyscribe onboard --provider deepgram --quality balanced --yes --json # set a tier instead
```

**Agent rule:** always use the headless form. The interactive TUI uses arrow-key selectors and blocks on stdin — it cannot be driven programmatically.

| Flag | Required with `--yes` | Default | Description |
|------|-----------------------|---------|-------------|
| `--yes` / `-y` | yes (to opt in) | off | Turn on headless mode. |
| `--provider` / `-p` | yes | none | `openai`, `deepgram`, `elevenlabs`, `sargam`, `groq`, `openrouter`, `local`. |
| `--api-key` | for API providers (or env var) | none | Stored in `.env`. Prefer the env-var form. |
| `--local-model` | yes when `--provider=local` | none | `tiny`, `base`, `small`, `medium`, `large-v3`, `large-v3-turbo`, `distil-large-v3.5`. Recommended: `base`. |
| `--model` / `-m` | no | provider default | Pin `--provider`'s model (writes `provider_models.<provider>`). Exit 2 with the valid list if the provider doesn't offer it. Not for `local`. |
| `--quality` | no | `custom` | `accuracy`, `balanced`, `cost`, `free`, `custom`. **Omitting it writes `custom`**, so `--provider` is what runs. Only pass it if the user asked for a tier. |
| `--workspace` | no | `~/anyscribe` | Obsidian vault path. |
| `--language` | no | `auto` | Default language code. |
| `--keep-media` / `--no-keep-media` | no | off | Keep downloaded audio after transcription. |
| `--output-format` | no | `clean` | `clean`, `timestamped`, `diarized`. |
| `--instagram-browser` | no | — | Browser to read IG cookies from. Optional — only needed for private reels. |
| `--force` / `-f` | no | off | Re-run over existing config. |
| `--json` / `-j` | no | off | Emit the result as a single JSON object on stdout. |

**Result JSON:** `{"status", "provider", "quality", "model", "workspace", "local_enabled", "api_keys_set", "skill_installed"}`. Read `model` back rather than assuming — it reports the effective model, pinned or default.

**Exit codes:** 0 success · 1 setup failure (e.g., local install failed — stderr carries pip command + captured stderr) · 2 usage error (missing `--provider`, unknown provider, unknown `--model`/`--quality`, already configured without `--force`, etc.). Exit-2 stderr is structured JSON with `error` and `choices`.

---

## anyscribe doctor

Run diagnostic checks. Reports on dependencies, config, installation, and updates.

```bash
anyscribe doctor
```

Output includes everything needed for debugging. Suggest this when users report issues.

---

## anyscribe update

Update anyscribe to the latest version.

```bash
anyscribe update                           # Update to latest
anyscribe update --check                   # Check without installing
anyscribe update --force                   # Force update (stashes local changes)
```

---

## anyscribe migrate

One-shot upgrade helper for machines that used the old `anyscribecli` package.
It moves config, API keys, sessions, and downloads from `~/.anyscribecli/` to
`~/.anyscribe/` (never overwriting anything already in the new folder),
refreshes the bundled Claude Code skill, re-keys the MCP server registration to
`anyscribe`, and verifies the `anyscribe`, `scribe`, and `ascli` commands all
resolve. It reports the number of keys moved, never the key values, so its
output is safe to paste into an issue. Idempotent — a second run reports there
is nothing to do.

```bash
anyscribe migrate --dry-run                # preview everything; writes nothing
anyscribe migrate                          # perform the migration
anyscribe migrate --json                   # machine-readable report
```

### Flags

| Flag | Short | Description | Default |
|---|---|---|---|
| `--dry-run` | | Show exactly what would change and write nothing (not even the backup) | Off |
| `--json` | `-j` | Output the report as JSON | Off |

---

## anyscribe --version

```bash
anyscribe --version
# Output: anyscribe v0.13.0
```

---

## anyscribe --help

```bash
anyscribe --help                           # All commands
anyscribe transcribe --help                # Command-specific help
```

---

## Shell Completion

```bash
anyscribe --install-completion             # Install tab completion for your shell
```

Restart your shell after installing.
