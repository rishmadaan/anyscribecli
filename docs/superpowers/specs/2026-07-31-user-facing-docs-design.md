# anyscribe: user-facing documentation rebuild — design

**Date:** 2026-07-31
**Status:** Approved by Rishabh (brainstorm session); revised per Opus 5
independent review (approve-with-changes, all findings folded in).
**Research basis:** 7-agent ultracode sweep over README, landing, docs/user/, install scripts, ui/src, CLI surface, and provider code. Key findings inline below.

## Goal

Reposition anyscribe's documentation from dev-tool docs to product docs for
**AI-tool power users** — people who use Claude/ChatGPT daily, can run a guided
one-line install and paste an API key, but arrive expecting the agent
integration to be the headline. Ship a docs overhaul plus the small product
fixes needed so the docs and the product stop contradicting each other.

## Decisions (locked)

1. **Audience:** AI-tool power users. Terminal-tolerant if guided; agent/skill
   integration front and center.
2. **Scope:** Docs overhaul + quick product fixes. Larger product changes go to
   the backlog (§6).
3. **Docs home:** The landing site (Vercel) becomes the front door with a real
   docs section. README shrinks to a pitch that links there.
4. **Structure:** Three-journey docs site (agent / dashboard / CLI), not a
   polish-in-place or task-recipe rewrite.

## 1. Docs architecture

- `docs/user/*.md` stays the **single source of truth**. Rendering happens at
  **commit time, not deploy time**: `scripts/build-docs.py` (Python, stdlib +
  `markdown`) writes styled HTML into `landing/docs/*.html`, and the output is
  committed. `vercel.json` stays untouched (its `cleanUrls: true` already
  serves `landing/docs/cli.html` at `/docs/cli`). CI gate: re-run the script
  and `git diff --exit-code` — catches both stale output and hand-edited HTML.
  No second copy is ever hand-maintained.
- Docs landing page mirrors the product pitch: three doors in priority order.
  - **Door 1 — "From your AI agent"** (NEW page): connect via Claude Code
    skill + MCP server in ~2 minutes; what you can ask it to do; an honest
    capability map. There are **two agent paths with different reach** and
    the page must present both: (a) the **Claude Code skill**, which shells
    out to the CLI and can reach everything including batch, logs, doctor,
    and update; (b) the **MCP server**, a fixed tool surface (transcribe,
    batch_transcribe, download, list/delete transcripts, get/set config,
    list/test providers, doctor). MCP-unreachable today: logs, update, tray,
    onboard, local setup, model management. The only thing no agent path can
    reach is the tray. Generate the MCP column from the `@mcp.tool()`
    decorators in `src/anyscribe/mcp/server.py` rather than hand-listing it.
  - **Door 2 — "The dashboard"**: one-line install → wizard → and the
    currently-missing "keep it alive" chapter: tray app, autostart, how to
    get back in after Shutdown.
  - **Door 3 — "The CLI"**: existing `commands.md` reference retained; the
    "agentic-first" material (--json, TTY, exit codes) moves to a "For
    scripts and agents" section at the bottom.
- Supporting pages: **Providers & pricing** (one honest table: free local
  path, Deepgram's $200 credit, which providers need a card, real per-minute
  costs) and **Troubleshooting**.
- README becomes: what it is, the install line, one screenshot, links to docs.
  Prerequisites move above the install command. Migration note moves to the
  bottom.
- **Landing page wiring (permitted exception to §4's no-redesign rule):**
  rewrite the footer doc links at `landing/index.html:2025-2036` — which
  currently point at GitHub blob views, the exact thing §5 forbids — to
  `/docs/*`, and add a Docs entry to `nav.links` (`landing/index.html:147`).
  Facts and links only; no style changes.

## 2. Accuracy pass (fix at the source)

- Stale versions (actual 0.16.0): landing says v0.13.1 (×2),
  getting-started.md:85 says 0.8.3, commands.md:1117 says 0.13.0, and
  src/anyscribe/skill/references/commands.md:662 says v0.13.0 (in the skill
  files agents repeat verbatim — highest stakes). Fix all five, and
  **stop printing exact versions in prose** so they cannot drift again.
  Note: some historical version mentions are *correct* copy (e.g.
  skill/references/troubleshooting.md:267 explains a 0.13.1 tray bug) and
  must survive — see the CI gate in §6.
- False claim: landing/index.html:1944 says the wizard installs ffmpeg — it
  does not. Correct the copy.
- False parity claims: getting-started.md:19 ("you never need to hop between
  them") and src/anyscribe/skill/references/config.md:41 ("nothing is
  terminal-only"). Scope them honestly — every *setting* is web-editable, but
  batch, download-only, logs, doctor, update, and tray are CLI-only. The
  skill file matters most: agents repeat it verbatim.
- Move anyscribecli migration note (README.md:68-72) out of Quick Start.
- Sweep the four docs/user files for the power-user voice: keep, but fix
  ordering (installer one-liner becomes Step 1 in getting-started; manual
  Homebrew path becomes an appendix), add "Where in the Web UI?" column to
  the command overview table.
- Quit/Shutdown: fix **getting-started.md:103 only** (sidebar button is
  labelled "Shutdown", Layout.tsx:104). The tray menu genuinely says "Quit"
  (src/anyscribe/cli/tray_cmd.py:179), so commands.md:916/937 and
  skill/references/troubleshooting.md:273/285 are correct and stay.

## 3. Quick product fixes (ship with this effort)

- **install.sh crashes on fresh Apple Silicon (3 bugs):**
  1. `eval "$(/opt/homebrew/bin/brew shellenv)"` after Homebrew install
     (~line 121) — currently the next line can't find brew.
  2. Use the just-installed python3.12's pip, not stale system `pip3` — at
     **all three** call sites: install_package() line 184 (yt-dlp fallback),
     check_python() ~194, and install_scribe() line 277.
  3. pipx fallback (line 287): the `*)` catch-all serves both macOS and
     unrecognised Linux distros — branch on `$OS`: macOS gets
     `brew install pipx`, the Linux fallback keeps a working path.
- install.sh: warn before the Homebrew prompt ("asks for your Mac password,
  takes 10-20 minutes — this is normal"); install the `[tray]` extra at all
  three call sites (pip line 277, pipx ~283, dry-run echo ~273). The
  `INSTALL_METHOD=git` path is **excluded** from tray-extra support (extras
  syntax differs for git URLs; not worth the branch) — state that in a
  comment.
- False "Setup needed" banner shown forever to local-only users: root cause
  is `local` being absent from PROVIDER_KEY_MAP (web/routes/config.py:52), so
  `hasAnyKey` (SetupBanner.tsx:34) stays false; render guard at
  SetupBanner.tsx:57.
- Groq card in the web wizard (OnboardingWizard.tsx:35-41; copy the object
  from cli/onboard.py:197-202) — cheapest cloud provider, currently
  unreachable by click.
- Post-Shutdown screen names how to get back in (Layout.tsx:29-39).
- install.ps1: read-through for the same three bug classes as install.sh
  (env activation after installing a dependency, stale interpreter/pip,
  broken fallback) — the Windows one-liner sits at equal prominence on the
  landing page.
- **Borderline, decide at plan review:** "Open at login" toggle in Settings,
  wired to existing install_service()/uninstall_service() in
  src/anyscribe/core/service.py (~40 lines). Real fix for "the app
  disappears"; largest code change on this list. **macOS-only** (service.py
  is launchctl/plist-based): the toggle is *hidden* on other platforms, not
  disabled, and the docs copy says macOS-only — a silently-inert toggle
  would be a new false claim.

## 4. Explicitly out of scope (backlog)

- Signed .dmg / .exe installer (real fix for zero-terminal users — different
  audience than this effort).
- ffmpeg dependency step inside the web wizard (we fix the false claim
  instead).
- Flipping default quality tier to `free`/local (product-behavior change;
  deserves its own decision — this audience has API keys).
- Landing page pitch/style redesign — facts corrected only.
- Auto-retry on port conflict; sarvam/sargam spelling alias (nice-to-haves;
  backlog).
- Deleting `dist/` — it is gitignored and was never committed; no user ever
  sees it. Local tidy at most, not a spec item.
- Windows *functional* install testing (the install.ps1 read-through in §3 is
  a code review, not a VM run) — revisit when a Windows environment is
  available.

## 5. Success criteria

- A power user landing on the site can go from zero to "Claude transcribed a
  YouTube video for me" following Door 1 alone, without opening any GitHub
  file view.
- Door 2: a reader can install, complete the wizard, and — after closing the
  terminal or rebooting — get back into the dashboard using only what the
  docs told them (tray/autostart chapter).
- Door 3: every CLI command in `--help` output appears in the reference, and
  the "Where in the Web UI?" column is present.
- Docs build: every `docs/user/*.md` renders, no internal docs link 404s,
  and CI fails if committed HTML is stale or hand-edited.
- Fresh-Mac install via the one-liner completes without error.
- No user-facing surface (site, README, docs, skill references, UI copy)
  states a version, capability, or claim that the product contradicts.

## 6. Error handling & testing

- Docs build step: fails loudly in CI if a `docs/user` file fails to render,
  an internal docs link 404s, or the committed HTML differs from a fresh
  render (`git diff --exit-code`).
- Version-drift gate (added to the existing .github/workflows/ci.yml): fail
  if any `v?\d+\.\d+\.\d+` string in docs/user/, landing/, README.md, or
  src/anyscribe/skill/ does not equal pyproject.toml's version — gating on
  the invariant, not today's stale values, so it fires on the *next* drift
  too. Genuine historical references (e.g. skill/references/
  troubleshooting.md:267's 0.13.1 tray-bug note) carry an explicit
  `<!-- version-pin-ok -->` allowlist marker.
- install.sh fixes verified on a clean macOS environment (container/VM or a
  PATH-stripped shell harness) — not just by reading the diff.
- SetupBanner/wizard changes: existing UI lint/build gates; manual smoke of
  the wizard flow.
- Claim sweeps: no "nothing is terminal-only", no "installs ffmpeg" claim;
  Door 1's MCP capability table matches the `@mcp.tool()` set in
  src/anyscribe/mcp/server.py.
