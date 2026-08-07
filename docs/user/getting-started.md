---
summary: One installer command, one setup wizard, one transcript — then how to keep scribe running in the background and where to go next.
read_when:
  - First time setting up scribe
  - You want the fastest path to a working transcription
  - You want scribe always running (menu bar, open at login)
  - You're an agent / script and want the headless setup form
---

# Getting Started

Install scribe, run setup, get your first transcript — about 5 minutes.

By the end of this guide you will have:
- scribe installed on your machine
- An Obsidian vault ready to browse your transcripts
- Your first video transcribed to markdown
- scribe running in the background, if you want it there

> **scribe has three equivalent surfaces.** The Web UI, the terminal wizard, and the headless flag-driven CLI all cover the full product. Every *setting* can be changed from either the CLI or the Web UI. A few maintenance commands are CLI-only: `batch`, `logs`, `doctor`, `update`, and `tray`. Pick whichever fits:
>
> - **Prefer clicking?** → `scribe ui` opens a browser dashboard with a setup wizard on first launch. See Option A in Step 2.
> - **Prefer typing?** → `scribe onboard` runs an arrow-key terminal wizard. See Option B.
> - **Writing a script or an AI agent?** → `scribe onboard --provider X --api-key $KEY --yes --json`. See Option C.
>
> All three write the same config and land you in the same place. Transcriptions you start from one surface show up in all of them.

> **Everything runs locally.** The Web UI at `http://127.0.0.1:8457` is a server on your own machine — no cloud account, no sign-up, no telemetry. The only time scribe touches the internet is when *you* ask it to: downloading a YouTube/Instagram source you pointed it at, calling whichever transcription API provider you set up, or pulling a Whisper model for offline transcription (once, the first time). Point it at a local file with the local provider and the whole pipeline runs offline — your audio never leaves your machine.

## What you need

- **A computer running macOS, Linux, or Windows** (native Windows and WSL2 both work). The one-line installer below brings the rest: Python, ffmpeg, and yt-dlp.
- **Then pick one engine:**
  - **Free, offline** — the **local** provider. No API key, no internet, runs Whisper on your machine. Downloads a model once during setup.
  - **Or an API key** from one provider — OpenAI is the default. Get one at [platform.openai.com/api-keys](https://platform.openai.com/api-keys); Whisper costs about $0.006/minute, so a 10-minute video is roughly 6 cents. Six cloud providers are supported alongside local — see [providers.md](providers.md) for the comparison.

> **Later, if you want cheaper or more accurate:** each provider offers a few models you can switch between — see [providers.md](providers.md). You don't need to think about this to get started; the defaults are good.

> **New to the command line?** You'll be typing commands in your Terminal app (macOS), terminal emulator (Linux), or Command Prompt / PowerShell (Windows). Every command in this guide starts with `scribe` — just copy-paste and press Enter.

## Step 1 — Install

**macOS / Linux:**
```bash
curl -fsSL https://raw.githubusercontent.com/rishmadaan/anyscribe/main/install.sh | bash
```

**Windows (PowerShell):**
```powershell
irm https://raw.githubusercontent.com/rishmadaan/anyscribe/main/install.ps1 | iex
```

The installer checks for Python 3.10+, ffmpeg, and yt-dlp, installs whatever's missing, then installs scribe with the menu-bar tray included. On Windows it also fixes your PATH so `scribe` works from any terminal.

Verify it worked:

```bash
scribe --version
```

You should see `scribe` followed by a version number.

**Already have Python and just want the package?**

```bash
pip install "anyscribe[tray]"
```

The `[tray]` extra is what gives you the menu-bar icon and open-at-login (see [Keep it running](#keep-it-running)). Plain `pip install anyscribe` works too, and you can add the extra later. With pip you install ffmpeg and yt-dlp yourself — or just run `scribe doctor`, which tells you what's missing.

> **Want to install Python and the dependencies by hand?** See the [Appendix: manual install](#appendix-manual-install) at the bottom.

> **`command not found: scribe` on Windows?** Use `python -m anyscribe` as a drop-in replacement — it always works. See [Troubleshooting](#troubleshooting).

## Step 2 — First run

You can set up scribe either way — both paths save the same config, so pick whichever feels natural.

### Option A (recommended): Web UI

```bash
scribe ui
```

Opens a local dashboard at `http://127.0.0.1:8457`. A **setup wizard pops up on first launch**:

1. **Pick a provider** — cards for `openai` (general purpose, multilingual), `deepgram` (fast, native diarization), `groq` (cheapest and fastest cloud Whisper), `elevenlabs` (high accuracy, 99 languages), `sargam` (Sarvam AI, Indic languages), `openrouter` (many models, one API), plus `local` for free offline transcription on your own machine.
2. **Paste your API key** — with a live **Test** button so you know it works before you continue. (Skipped if you picked `local`.)
3. **Choose whether to also enable offline transcription** — installs faster-whisper and a Whisper model so you have a free fallback.
4. **Confirm your workspace** — where your transcripts live, default `~/anyscribe/`.

Click around — no commands to memorize.

Close the tab when you're finished; to stop the server, hit Ctrl+C in the terminal or click **Shutdown** in the sidebar.

### Option B: Terminal (interactive)

```bash
scribe onboard                   # macOS / Linux
python -m anyscribe onboard      # Windows (first time — prints PATH fix)
```

The wizard uses arrow-key selectors — navigate with **↑↓** and press **Enter** to select:

1. **Check your system** — makes sure `yt-dlp` and `ffmpeg` are installed. Offers to install missing ones.
2. **Choose your provider** — 7 options: OpenAI (default), Deepgram, ElevenLabs, Sarvam AI, Groq, OpenRouter, Local.
3. **Choose that provider's model** — only if it offers more than one. The first is the recommended default; press Enter to take it.
4. **Enter your API key** — stored locally at `~/.anyscribe/.env`. Never sent anywhere except your provider.
5. **Add more provider keys** (optional) — configure multiple providers now or later.
6. **Configure Instagram** (optional) — choose which browser to read Instagram cookies from. Needed only for rate-limited or private reels.
7. **Choose language** — auto-detect (default) or pick a specific language.
8. **Keep audio files** — whether to save the transcription audio to `~/.anyscribe/downloads/audio/`.
9. **Local file handling** — what to do with original files when transcribing local audio/video (skip/copy/move/ask).
10. **Post-transcription downloads** — whether scribe should offer to download the full video after each transcription (never/ask/always).
11. **Choose workspace location** — where to store transcripts (default: `~/anyscribe/`).
12. **Create workspace** — sets up your Obsidian vault at the chosen location.

> **Re-run anytime:** `scribe onboard --force` to change settings — it shows your current config and lets you choose which parts to update. `scribe onboard --skip-deps` to skip the dependency check. Or use the Web UI: Settings → **Run setup wizard**.

### Option C: Headless (for agents + scripts)

If you're automating scribe (CI, a Claude Code agent, a provisioning script), bypass the wizards entirely with `scribe onboard --yes`:

```bash
scribe onboard \
  --provider openai \
  --api-key "$OPENAI_API_KEY" \
  --yes --json
```

Every interactive field maps to a flag. Full reference: [commands.md → scribe onboard](commands.md#scribe-onboard).

## Step 3 — First transcript

Pick any YouTube video and run:

```bash
scribe "https://www.youtube.com/watch?v=VIDEO_ID"
```

Replace `VIDEO_ID` with a real video ID. A short video (under 5 minutes) is good for your first try.

> **No subcommand needed.** Just `scribe "url"` — it knows you want to transcribe. You can also write `scribe transcribe "url"` explicitly, but it's not required.

> **Always wrap URLs in quotes** (`"..."`). Shells like zsh break URLs with `?` in them. Or run `scribe` with no URL and paste it when prompted — no quoting needed.

You'll see:

```
Transcription saved: ~/anyscribe/sources/youtube/how-to-make-perfect-coffee.md
  Title:    How to Make Perfect Coffee
  Duration: 4:32
  Language: en
  Words:    847
```

### Also try

```bash
# Local audio/video file (mp3, mp4, m4a, wav, opus, ogg, flac, webm)
scribe /path/to/podcast.mp3

# Instagram reel
scribe "https://www.instagram.com/reel/SHORTCODE/"

# Just download, no transcription
scribe download "https://www.youtube.com/watch?v=VIDEO_ID"

# From clipboard (copy a URL first)
scribe --clipboard
```

### Browse it in Obsidian

Open Obsidian and select "Open folder as vault", then choose:

```
~/anyscribe/
```

> **Tip:** This folder is in your home directory — it shows up in Finder and file pickers by default. If you chose a custom workspace path during setup, use that path instead.

You'll see:
- **`_index.md`** — a table of all your transcripts, newest first
- **`sources/youtube/`**, **`sources/instagram/`**, and **`sources/local/`** — transcripts organized by source
- **`daily/`** — a log of what you transcribed each day

Each transcript has YAML properties that Obsidian can search and filter:

```yaml
title: "How to Make Perfect Coffee"
platform: youtube
duration: "4:32"
language: en
word_count: 847
reading_time: "4 min"
tags: [transcript, youtube]
```

## Keep it running

`scribe ui` runs in a terminal window, which means the server dies when you close it. If you want scribe to just *be there*, put it in your menu bar.

**The menu-bar icon:**

```bash
scribe tray
```

The tray is a small icon that sits in your menu bar (macOS) or system tray (Linux/Windows) with the web server running behind it. Click it to open the dashboard, no terminal needed. Both one-line installers include the tray by default, so this works right after install. Installed with plain `pip install anyscribe`? Add it with `pip install "anyscribe[tray]"`.

**Start it automatically at login (macOS):**

Open `scribe ui` → **Settings** → **Startup** → toggle **Open at login (menu-bar app)** on. That's it — the menu-bar icon comes back every time you log in.

> The Startup section only appears on macOS. If the tray extra isn't installed, the toggle refuses with a message telling you to run `pip install "anyscribe[tray]"` first — better than a login item that silently fails.

The CLI does the same thing:

```bash
scribe install-service      # register the tray to start at login
scribe uninstall-service    # undo it
```

**The way back in.** Closed the tab, clicked Shutdown, or rebooted? Run `scribe ui` again — or click the menu-bar icon if you set up the tray. Your library, config, and API keys are untouched; nothing about stopping the server touches your data.

See [Commands → scribe tray](commands.md#scribe-tray) and [scribe install-service](commands.md#scribe-install-service) for the full reference.

## Where next

Three doors, depending on how you want to use scribe:

- **[Use scribe from your AI tools](agents.md)** — the Claude Code skill and the MCP server, so you can say "transcribe this" instead of typing commands
- **[Commands](commands.md)** — every command, flag, and example
- **[Providers](providers.md)** — cost, accuracy, languages, and how to switch

Handy things you can do right now:

- **Speaker diarization** — `scribe "url" --diarize` identifies who said what (auto-detects number of speakers). Set up Deepgram first: `scribe config set deepgram_api_key YOUR_KEY` ($200 free credit at [console.deepgram.com](https://console.deepgram.com/))
- **Batch process** — `scribe batch urls.txt` to transcribe a list of URLs
- **See what will run** — `scribe config` shows the provider + model of your next transcription and every alternative
- **Switch providers** — `scribe config set provider elevenlabs` (or let a tier choose: `scribe config set quality accuracy`)
- **Try JSON output** — `scribe "url" --json` for scripting
- **Check health** — `scribe doctor` verifies everything is working
- **Update** — `scribe update` pulls the latest version
- **View all commands** — `scribe --help`

## Instagram (optional)

Public reels usually work out of the box. If you hit rate-limiting, or want
to transcribe reels from accounts you follow, scribe can read your existing
browser session — no password needed:

```bash
scribe config set instagram.browser firefox
```

Supported browsers: `firefox`, `chrome`, `safari`, `brave`, `edge`, `chromium`,
`vivaldi`, `opera`.

> **Tip:** Firefox tends to work most reliably on macOS. Chrome's cookie
> encryption can make extraction flakier.

> **Note for upgraders:** If you onboarded with scribe < 0.8.3, you may have <!-- version-pin-ok -->
> an `INSTAGRAM_PASSWORD` in your `~/.anyscribe/.env`. It's no longer used
> and can be removed.

## Troubleshooting

**"command not found: scribe"** or **"scribe is not recognized"**
You can always use `python -m anyscribe` as a drop-in replacement for `scribe`:
```bash
python -m anyscribe onboard           # works exactly like: scribe onboard
python -m anyscribe transcribe "..."  # works exactly like: scribe transcribe "..."
```

To make the `scribe` shortcut work, add your Python Scripts directory to PATH:
- **macOS**: add the Python framework bin directory to your PATH
- **Linux**: add `~/.local/bin` to your PATH
- **Windows** (PowerShell, run as admin):
  ```powershell
  # Find where pip installed scripts:
  python -c "import sysconfig; print(sysconfig.get_path('scripts'))"
  # Then add that path permanently (replace <path> with the output above):
  [Environment]::SetEnvironmentVariable('Path', [Environment]::GetEnvironmentVariable('Path', 'User') + ';<path>', 'User')
  ```
  Then restart your terminal.

**"OPENAI_API_KEY not set"**
Set the key directly: `scribe config set openai_api_key YOUR_KEY`. Or run `scribe onboard --force` to re-enter it interactively.

**"No matches found" when pasting a URL**
Your shell is interpreting `?` as a special character. Wrap the URL in quotes:
```bash
scribe transcribe "https://www.youtube.com/watch?v=VIDEO_ID"
```
Or run `scribe transcribe` without a URL and paste it at the prompt.

**"yt-dlp download failed"**
scribe automatically updates yt-dlp if it's more than 60 days old (YouTube frequently changes formats, breaking older versions). If you still see this error, the video may be age-restricted, private, or geo-blocked. Try a different video, or manually update: `pip install --upgrade yt-dlp`.

**Instagram "login_required" errors**
Instagram rate-limits anonymous access. Tell scribe which browser to borrow cookies from:
```bash
scribe config set instagram.browser firefox
```
Supported browsers: `firefox`, `chrome`, `safari`, `brave`, `edge`, `chromium`, `vivaldi`, `opera`. Make sure you're already logged in to Instagram in that browser. Firefox tends to work most reliably on macOS.

**Transcription in wrong language**
Force a specific language: `scribe transcribe "url" --language en` (or `es`, `fr`, `hi`, etc.)

**Large video taking too long**
Videos over ~30 minutes are chunked automatically. Each chunk is transcribed separately and merged. This is normal.

## Appendix: manual install

Prefer to install each piece yourself? The one-line installer in Step 1 does all of this for you — this path is for people who'd rather see every step.

**1. Python 3.10 or newer.** Check what you have:

```bash
python3 --version      # macOS / Linux
python --version       # Windows
```

You should see something like `Python 3.12.x`. If you get an error or a version below 3.10:

**macOS:**
```bash
brew install python@3.12
```

**Linux (Ubuntu/Debian):**
```bash
sudo apt install python3 python3-pip python3-venv
```

**Windows:**
Download from [python.org/downloads](https://www.python.org/downloads/) and run the installer. **Check "Add Python to PATH"** during installation.

> **Don't have Homebrew?** It's the standard package manager for macOS. Install it from [brew.sh](https://brew.sh).

**2. ffmpeg and yt-dlp.** ffmpeg converts audio; yt-dlp fetches the video.

**macOS:**
```bash
brew install ffmpeg yt-dlp
```

**Linux (Ubuntu/Debian):**
```bash
sudo apt install ffmpeg
pip install yt-dlp
```

**Windows:**
```powershell
winget install ffmpeg
pip install yt-dlp
```

**3. scribe itself.**

```bash
pip install "anyscribe[tray]"
```

Verify:

**macOS / Linux:**
```bash
scribe --version
```

**Windows:**
```bash
python -m anyscribe --version
```

You should see `scribe` followed by a version number.

> **Why `python -m` on Windows?** pip installs `scribe.exe` to a Scripts directory that's usually not on PATH. `python -m anyscribe` always works because it uses the same Python you installed with. On first run, it will print the exact PowerShell command to add `scribe` to your PATH permanently — after that, you can use `scribe` directly.

**4. Check everything landed:**

```bash
scribe doctor
```

Then head back to **Step 2 — First run** above.

> **Developing on scribe?** [Clone the repo](https://github.com/rishmadaan/anyscribe) and install it editable — see the building docs.

See [Commands](commands.md) for the full reference, [Configuration](configuration.md) for all settings, or [Providers](providers.md) for provider comparison.
