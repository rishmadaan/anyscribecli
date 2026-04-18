---
type: plan
tags: [web-ui, tray, menu-bar, distribution, autostart, future]
tldr: "Future plan — turn the existing `scribe ui` into a click-to-open menu-bar/tray companion that supervises the FastAPI server and auto-starts at login. Cross-platform via pystray, shipped as an optional `[tray]` extra. Browser remains the UI surface — no Tauri/Electron. Deferred to ~v0.9.x."
---

# Menu-bar tray companion — future plan

**Date:** 2026-04-18
**Status:** Deferred — not building now. Target ~v0.9.x. See [BACKLOG.md](../../../BACKLOG.md#v090--menu-bar-tray-companion-planned).

## Context — why we explored this

Today `scribe ui` runs uvicorn in the foreground: user types a command, tab stays open, Ctrl+C to kill. If the web UI were the *primary* way to use anyscribe (instead of the CLI), that flow needs to feel more like "launch an app" than "run a server". The question: what's the minimum lift to get a click-to-open, always-there experience without introducing a native-app build chain?

We ruled out Tauri/Electron up front. The browser is a good enough UI surface; what's missing is **supervision, discoverability, and auto-start** — not a bespoke window.

## Sketch

Two new commands, one new long-running process. Reuses the existing FastAPI server and `/shutdown` endpoint — no new architecture.

```
scribe tray                   # runs tray icon + supervises uvicorn as subprocess
scribe install-service        # registers launchd/systemd/startup autostart for `scribe tray`
scribe uninstall-service      # removes it
```

Tray menu (via `pystray` — cross-platform, one code path):

```
● anyscribe — running
──────────────
Open UI                       → webbrowser.open("http://127.0.0.1:8457")
Status: idle                  (or "transcribing 1 of 2")
──────────────
Check for updates…
Restart server
──────────────
Quit
```

### Package layout

- `cli/tray.py` — pystray loop, subprocess supervision, webbrowser open (~150 LOC)
- `cli/service.py` — generators for launchd `.plist` / systemd `.service` / Windows startup `.lnk` (~100 LOC)
- Icon assets — `icon.png` (mac/Linux, template-style monochrome) and `icon.ico` (Windows)
- Extras in `pyproject.toml`: `anyscribecli[tray]` → pulls `pystray` + `pillow` (+ `pyobjc` on macOS, `python-xlib` on Linux transitively)

Base `pip install anyscribecli` stays CLI-only. Invoking `scribe tray` without the extras fails with a one-line hint: `Run: pip install -U 'anyscribecli[tray]'`.

## Pressure test — what could go wrong

### pystray cross-platform reality

- **Linux Wayland**: GNOME 40+ dropped system tray. Users need the AppIndicator extension or see nothing. Not fixable by us — document it. Headless servers skip tray entirely.
- **macOS**: icon must be a template image (monochrome + alpha) or it looks awful in dark mode. Test both appearances before shipping.
- **Windows**: requires `.ico` format, not `.png`. Must ship both formats in package data.
- **Threading**: `pystray.Icon.run()` blocks main thread. Server must run as subprocess (cleaner than thread — separate process means server crashes don't take the tray down).

### Distribution via pip / curl

- Tray extras pull `pyobjc` on macOS (~30MB), `python-xlib` on Linux, Pillow everywhere. Bloats CLI-only installs if bundled by default — hence the `[tray]` extra.
- `install.sh` (if extended) should default to CLI-only and offer `--with-tray` opt-in, not the reverse.
- `pipx install 'anyscribecli[tray]'` is probably the recommended path for tray users — isolates the env cleanly.

### Auto-start resolution bugs

- launchd plists need an absolute path to the `scribe` binary. That path varies by install method (pipx `~/.local/pipx/venvs/...`, pip `--user`, homebrew, venv). If the user reinstalls Python or switches install methods, the plist points at a dead binary and **silently fails at next login**.
- Mitigation: `install-service` resolves via `shutil.which("scribe")` at install time and also writes a `scribe doctor` check that revalidates. Consider generating the plist with `{python_path} -m anyscribecli tray` instead of `scribe tray` — marginally more resilient since the module path is stable within a given Python install.
- systemd user units don't need `loginctl enable-linger` for tray use (user is logged in when tray matters). Skip that complexity.

### Update-from-tray (the riskiest piece)

- `pip install -U` only works if you invoke the **right** pip. pipx installs need `pipx upgrade`; `pip --user` installs need `--user`; venv installs need that venv's pip. Getting this wrong silently installs into the wrong env and does nothing visible.
- Detect install mode by inspecting `sys.prefix` + checking for pipx markers (`~/.local/pipx/venvs/anyscribecli`). Pick the right command accordingly.
- After upgrade, the running tray process still has old code loaded. Cleanest UX: show "Update installed — click Quit to relaunch." `os.execv` self-restart is possible but fragile across platforms; not worth it for v1.
- **Never update while a job is in flight.** Query `/api/jobs/active` first, disable the menu item or warn if any are running.

### Port & instance collisions

- If user ran `scribe ui` manually and tray tries to start a second server, port 8457 collides and uvicorn dies. Tray should probe the port first — if already responding to `/health`, attach to it (open the UI, show "running" status) rather than spawning its own.
- Pidfile at `~/.anyscribecli/tray.pid` for cross-instance detection. Stale pidfiles after crashes — check if PID still alive before trusting it.

### Signal & shutdown

- Tray apps have no TTY so Ctrl+C is irrelevant. Quit menu → POST `/shutdown` → wait up to 5s → `SIGTERM` subprocess → exit. Don't leave zombies.

## Minimal ship order

Ship in this order, stop whenever "enough":

1. **`scribe tray` + `[tray]` extra** — works without auto-start; users launch manually from terminal or Dock
2. **`scribe install-service` for macOS only first** (launchd). Highest-leverage platform. Add Linux/Windows later if anyone asks.
3. **Port probe + pidfile** — small; prevents the most common confusing failure (double-launch → silent port collision)
4. **Skip self-update in v1.** "Check for updates" opens the GitHub releases page in the browser. Revisit once install-mode detection is bulletproof — it's the single piece most likely to eat an afternoon and produce subtle breakage.

Estimated code footprint: ~250 LOC, one new optional dep family, zero changes to the existing server. No Tauri/Rust/Electron.

### Accepted tradeoffs

- Linux Wayland users without AppIndicator get a degraded experience (documented, not fixed).
- "Check for updates" is a browser link in v1, not an in-place button (defers the install-mode detection minefield).
- Auto-start on login means a background process users didn't explicitly start every session — the always-visible tray icon + obvious Quit item is what keeps this honest.

## Why deferred

The current web UI is fine for the CLI-forward workflow most users have today. Pushing web-first is a product bet that the UI is ready to carry primary usage — that case strengthens after v0.8.0's cache/dedup and error-handling work lands. Revisiting once the UI has more reasons to stay open (history browsing, search, long jobs).
