# Troubleshooting anyscribe

## Diagnostic First Step

Always start with:
```bash
anyscribe doctor
```
This checks dependencies, config, installation, and updates. Include output in any bug report.

If the issue is about a specific past run (did it actually transcribe, what
happened to a failed job), also check:
```bash
anyscribe logs
```
It shows recent daily-log activity plus any **recovery artifacts** — audio saved
from a failed transcription so it doesn't need re-downloading. See "Recovery
artifacts left after a failed run" below.

## Common Errors

### "command not found: anyscribe"

anyscribe is not on PATH.

**Fix:**
```bash
python3 -m pip show anyscribe    # Verify it's installed
```

If installed but not found, the Python scripts directory isn't on PATH:
- macOS/Linux: Add `~/.local/bin` to PATH
- Or reinstall: `pip install anyscribe`

### "I upgraded and my keys are gone"

The tool used to store config and API keys in `~/.anyscribecli/`; it now uses
`~/.anyscribe/`. On a normal transcription the move happens automatically, but if
the first command after upgrading was something that created an empty
`~/.anyscribe/` (e.g. `anyscribe ui` or `anyscribe config`) the old keys can be
left behind in the legacy folder.

**Fix:** run the one-shot migration — it moves config, keys, sessions, and
downloads across (never overwriting anything already in the new folder) and
reports exactly what it did:
```bash
anyscribe migrate --dry-run    # preview — writes nothing
anyscribe migrate              # do it
```
It is safe to run more than once; a second run reports there is nothing to do.

### "No matches found" when pasting a URL

The shell is interpreting `?` as a glob character (common in zsh).

**Fix:** Wrap the URL in double quotes:
```bash
anyscribe transcribe "https://www.youtube.com/watch?v=VIDEO_ID"
```

Or run `anyscribe transcribe` with no URL and paste at the interactive prompt (no quoting needed).

### "OPENAI_API_KEY not set" (or other API key errors)

The required API key is missing from `~/.anyscribe/.env`.

**Fix:**
```bash
anyscribe config set openai_api_key sk-proj-...    # Quick — set key directly
anyscribe onboard --force                           # Or re-run setup wizard
```

### "yt-dlp download failed: Video unavailable"

The video is private, age-restricted, geo-blocked, or deleted.

**Fix:**
1. Try a different video to confirm anyscribe works
2. Update yt-dlp: `pip install --upgrade yt-dlp`
3. If age-restricted: yt-dlp may need browser cookies (advanced)

### Instagram: "rate-limit reached" or "login required"

The reel is gated behind login. Configure cookies from a browser logged into
Instagram:

```bash
anyscribe config set instagram.browser firefox
```

Then retry. If you've already configured a browser and still see this:
1. Open Instagram in that browser and confirm you're logged in.
2. Visit the reel URL in that same browser to confirm you can view it.
3. If it loads in the browser but not via anyscribe, your cookie store may be
   locked by the running browser — quit the browser and retry.

### Instagram: "private account"

The reel is from a private account. Cookies from a browser logged into an
account that follows the poster will work; cookies from a different account
won't.

### Instagram: "video unavailable" / "post not found"

The reel was deleted, made private, or is region-locked. There's no
client-side fix.

### Transcription in wrong language

Auto-detection guessed incorrectly.

**Fix:** Force the correct language:
```bash
anyscribe transcribe "url" --language en    # or es, fr, hi, etc.
```

Or set a default: `anyscribe config set language hi`

### "Already transcribed" — nothing got re-transcribed

Not an error. anyscribe found an existing transcript whose frontmatter `source:` matches this URL/path, so it returned that file instead of re-transcribing (no download, no API cost). Human output prints `Already transcribed: <path> — use --force to re-transcribe.`; JSON output has `"cached": true`; batch marks the row `CACHED`.

**If you actually want a fresh transcription** (changed provider, source was updated):
```bash
anyscribe "url" --force
```

**If you want the old one gone entirely:** delete it first with `anyscribe rm <path-or-slug>`, then transcribe again.

### Recovery artifacts left after a failed run

If a transcription fails after the audio was already downloaded, anyscribe saves
that audio to a recovery directory instead of throwing it away. Check for these
with:

```bash
anyscribe logs
```

Recovery artifacts show up in a separate section from the activity log. Re-run
`anyscribe "url"` (or `--force` if it partially wrote a transcript) to retry using
fresh audio, or just delete the file if you've moved on — it's not referenced by
anything else.

### Timestamped or diarized output came out as plain paragraphs

The model that ran doesn't return segment timestamps, so there's nothing to render `[mm:ss]` markers from. On OpenAI that's `gpt-transcribe` (the default), `gpt-4o-transcribe`, and `gpt-4o-mini-transcribe`; `sargam` and `openrouter` never return them either.

**On OpenAI this shouldn't happen by itself** — anyscribe swaps in `whisper-1` when `output_format` is `timestamped`/`diarized` and prints `switched to whisper-1 — gpt-transcribe can't produce timestamps`. So if the user got paragraphs, one of these is true:

1. **The run passed `-m`.** An explicit per-run model suppresses the swap. Re-run without `-m` (or with `-m whisper-1`).
2. **The provider isn't OpenAI.** Sarvam and OpenRouter have no timestamped model to fall back to — switch provider: `anyscribe "url" -p deepgram --force`.
3. **`output_format` is `clean`.** Then there were never going to be timestamps: `anyscribe config set output_format timestamped`.

**Check what actually ran:**
```bash
anyscribe config --json     # resolved.provider, resolved.model, resolved.notes
```

Deepgram and ElevenLabs give word-level timestamps if the user wants finer granularity than Whisper's segments. To force Whisper on every OpenAI run: `anyscribe config set provider_models.openai whisper-1`.

### "Next run" isn't the provider I set

`quality` outranks `provider`. If `quality` is a tier (`accuracy`/`balanced`/`cost`/`free`), the tier picks the provider and the `provider` line is ignored.

```bash
anyscribe config              # look at the (…) after the model — `quality: balanced` means the tier won
```

**Fix:** re-set the provider — that writes `quality: custom` in the same save, which is what makes it stick:
```bash
anyscribe config set provider elevenlabs
```

A config hand-edited in an editor is the usual cause: writing `provider:` without also writing `quality: custom` leaves the tier in charge.

### "WARNING: quality 'X' wants Y but no Y_API_KEY is set"

Not an error — anyscribe ran anyway on the configured `provider`. The tier you chose needs a key you don't have.

**Either add the key:**
```bash
anyscribe config set deepgram_api_key YOUR_KEY
```

**or pick a tier you have a key for** (`anyscribe config` shows which keys are present in the `Key` column).

### OpenRouter: "model not found" / 404

The requested slug isn't available on OpenRouter. Most often this is the **old default `openai/gpt-4o-audio-preview`**, which OpenRouter removed — anything still pointing at it will 404. OpenRouter is the one provider anyscribe doesn't validate models for, so a typo'd or retired slug reaches the API before failing.

**Find the pin:**
```bash
anyscribe config --json     # resolved.model, and providers[].default_model
anyscribe config show       # provider_models.openrouter
```

> A stale `OPENROUTER_MODEL=` line in `~/.anyscribe/.env` is **not** the cause — that env var was removed in 0.15.0 and is no longer read. Tell the user to delete the line and set `provider_models.openrouter` instead. <!-- version-pin-ok -->

**Fix — set a current slug:**
```bash
anyscribe config set provider_models.openrouter openai/gpt-audio-mini
```

Current options: `openai/gpt-audio-mini` (default), `google/gemini-2.5-flash-lite`, `google/gemini-2.5-flash`, `google/gemini-3-flash-preview`, `mistralai/voxtral-small-24b-2507`, `openai/gpt-audio`. Any other audio-capable OpenRouter slug also works — check https://openrouter.ai/models for what's live.

### "Unknown model 'X' for provider 'Y'"

The model isn't in that provider's list. anyscribe rejects it before downloading or spending anything, and the error names the valid models.

**Fix:** run `anyscribe config --json` (or `anyscribe providers list --json`) to see each provider's current model and alternatives, then pick from that list. Note `elevenlabs` and `sargam` have exactly one model each, and `local` has none — its sizes come from `anyscribe model list`, not `-m`.

Two cases that look like bugs but aren't:

- **`saaras:v2.5` is rejected.** Sarvam retired the endpoint it ran on; `saaras:v3` is the only model. An existing pin is dropped automatically on the next run.
- **`extra_models.<provider>` is rejected for everything but openrouter.** By design — those catalogs ship with anyscribe releases because each model needs response-parsing code. The fix is `anyscribe update`, not a config key.

### "Provider error" or API failures

**Fix:**
1. Test the provider: `anyscribe providers test`
2. Check API key is valid and has credits
3. Try a different provider: `anyscribe transcribe "url" --provider openai`

### Large video taking very long

Videos >30 min are auto-chunked. Each chunk transcribes separately. This is normal.

**Estimate:** Cloud APIs process roughly at real-time speed. Local (CPU) is 2-5x real-time.

### Config or workspace corruption

**Fix:**
```bash
anyscribe doctor    # Check what's wrong
```

Nuclear option (loses config — transcripts are separate at `~/anyscribe/`):
```bash
rm -rf ~/.anyscribe
anyscribe onboard
```

Back up `~/anyscribe/` first if transcripts matter (or check `anyscribe config show` for custom workspace path).

### faster-whisper not found (local provider)

**Fix:**
```bash
pip install faster-whisper
```

First run downloads the model from Hugging Face (~150 MB for base). Needs internet for that initial download.

### "The tray companion needs extra packages" / tray won't start

`anyscribe tray` needs the optional `[tray]` extra (pystray, Pillow, and pyobjc on macOS) — the base install doesn't pull it in so `pip install anyscribe` stays lightweight.

**Fix:**
```bash
pip install -U "anyscribe[tray]"
anyscribe tray
```

### Tray runs but no icon in the menu bar

If the server responds at `http://127.0.0.1:8457` but you can't find the waveform icon, check whether a menu-bar manager (Hidden Bar, Bartender, Ice, Dozer) is running. macOS inserts new status items at the LEFT of the strip, which these apps hide by default — expand the manager (chevron icon) and drag the anyscribe waveform to the always-visible side. Also make sure anyscribe is v0.13.2+ (`anyscribe update`): 0.13.1 had a bug where the icon never appeared at all. <!-- version-pin-ok -->

### "An anyscribe tray is already running"

A tray is already active — its pidfile (`~/.anyscribe/tray.pid`) still points at a live process. This is by design: `anyscribe tray` refuses to start a second instance instead of colliding.

**Fix:** Use the existing tray (check the menu bar), or quit it first (menu → Quit, or Ctrl+C in its terminal), then relaunch.

### "port already in use" when starting the tray or `anyscribe ui`

**`anyscribe ui` self-heals — don't prescribe `--port` for it.** A busy port makes it scan the next 10, start on the first free one and print `Port 8457 busy — using 8458.`. It exits 1 only when all 11 are busy; that is the only case where `anyscribe ui --port <n>` is the fix.

**`anyscribe tray` does not roll forward, by design.** If an `anyscribe ui` server is already listening on its port, the tray **attaches** to it rather than erroring — expected behavior, not a bug. A tray on a rolled-forward port would supervise a server nothing else could find, so if a *different, unrelated* process holds the port, give the tray another one explicitly:

```bash
anyscribe tray --port 9000
```

### Fully removing the tray / menu-bar auto-start

1. Quit the tray if it's running (menu → Quit).
2. Remove login auto-start (macOS): `anyscribe uninstall-service --yes`
3. Optionally uninstall the extra: `pip uninstall pystray Pillow`

`uninstall-service` only removes the login LaunchAgent — it doesn't stop an already-running tray or uninstall anyscribe itself.

### Permission denied errors

**Fix:** Check file ownership:
```bash
ls -la ~/.anyscribe/
```

If owned by root (from sudo install), fix:
```bash
sudo chown -R $(whoami) ~/.anyscribe/
```
