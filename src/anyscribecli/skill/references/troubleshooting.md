# Troubleshooting ascli

## Diagnostic First Step

Always start with:
```bash
ascli doctor
```
This checks dependencies, config, installation, and updates. Include output in any bug report.

## Common Errors

### "command not found: ascli"

ascli is not on PATH.

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
ascli transcribe "https://www.youtube.com/watch?v=VIDEO_ID"
```

Or run `ascli transcribe` with no URL and paste at the interactive prompt (no quoting needed).

### "OPENAI_API_KEY not set" (or other API key errors)

The required API key is missing from `~/.anyscribecli/.env`.

**Fix:**
```bash
ascli onboard --force    # Re-run setup to enter keys
```

### "yt-dlp download failed: Video unavailable"

The video is private, age-restricted, geo-blocked, or deleted.

**Fix:**
1. Try a different video to confirm ascli works
2. Update yt-dlp: `pip install --upgrade yt-dlp`
3. If age-restricted: yt-dlp may need browser cookies (advanced)

### Instagram "login_required" errors

Instagram rate-limits third-party access.

**Fix:**
1. Wait a few minutes and retry
2. Verify credentials: `ascli config show`
3. Consider using a secondary Instagram account
4. Re-enter credentials: `ascli onboard --force`

### Transcription in wrong language

Auto-detection guessed incorrectly.

**Fix:** Force the correct language:
```bash
ascli transcribe "url" --language en    # or es, fr, hi, etc.
```

Or set a default: `ascli config set language hi`

### "Provider error" or API failures

**Fix:**
1. Test the provider: `ascli providers test`
2. Check API key is valid and has credits
3. Try a different provider: `ascli transcribe "url" --provider openai`

### Large video taking very long

Videos >30 min are auto-chunked. Each chunk transcribes separately. This is normal.

**Estimate:** Cloud APIs process roughly at real-time speed. Local (CPU) is 2-5x real-time.

### Config or workspace corruption

**Fix:**
```bash
ascli doctor    # Check what's wrong
```

Nuclear option (loses config — transcripts are separate at `~/anyscribe/`):
```bash
rm -rf ~/.anyscribecli
ascli onboard
```

Back up `~/anyscribe/` first if transcripts matter (or check `ascli config show` for custom workspace path).

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
