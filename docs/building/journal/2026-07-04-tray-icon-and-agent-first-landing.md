---
type: feature
tags: [tray, icon, landing, positioning, pitch, vercel, nano-banana]
tldr: "v0.13.1 + the agent-first repositioning. Pressure-tested the tray icon in a real menu bar (black circle, invisible on dark bars), replaced it with a nano-banana-generated waveform glyph shipped as a macOS template image. Then repositioned the landing page and README around usage priority: AI agents first, Web UI second, CLI last, with a real scribe ui screenshot on the page. Landing deploys via Vercel; Pages workflow removed."
---

# Tray icon + agent-first landing repositioning

**Date:** 2026-07-04
**Version:** 0.13.1 (icon + landing polish) and post-0.13.1 main (repositioning)
**Follows:** [2026-07-04 tray/releases/landing](2026-07-04-tray-releases-landing.md)

## Tray icon: pressure test → real glyph

The 0.13.0 tray shipped with a placeholder icon (Pillow-drawn black circle, flagged
with a `ponytail:` comment). A live pressure test — launching the tray and
screenshotting the actual macOS menu bar — showed it renders as a near-invisible
dark smudge on dark menu bars, and being a non-template image it would never adapt
to light/dark modes.

Replacement pipeline:

1. Generated a five-bar waveform glyph with **nano-banana**
   (`google/gemini-2.5-flash-image` via OpenRouter's chat-completions image
   modality). GPT Image was the intended first choice but both local OpenAI keys
   were `sk-test` placeholders and the direct Gemini key was over quota.
2. Post-processed with Pillow: luminance threshold → pure black + alpha, crop to
   content, 14% margin, 88px square (pystray resizes to the 22px bar itself).
3. Shipped as package data at `src/anyscribecli/assets/tray-icon.png`, loaded via
   `importlib.resources` with the old circle as fallback.
4. Marked as a **template image** by reaching into pystray's darwin backend
   (`icon._icon_image.setTemplate_(True)` in the `run(setup=...)` hook) — macOS
   then tints it correctly for light/dark bars. Wrapped in try/except so a pystray
   internals change degrades gracefully.

Verified at 22px on simulated dark/light bars, in the built wheel, and via a live
tray run. Added a checklist line for the landing version badges while in there.

## Agent-first repositioning (landing + README)

Positioning decision (user): anyscribe is **a tool your AI agents use for you**
first, a clean local Web UI second, and a CLI last. This matches CLAUDE.md's
"the skill is the primary usage path" but the landing page and README both said
the opposite ("The command-line scribe…", "None of the three is primary").

A copy-level pitch audit found ~12 offenders; the worst was the agents section
opening with "Most people never need this section." Rework (Opus subagent,
frontend-design skill):

- Title/H1: **"Let your AI agent scribe anything."**; hero names the three ways
  in priority order; install CTA stays above the fold (verified 1280×800 and
  375×812).
- Page spine = ways to use it: (1) a realistic Claude Code exchange (skill +
  10 MCP tools), (2) the Web UI with a **real screenshot** of `scribe ui`
  (captured via headless Chrome at 2x — desktop-screenshot attempts kept pulling
  in personal windows; headless renders are the clean path), (3) the CLI
  input→output demo, compact, last. The earlier vanity "any." typographic
  section is gone.
- README opening realigned to the same order. Rest untouched.

Verification note: headless Chrome CLI clamps its minimum window width (~500px),
so naive `--window-size=375` screenshots show fake "clipping". A same-origin
iframe probe (`--allow-file-access-from-files`, 375px iframe, measure
`scrollWidth` + offender scan) is the reliable mobile check: scrollWidth == 375,
only self-scrolling code blocks exceed.

## Hosting: Vercel, not GitHub Pages

The user deploys the landing page by importing the repo into Vercel. The Pages
workflow (never enabled, failing on every landing push) is removed; a minimal
`vercel.json` (`outputDirectory: landing`, `cleanUrls`) makes the import
zero-config. The PyPI project page picks up the new README pitch at the next
release.
