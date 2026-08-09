# Changelog

What changed in each release of anyscribe, newest first.

This file is for **users** — what changed for you, and whether you need to do
anything about it. `BACKLOG.md` is the developer-facing companion: the same
releases with implementation detail, plus the roadmap and parked ideas.

Install or upgrade with `pip install --upgrade anyscribe`. Versions follow
SemVer; while we're on `0.x`, a minor bump can carry a breaking change.

---

## 0.16.4 — 2026-08-09

**Fixed**
- `pip install anyscribe` no longer prints `WARNING: typer 0.27.1 does not
  provide the extra 'all'`. We were asking for a `typer` extra that typer
  removed; plain `typer` has bundled the same pieces since 0.12. Cosmetic only —
  nothing behaved differently.

**Added**
- This changelog. CI now fails if a version is tagged without an entry here, so
  it can't silently fall behind.

## 0.16.3 — 2026-08-09

**Fixed — affects the MCP server only**
- `anyscribe-mcp` failed to start on any machine that installed it fresh on or
  after 2026-07-28, with `ModuleNotFoundError: No module named
  'mcp.server.fastmcp'`. The MCP library released a version 2 that renamed the
  piece we imported, and we hadn't pinned a version range, so new installs
  picked up the incompatible one. **If you hit this, `pip install -U
  "anyscribe[mcp]"` fixes it.** Existing installs were unaffected.

**Changed**
- The MCP server now speaks protocol revision `2026-07-28`, the current spec.
- Hosts (Claude Desktop, Cursor) now show the server as `anyscribe` with its
  version, instead of the old `scribe` name and a blank version. Resource
  addresses (`scribe://config` and friends) are unchanged, so nothing that
  referenced them breaks.

## 0.16.2 — 2026-08-09

**Changed**
- Every message anyscribe prints now says `anyscribe`, matching the docs.
  `scribe` and `ascli` remain permanent aliases you can keep typing.
- `sarvam` is accepted anywhere a provider name is entered, as a spelling of
  `sargam`. Previously some surfaces silently reported a keyless provider as
  configured.
- `anyscribe ui` now tries the next port (up to 10) when yours is busy instead
  of failing.

## 0.16.1 — 2026-08-09

**Added**
- Rebuilt user documentation as three routes: using anyscribe through an AI
  agent, through the web dashboard, or through the terminal. New agents guide,
  a getting-started that leads with the installer, a separate troubleshooting
  page, and an honest cost-to-start table per provider.
- macOS "open at login" toggle for the menu-bar tray.

**Fixed**
- `install.sh` on fresh Apple Silicon Macs; both installers now include the tray
  extra. The web UI's "setup needed" banner no longer sticks when your only
  configured provider is local.

## 0.16.0 — 2026-07-31

**Changed — action may be needed**
- The project is now `anyscribe`, not `anyscribecli`. The command is
  `anyscribe`; **`scribe` and `ascli` keep working permanently.** Config moved
  from `~/.anyscribecli/` to `~/.anyscribe/` automatically. If anything looks
  missing after upgrading, run `anyscribe migrate` once.

## 0.15.1 — 2026-07-29

**Added**
- The Settings page shows a "Next run" banner telling you exactly which provider
  and model your next transcription will use.
- Provider and model controls are always visible (they used to be hidden until
  you picked "custom"), plus a new Downloads & media section.

## 0.15.0 — 2026-07-29

**Changed**
- Picking a provider now sticks. Previously the quality preset could silently
  override your choice.
- Every run prints the provider and model it chose, and why.
- A quality tier that needs a key you don't have now warns instead of quietly
  falling back to something else.
- `anyscribe config` with no arguments is now a defaults dashboard.
- OpenAI defaults to `gpt-transcribe`, switching to `whisper-1` automatically
  when you ask for timestamps or speaker labels.

**Removed**
- The `OPENROUTER_MODEL` environment variable — set the model in config instead.

## 0.14.1 — 2026-07-29

**Fixed**
- Several transcription bugs from 0.14.0: a malformed language field in
  frontmatter, a crash on an empty `provider_models:` config block, OpenAI
  speaker labels, and Sarvam speaker labels (not supported upstream — now says
  so). Turbo local models pulled during the brief 0.14.0 window need
  re-downloading.

## 0.14.0 — 2026-07-29

**Added**
- Pick the model per provider, not just the provider: `--model/-m` on
  `transcribe` and `batch`, dropdowns in the web UI.

**Changed**
- Refreshed every provider's model list against what each service actually
  offers. OpenRouter's old default had been removed upstream and was silently
  broken.

## 0.13.4 — 2026-07-16

**Fixed**
- Audio files over 25 MB but under 18 minutes no longer lose the original file.
- Groq's API key was not detected in pre-flight checks.

## 0.13.3 — 2026-07-14

**Added**
- Remove a saved provider API key from the web UI (Settings → Providers), with
  a two-step confirm. The secrets file is now created private to your user.

## 0.13.2 — 2026-07-04

**Fixed**
- The menu-bar tray icon was invisible in 0.13.1.

## 0.13.1 — 2026-07-04

**Changed**
- Real tray icon and landing-page copy pass. *Contains the invisible-icon
  regression fixed in 0.13.2 — skip straight to 0.13.2.*

## 0.13.0 — 2026-07-04

**Added**
- Menu-bar tray companion that keeps the web UI running, with start-at-login.

## 0.12.0 — 2026-07-04

**Added**
- `anyscribe logs`, a `--timeout` for batch runs, and live download progress for
  local model downloads in the web UI.

## 0.11.0 — 2026-07-03

**Added**
- Duplicate detection — re-transcribing the same source returns the existing
  file unless you pass `--force`.
- Delete a transcript from any surface (`anyscribe rm`, web UI, MCP).
- Cancel and retry buttons in the web UI.

## 0.10.1 — 2026-06-29

**Fixed**
- Sarvam rejected exactly-30-second audio chunks.

## 0.10.0 — 2026-06-29

**Changed**
- Instagram downloads moved to yt-dlp with browser-cookie authentication.

## 0.9.0 — 2026-06-29

**Added**
- Quality picker — choose accuracy, balanced, cost, or free and let anyscribe
  route to the right provider. Groq added as a provider.

## 0.8.4 — 2026-05-28

**Fixed**
- Release hardening, Windows file-locking issues, pre-flight check fixes.

## 0.8.2 — 2026-04-20

**Fixed**
- The web UI's "Browse local file" no longer submits the moment you pick a file,
  so you can set options first.

## 0.8.1 — 2026-04-18

**Added**
- First-run setup wizard in the web UI, and `anyscribe onboard --yes` for
  agents and scripts — the same setup available three ways.
- Local (offline) transcription: opt-in setup and model management.

## 0.7.4 – 0.7.4.7.2 — 2026-04-18

**Added**
- The web UI itself (`anyscribe ui`): a local dashboard for transcribing and
  configuring, followed by a rapid series of usability fixes — inline API key
  setup, retry and checkpoints, pre-flight checks, cross-platform install
  scripts, a shutdown button, file upload, and a per-provider language picker.

## 0.7.0 – 0.7.2.3 — 2026-04-16

**Added**
- Speaker labels (diarization) and the Deepgram provider. Setting API keys via
  `config set`. Asking for speaker labels routes to Deepgram automatically.

## 0.6.0 — 2026-04-05

**Added**
- The MCP server, so Claude Desktop, Cursor, and other MCP hosts can use
  anyscribe directly.

## 0.5.0 – 0.5.4 — 2026-03-30 → 2026-04-01

**Added**
- Configurable workspace path, Windows support, and automatic yt-dlp updates
  when it goes stale.

## 0.4.0 – 0.4.1 — 2026-03-30

**Added**
- Local file transcription, and the Claude Code skill that installs itself.

## 0.3.0 – 0.3.1 — 2026-03-27 → 2026-03-29

**Added**
- The `download` command. First PyPI release.

## 0.2.0 — 2026-03-26

**Added**
- Instagram, all remaining providers, batch mode, config, and onboarding.

## 0.1.0 — 2026-03-26

**Added**
- First release: YouTube video → markdown transcript via OpenAI.
