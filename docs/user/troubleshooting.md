---
title: Troubleshooting
summary: Errors listed by the exact text scribe prints, each with a plain-English cause and a copy-paste fix.
read_when:
  - scribe printed an error and you want the fix
  - A transcript came out wrong and you don't know why
  - Something worked yesterday and doesn't today
---

# Troubleshooting

Find the error by the text you actually saw. Each entry says what it means and
what to type.

## Start here

Whatever the problem, run this first:

```bash
scribe doctor
```

It checks your dependencies, config, install, and whether an update is
available. If you're asking for help or filing a bug, paste its output — it
contains everything needed to diagnose the issue and no secrets.

If the question is about a *specific past run* — did it actually transcribe,
what happened to the one that failed — check the activity log instead:

```bash
scribe logs
```

That shows recent transcriptions plus any **recovery artifacts**: audio that was
downloaded before a run failed, kept so you don't have to download it again.

---

## Install and startup

### `command not found: scribe` (or `'scribe' is not recognized`)

scribe is installed, but the folder pip put it in isn't on your PATH.

**The instant workaround** — this always works, no setup:

```bash
python -m anyscribe onboard              # same as: scribe onboard
python -m anyscribe transcribe "<url>"   # same as: scribe transcribe "<url>"
```

**To fix the `scribe` shortcut properly**, first confirm it's installed:

```bash
python3 -m pip show anyscribe
```

Then add your Python scripts directory to PATH:

- **macOS** — add the Python framework `bin` directory to your PATH
- **Linux** — add `~/.local/bin` to your PATH
- **Windows** (PowerShell, as administrator):

  ```powershell
  # Find where pip installed the scripts:
  python -c "import sysconfig; print(sysconfig.get_path('scripts'))"
  # Add that path permanently (replace <path> with the output above):
  [Environment]::SetEnvironmentVariable('Path', [Environment]::GetEnvironmentVariable('Path', 'User') + ';<path>', 'User')
  ```

  Then restart your terminal.

### "I upgraded and my API keys are gone"

scribe used to keep config and keys in `~/.anyscribecli/`; it now uses
`~/.anyscribe/`. Normally the move happens by itself on your first
transcription — but if the first thing you ran after upgrading created an empty
new folder (`scribe ui` or `scribe config`, say), the old keys can be stranded
in the legacy folder.

**Fix** — run the one-time migration. It never overwrites anything already in
the new folder, and it reports how many keys it moved, never the keys
themselves:

```bash
anyscribe migrate --dry-run    # preview — writes nothing at all
anyscribe migrate              # do it
```

Safe to run twice: a second run just reports there's nothing left to do.

### "Permission denied"

Usually the app folder is owned by root, from an install run with `sudo`.

```bash
ls -la ~/.anyscribe/                      # check the owner
sudo chown -R $(whoami) ~/.anyscribe/     # hand it back to yourself
```

---

## Input and downloads

### `no matches found` when you paste a URL

Your shell — zsh especially — is treating the `?` in the URL as a wildcard. This
happens before scribe ever runs.

**Fix:** wrap the URL in double quotes.

```bash
scribe transcribe "https://www.youtube.com/watch?v=VIDEO_ID"
```

Or run `scribe transcribe` with no URL and paste it at the prompt, where no
quoting is needed.

### `yt-dlp download failed: Video unavailable`

The video is private, deleted, age-restricted, or blocked in your region.

scribe auto-updates yt-dlp when it's more than 60 days old — YouTube changes
formats often and old versions break — so this is rarely a stale-tool problem.
Still:

1. Try a different video, to confirm scribe itself is working.
2. Update yt-dlp by hand: `pip install --upgrade yt-dlp`
3. If it's age-restricted, yt-dlp needs browser cookies (advanced).

### Instagram: `rate-limit reached` or `login required`

The reel is behind a login wall. Point scribe at a browser you're already
logged into — it borrows the cookies, no password involved:

```bash
scribe config set instagram.browser firefox
```

Supported: `firefox`, `chrome`, `safari`, `brave`, `edge`, `chromium`,
`vivaldi`, `opera`. Firefox is the most reliable on macOS; Chrome's cookie
encryption makes extraction flakier.

Already configured a browser and still seeing this?

1. Open Instagram in that browser and confirm you're logged in.
2. Open the reel URL in that same browser and confirm you can watch it.
3. If it plays in the browser but not through scribe, the cookie store may be
   locked by the running browser — quit the browser and retry.

### Instagram: `private account`

The poster's account is private. Cookies from a browser logged into an account
that *follows* them will work; cookies from any other account won't.

### Instagram: `video unavailable` / `post not found`

The reel was deleted, made private, or is region-locked. Nothing to fix on your
side.

---

## Providers and API keys

### `OPENAI_API_KEY not set` (or any other missing-key error)

The key that provider needs isn't in `~/.anyscribe/.env`.

```bash
scribe config set openai_api_key YOUR_KEY   # set it directly
scribe onboard --force                       # or re-run the wizard
```

### `WARNING: quality 'X' wants Y but no Y_API_KEY is set`

Not an error — scribe went ahead using your configured provider instead. Your
quality tier prefers a provider whose key you don't have.

**Either add the missing key:**

```bash
scribe config set deepgram_api_key YOUR_KEY
```

**Or pick a tier you have a key for.** `scribe config` shows which keys are
present in its `Key` column.

### `Provider error` or general API failures

```bash
scribe providers test                          # is the key valid?
scribe "url" --provider openai                 # does another provider work?
```

If the test fails, the key is wrong, expired, or the account is out of credit.
If the test passes but transcription fails, try another provider to isolate
whether it's the service or the file.

### "Next run" isn't the provider I set

`quality` outranks `provider`. If `quality` is a tier
(`accuracy`/`balanced`/`cost`/`free`), that tier picks the provider and your
`provider` line is ignored.

```bash
scribe config    # look at the (…) after the model — `quality: balanced` means the tier won
```

**Fix:** set the provider through the CLI, which writes `quality: custom` in the
same save — that's what makes the choice stick:

```bash
scribe config set provider elevenlabs
```

Hand-editing `config.yaml` is the usual cause: writing `provider:` without also
writing `quality: custom` leaves the tier in charge.

### `Unknown model 'whisper-2' for openai.`

That model isn't in the provider's list. scribe rejects it before downloading or
spending anything, and the error names the valid options.

```bash
scribe config --json          # each provider's current model and alternatives
scribe providers list --json
```

Two cases that look like bugs but aren't:

- **`elevenlabs` and `sargam` have exactly one model each**, and `local` has
  none — its sizes come from `scribe model list`, not `-m`.
- **`extra_models.<provider>` is rejected for everything except `openrouter`.**
  By design: every other provider's models ship with scribe releases because
  each response shape needs parsing code. The fix is `scribe update`, not a
  config key.

### OpenRouter: `model not found` / 404

The slug you pinned isn't available on OpenRouter. OpenRouter is the one
provider scribe doesn't validate models for — it forwards any name unchanged —
so a typo or a retired slug only fails once the request reaches the API. Old
pins to models OpenRouter has since removed are the most common cause.

**Find the pin:**

```bash
scribe config --json     # resolved.model, and providers[].default_model
scribe config show       # provider_models.openrouter
```

**Set a current slug:**

```bash
scribe config set provider_models.openrouter openai/gpt-audio-mini
```

Any audio-capable OpenRouter slug works — see
[openrouter.ai/models](https://openrouter.ai/models) for what's live today.

> A leftover `OPENROUTER_MODEL=` line in `~/.anyscribe/.env` is **not** the
> cause — that variable is no longer read at all. Delete the line and use
> `provider_models.openrouter` instead.

---

## Transcription results

### "Already transcribed" — nothing got re-transcribed

Not an error. scribe found an existing transcript whose `source:` frontmatter
matches this URL or file, so it handed you that file back instead of
re-downloading and re-paying for it. You'll see
`Already transcribed: <path> — use --force to re-transcribe.` — in JSON that's
`"cached": true`, and in a batch the row is marked `CACHED`.

**If you genuinely want a fresh run** (you switched providers, or the source was
re-uploaded):

```bash
scribe "url" --force
```

**If you want the old one gone entirely:** `scribe rm <path-or-slug>` first,
then transcribe again.

### Transcription came out in the wrong language

Auto-detection guessed wrong.

```bash
scribe "url" --language en        # force it for one run (or es, fr, hi, …)
scribe config set language hi     # or make it the default
```

### Timestamped or diarized output came out as plain paragraphs

The model that ran doesn't return segment timestamps, so there's nothing to
build `[mm:ss]` markers from. On OpenAI that's `gpt-transcribe` (the default),
`gpt-4o-transcribe`, and `gpt-4o-mini-transcribe`; `sargam` and `openrouter`
never return them at all.

**On OpenAI this shouldn't happen on its own** — scribe swaps in `whisper-1`
when your output format is `timestamped` or `diarized`, and prints
`switched to whisper-1 — gpt-transcribe can't produce timestamps`. So if you got
paragraphs, one of these is true:

1. **You passed `-m`.** An explicit per-run model always wins, which suppresses
   the swap. Re-run without `-m`, or with `-m whisper-1`.
2. **The provider isn't OpenAI.** Sarvam and OpenRouter have no timestamped
   model to fall back to. Switch: `scribe "url" -p deepgram --force`
3. **Your `output_format` is `clean`.** There were never going to be timestamps:
   `scribe config set output_format timestamped`

**Check what actually ran:**

```bash
scribe config --json     # resolved.provider, resolved.model, resolved.notes
```

To force Whisper on every OpenAI run:
`scribe config set provider_models.openai whisper-1`. Deepgram and ElevenLabs
give word-level timestamps if you want finer granularity than Whisper's
segments.

### A long video is taking forever

Anything over ~30 minutes is split into chunks and transcribed piece by piece,
then merged. That's normal, not a hang.

**Rough guide:** cloud providers run at roughly real-time speed. Local
transcription on CPU is 2–5× real-time.

### Audio left over after a failed run

When a transcription fails *after* the audio downloaded, scribe keeps that audio
rather than throwing it away, so a retry doesn't re-download it.

```bash
scribe logs
```

Recovery artifacts appear in their own section, separate from the activity log.
Re-run `scribe "url"` to retry (add `--force` if it partly wrote a transcript),
or just delete the file if you've moved on — nothing else references it.

---

## Local (offline) transcription

### `faster-whisper is not installed`

The local provider is opt-in and needs a one-time install:

```bash
scribe local setup --model base
```

That installs faster-whisper into the same Python environment as scribe and
downloads the model. The first download needs internet (~150 MB for `base`);
everything after that is fully offline.

> `--model` is deliberately required — scribe will never pick a model size for
> you. `base` is the recommended starting point.

### Checking what's actually installed

```bash
scribe local status
```

Reports faster-whisper's version, whether ffmpeg is present, which models are
cached, disk usage, and how scribe was installed. It always exits 0, so it's
safe to run before setup.

### Model weights look corrupted

Delete and re-download in one step:

```bash
scribe model reinstall base --yes
```

---

## Web UI and menu-bar tray

### The "Setup needed to start transcribing" banner won't go away

The banner appears when either of two things is missing, and it disappears on
its own — it re-checks every 30 seconds — once both are satisfied:

1. **ffmpeg (and ffprobe) aren't installed.** The banner shows the exact install
   command for your platform, with a copy button.
2. **No transcription provider is set up at all.** Add an API key under
   **Settings → Providers**.

> **Using local transcription only?** That counts. Once faster-whisper is
> installed (`scribe local setup --model base`, or the **Set up local
> transcription** button on the Local provider card in Settings), the provider
> requirement is satisfied without any API key.

You can also dismiss the banner with the ✕ for the current session.

### The Remove key button is missing for a provider

That provider's key is coming from your shell environment — an
`export OPENAI_API_KEY=…` in your shell profile, say — not from
`~/.anyscribe/.env`. scribe can't edit your shell config, so it hides a button
that wouldn't work. Unset it where you set it.

### `The tray companion needs extra packages` / the tray won't start

The tray needs the optional `[tray]` extra (`pystray`, `Pillow`, and `pyobjc` on
macOS). The one-line installers include it by default — if you see this message,
you almost certainly installed with a bare `pip install anyscribe`:

```bash
pip install -U "anyscribe[tray]"
scribe tray
```

### The tray is running but there's no icon in the menu bar

If the server answers at `http://127.0.0.1:8457` but you can't find the waveform
icon, check whether a menu-bar manager is running — Hidden Bar, Bartender, Ice,
Dozer. macOS inserts new status items at the **left** of the strip, which these
apps hide by default. Expand the manager (its chevron) and drag the scribe
waveform to the always-visible side.

> Very old versions had a bug where the icon never appeared at all — fixed in
> 0.13.2. Run `scribe update` if you're on anything older. <!-- version-pin-ok -->

### `A scribe tray is already running.`

A tray is already active and its pidfile (`~/.anyscribe/tray.pid`) still points
at a live process. This is intentional — scribe refuses to start a second tray
rather than collide with the first.

**Fix:** use the existing one (check your menu bar), or quit it first (menu →
Quit, or Ctrl+C in its terminal) and relaunch.

### `port already in use`

If a `scribe ui` server is already listening, `scribe tray` **attaches** to it
instead of erroring — that's expected. If some unrelated process holds the port,
pick another:

```bash
scribe tray --port 9000
scribe ui --port 9000
```

### Removing the tray completely

1. Quit the tray if it's running (menu → Quit).
2. Remove the login auto-start (macOS): `scribe uninstall-service --yes`
3. Optionally drop the extra packages: `pip uninstall pystray Pillow`

`uninstall-service` only removes the login item — it doesn't stop a running tray
or uninstall scribe.

---

## Last resort

### Config or workspace looks corrupted

```bash
scribe doctor     # find out what's actually wrong first
```

The nuclear option resets your config and API keys. **Your transcripts are
safe** — they live separately in `~/anyscribe/`:

```bash
rm -rf ~/.anyscribe
scribe onboard
```

> Check `scribe config show` first if you set a custom workspace path, and back
> up that folder if the transcripts matter to you.

---

## Still stuck?

Run `scribe doctor` and include its full output when you
[open an issue](https://github.com/rishmadaan/anyscribe/issues). It covers
dependencies, config, install type, and version — everything needed to reproduce
your setup, and nothing sensitive.
