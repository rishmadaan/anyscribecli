# anyscribe: user-facing documentation rebuild — design

**Date:** 2026-07-31
**Status:** Approved by Rishabh (brainstorm session)
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

- `docs/user/*.md` stays the **single source of truth**. A small build step
  renders these markdown files into styled HTML pages under the landing site
  (`landing/docs/…`), matching the landing page's look. No second copy is ever
  hand-maintained.
- Docs landing page mirrors the product pitch: three doors in priority order.
  - **Door 1 — "From your AI agent"** (NEW page): connect via Claude Code
    skill + MCP server in ~2 minutes; what you can ask it to do; an honest
    list of what the agent can and cannot reach (batch, logs, doctor, update,
    tray are terminal-only today).
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

## 2. Accuracy pass (fix at the source)

- Stale versions (actual 0.16.0): landing says v0.13.1 (×2),
  getting-started.md:85 says 0.8.3, commands.md:1117 says 0.13.0. Fix, and
  **stop printing exact versions in prose** so they cannot drift again.
- False claim: landing/index.html:1944 says the wizard installs ffmpeg — it
  does not. Correct the copy.
- False parity claims: getting-started.md:19 ("you never need to hop between
  them") and src/anyscribe/skill/references/config.md:41 ("nothing is
  terminal-only"). Scope them honestly — every *setting* is web-editable, but
  batch, download-only, logs, doctor, update, and tray are CLI-only. The
  skill file matters most: agents repeat it verbatim.
- Move anyscribecli migration note (README.md:68-72) out of Quick Start.
- Delete stale `dist/` (old anyscribecli wheels).
- Sweep the four docs/user files for the power-user voice: keep, but fix
  ordering (installer one-liner becomes Step 1 in getting-started; manual
  Homebrew path becomes an appendix), fix "Quit"→"Shutdown" label mismatch,
  add "Where in the Web UI?" column to the command overview table.

## 3. Quick product fixes (ship with this effort)

- **install.sh crashes on fresh Apple Silicon (3 bugs):**
  1. `eval "$(/opt/homebrew/bin/brew shellenv)"` after Homebrew install
     (~line 121) — currently the next line can't find brew.
  2. Use the just-installed python3.12's pip, not stale system `pip3`
     (~lines 194-277).
  3. pipx fallback: `brew install pipx` instead of re-running the blocked
     `pip3 install --user pipx` (~line 287).
- install.sh: warn before the Homebrew prompt ("asks for your Mac password,
  takes 10-20 minutes — this is normal"); install the `[tray]` extra.
- False "Setup needed" banner shown forever to local-only users
  (ui/src/components/SetupBanner.tsx:36, one line).
- Groq card in the web wizard (OnboardingWizard.tsx:35-41; copy the object
  from cli/onboard.py:197-202) — cheapest cloud provider, currently
  unreachable by click.
- Post-Shutdown screen names how to get back in (Layout.tsx:29-39).
- **Borderline, decide at plan review:** "Open at login" toggle in Settings,
  wired to existing install_service()/uninstall_service() in
  src/anyscribe/core/service.py (~40 lines). Real fix for "the app
  disappears"; largest code change on this list.

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

## 5. Success criteria

- A power user landing on the site can go from zero to "Claude transcribed a
  YouTube video for me" following Door 1 alone, without opening any GitHub
  file view.
- Fresh-Mac install via the one-liner completes without error.
- No user-facing surface (site, README, docs, skill references, UI copy)
  states a version, capability, or claim that the product contradicts.

## 6. Error handling & testing

- Docs build step: fails loudly in CI if a `docs/user` file fails to render
  or an internal docs link 404s.
- install.sh fixes verified on a clean macOS environment (container/VM or a
  PATH-stripped shell harness) — not just by reading the diff.
- SetupBanner/wizard changes: existing UI lint/build gates; manual smoke of
  the wizard flow.
- Accuracy pass verified by grep sweeps: no `0\.(8|13)\.` version strings in
  prose, no "nothing is terminal-only", no "installs ffmpeg" claim.
