# Troubleshooting scribe

## Diagnostic First Step

Always start with:
```bash
scribe doctor
```
This checks dependencies, config, installation, and updates. Include output in any bug report.

If the issue is about a specific past run (did it actually transcribe, what
happened to a failed job), also check:
```bash
scribe logs
```
It shows recent daily-log activity plus any **recovery artifacts** — audio saved
from a failed transcription so it doesn't need re-downloading. See "Recovery
artifacts left after a failed run" below.

## Common Errors

### "command not found: scribe"

scribe is not on PATH.

**Fix:**
```bash
python3 -m pip show anyscribecli    # Verify it's installed
```

If installed but not found, the Python scripts directory isn't on PATH:
- macOS/Linux: Add `~/.local/bin` to PATH
- Or reinstall: `pip install anyscribecli`

### "No matches found" when pasting a URL

The shell is interpreting `?` as a glob character (common in zsh).

**Fix:** Wrap the URL in double quotes:
```bash
scribe transcribe "https://www.youtube.com/watch?v=VIDEO_ID"
```

Or run `scribe transcribe` with no URL and paste at the interactive prompt (no quoting needed).

### "OPENAI_API_KEY not set" (or other API key errors)

The required API key is missing from `~/.anyscribecli/.env`.

**Fix:**
```bash
scribe config set openai_api_key sk-proj-...    # Quick — set key directly
scribe onboard --force                           # Or re-run setup wizard
```

### "yt-dlp download failed: Video unavailable"

The video is private, age-restricted, geo-blocked, or deleted.

**Fix:**
1. Try a different video to confirm scribe works
2. Update yt-dlp: `pip install --upgrade yt-dlp`
3. If age-restricted: yt-dlp may need browser cookies (advanced)

### Instagram: "rate-limit reached" or "login required"

The reel is gated behind login. Configure cookies from a browser logged into
Instagram:

```bash
scribe config set instagram.browser firefox
```

Then retry. If you've already configured a browser and still see this:
1. Open Instagram in that browser and confirm you're logged in.
2. Visit the reel URL in that same browser to confirm you can view it.
3. If it loads in the browser but not via scribe, your cookie store may be
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
scribe transcribe "url" --language en    # or es, fr, hi, etc.
```

Or set a default: `scribe config set language hi`

### "Already transcribed" — nothing got re-transcribed

Not an error. scribe found an existing transcript whose frontmatter `source:` matches this URL/path, so it returned that file instead of re-transcribing (no download, no API cost). Human output prints `Already transcribed: <path> — use --force to re-transcribe.`; JSON output has `"cached": true`; batch marks the row `CACHED`.

**If you actually want a fresh transcription** (changed provider, source was updated):
```bash
scribe "url" --force
```

**If you want the old one gone entirely:** delete it first with `scribe rm <path-or-slug>`, then transcribe again.

### Recovery artifacts left after a failed run

If a transcription fails after the audio was already downloaded, scribe saves
that audio to a recovery directory instead of throwing it away. Check for these
with:

```bash
scribe logs
```

Recovery artifacts show up in a separate section from the activity log. Re-run
`scribe "url"` (or `--force` if it partially wrote a transcript) to retry using
fresh audio, or just delete the file if you've moved on — it's not referenced by
anything else.

### Timestamped or diarized output came out as plain paragraphs

The pinned model doesn't return segment timestamps, so there's nothing for scribe to render `[mm:ss]` markers from. On OpenAI that's `gpt-transcribe`, `gpt-4o-transcribe`, and `gpt-4o-mini-transcribe`; `sargam` and `openrouter` never return them either.

**Check what model is actually in effect:**
```bash
scribe providers list
```

**Fix — go back to a model that keeps timestamps:**
```bash
scribe config set provider_models.openai whisper-1
```

Or drop the pin for a single run: `scribe "url" -p openai -m whisper-1 --force`. Deepgram and ElevenLabs give word-level timestamps if the user wants finer granularity than Whisper's segments.

> This is a model limitation, not a bug — `whisper-1` is the OpenAI default precisely because it keeps timestamps.

### OpenRouter: "model not found" / 404

The requested slug isn't available on OpenRouter. Most often this is the **old default `openai/gpt-4o-audio-preview`**, which OpenRouter removed — anything still pointing at it will 404. OpenRouter is the one provider scribe doesn't validate models for, so a typo'd or retired slug reaches the API before failing.

**Find the pin** — it can live in three places:
```bash
scribe providers list                       # shows the model in effect
scribe config show                          # provider_models.openrouter
grep OPENROUTER_MODEL ~/.anyscribecli/.env  # legacy env var (lowest precedence)
```

**Fix — set a current slug:**
```bash
scribe config set provider_models.openrouter openai/gpt-audio-mini
```

Current options: `openai/gpt-audio-mini` (default), `google/gemini-2.5-flash-lite`, `google/gemini-2.5-flash`, `google/gemini-3-flash-preview`, `mistralai/voxtral-small-24b-2507`, `openai/gpt-audio`. Any other audio-capable OpenRouter slug also works — check https://openrouter.ai/models for what's live.

### "Unknown model 'X' for provider 'Y'"

The model isn't in that provider's list. scribe rejects it before downloading or spending anything, and the error names the valid models.

**Fix:** run `scribe providers list` (or `--json`) to see each provider's current model and alternatives, then pick from that list. Note `deepgram` and `elevenlabs` have exactly one model each, and `local` has none — its sizes come from `scribe model list`, not `-m`.

### "Provider error" or API failures

**Fix:**
1. Test the provider: `scribe providers test`
2. Check API key is valid and has credits
3. Try a different provider: `scribe transcribe "url" --provider openai`

### Large video taking very long

Videos >30 min are auto-chunked. Each chunk transcribes separately. This is normal.

**Estimate:** Cloud APIs process roughly at real-time speed. Local (CPU) is 2-5x real-time.

### Config or workspace corruption

**Fix:**
```bash
scribe doctor    # Check what's wrong
```

Nuclear option (loses config — transcripts are separate at `~/anyscribe/`):
```bash
rm -rf ~/.anyscribecli
scribe onboard
```

Back up `~/anyscribe/` first if transcripts matter (or check `scribe config show` for custom workspace path).

### faster-whisper not found (local provider)

**Fix:**
```bash
pip install faster-whisper
```

First run downloads the model from Hugging Face (~150 MB for base). Needs internet for that initial download.

### "The tray companion needs extra packages" / tray won't start

`scribe tray` needs the optional `[tray]` extra (pystray, Pillow, and pyobjc on macOS) — the base install doesn't pull it in so `pip install anyscribecli` stays lightweight.

**Fix:**
```bash
pip install -U "anyscribecli[tray]"
scribe tray
```

### Tray runs but no icon in the menu bar

If the server responds at `http://127.0.0.1:8457` but you can't find the waveform icon, check whether a menu-bar manager (Hidden Bar, Bartender, Ice, Dozer) is running. macOS inserts new status items at the LEFT of the strip, which these apps hide by default — expand the manager (chevron icon) and drag the scribe waveform to the always-visible side. Also make sure scribe is v0.13.2+ (`scribe update`): 0.13.1 had a bug where the icon never appeared at all.

### "A scribe tray is already running"

A tray is already active — its pidfile (`~/.anyscribecli/tray.pid`) still points at a live process. This is by design: `scribe tray` refuses to start a second instance instead of colliding.

**Fix:** Use the existing tray (check the menu bar), or quit it first (menu → Quit, or Ctrl+C in its terminal), then relaunch.

### "port already in use" when starting the tray or `scribe ui`

If a `scribe ui` server is already listening on that port, `scribe tray` **attaches** to it rather than erroring — that's expected behavior, not a bug. If a *different, unrelated* process holds the port, pick another one:

```bash
scribe tray --port 9000
```

### Fully removing the tray / menu-bar auto-start

1. Quit the tray if it's running (menu → Quit).
2. Remove login auto-start (macOS): `scribe uninstall-service --yes`
3. Optionally uninstall the extra: `pip uninstall pystray Pillow`

`uninstall-service` only removes the login LaunchAgent — it doesn't stop an already-running tray or uninstall scribe itself.

### Permission denied errors

**Fix:** Check file ownership:
```bash
ls -la ~/.anyscribecli/
```

If owned by root (from sudo install), fix:
```bash
sudo chown -R $(whoami) ~/.anyscribecli/
```
