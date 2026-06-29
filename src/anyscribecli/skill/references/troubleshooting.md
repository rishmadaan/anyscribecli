# Troubleshooting scribe

## Diagnostic First Step

Always start with:
```bash
scribe doctor
```
This checks dependencies, config, installation, and updates. Include output in any bug report.

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

### Permission denied errors

**Fix:** Check file ownership:
```bash
ls -la ~/.anyscribecli/
```

If owned by root (from sudo install), fix:
```bash
sudo chown -R $(whoami) ~/.anyscribecli/
```
