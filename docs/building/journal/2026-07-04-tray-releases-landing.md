---
type: feature
tags: [tray, pystray, launchd, autostart, releases, github-actions, landing, pages, testing]
tldr: "v0.13.0. Ships the menu-bar tray companion planned in 2026-04-18: `scribe tray` (pystray icon supervising the web server as a subprocess, pidfile-guarded against double-launch) and `scribe install-service`/`uninstall-service` (macOS launchd LaunchAgent, RunAtLoad). Live testing surfaced a real bug: pystray's Cocoa event loop can swallow a plain `signal.signal` SIGTERM/SIGINT handler — fixed with a blocked-signal + `signal.sigwait` watcher thread. Also: the PyPI publish workflow now auto-creates a GitHub Release with generated notes on every tag (all 39 historical tags backfilled), and the landing page's parked v3 design direction was executed and wired to a Pages deploy workflow (hosting not yet enabled, pending approval)."
---

# Menu-bar tray companion, GitHub Releases automation, landing page unparked

**Date:** 2026-07-04
**Version:** 0.13.0
**Follows:** the [2026-04-18 tray companion plan](2026-04-18-menu-bar-tray-companion-plan.md) and [2026-07-04 logs/timeout/download-progress entry](2026-07-04-logs-timeout-download-progress.md)

## Tray companion — built to the plan, one real bug found in live testing

The April plan called the scope correctly: `scribe tray` (`cli/tray_cmd.py`) is a `pystray` icon that supervises `scribe ui` as a subprocess, with `core/tray.py` holding the GUI-free, unit-testable bits — pidfile read/write/roundtrip, a TCP connect-probe (`port_responding`) to detect an already-running server, and the GitHub releases URL constant. All pystray/Pillow imports are lazy (inside functions), so the base install stays tray-free and even `scribe tray --help` works without the `[tray]` extra — only actually running the command needs it.

Menu: **Open UI** (opens the browser), **Status** (live `running`/`stopped` via the port probe), **Restart server**, **Check for updates…** (opens the GitHub releases page — the plan's deferred "no real update-from-tray yet" call, unchanged), **Quit**.

**Attach, don't collide.** If a server is already listening on the port, `scribe tray` attaches instead of spawning a second one (`state["proc"] = None` in that case, so teardown knows not to touch it). If a tray is already running, `read_pidfile()` finds a live pid and the command exits 1 with a friendly message instead of a port-bind crash.

**The SIGTERM bug.** The plan assumed a normal signal handler would work for graceful shutdown on `launchctl unload` / logout. It doesn't: pystray's macOS backend runs the Cocoa event loop in Objective-C, and a plain `signal.signal()` handler only fires when Python bytecode is executing — which may never happen while the loop blocks in ObjC. In live testing, `launchctl unload`-ing the LaunchAgent left the server subprocess and pidfile orphaned.

Fix: block `SIGTERM`/`SIGINT` on the main thread (`signal.pthread_sigmask(signal.SIG_BLOCK, ...)`) and catch them synchronously in a dedicated daemon thread via `signal.sigwait()`, which *is* a blocking C call safe to run alongside the Cocoa loop. That thread runs the same `_teardown()` as menu Quit (stop the server if we own it, remove the pidfile) and then `os._exit(0)` — deliberately not trusting the Cocoa loop to unwind cleanly from a signal path. The spawned server subprocess itself needs `SIG_UNBLOCK` in its `preexec_fn`, since the blocked-signal mask is inherited across `fork`+`exec` and would otherwise make uvicorn deaf to its own SIGTERM.

Live-tested end to end: `scribe install-service` → LaunchAgent loads and starts the tray at login → `scribe uninstall-service` → `launchctl unload` delivers SIGTERM → sigwait thread fires → server stopped, pidfile removed, no orphan process left in `ps`.

**`scribe install-service` / `uninstall-service`** (`cli/service_cmd.py`, `core/service.py`): macOS-only for now, same as planned — other platforms get a `_require_macos()` early exit with a friendly message, not a crash. Writes/removes `~/Library/LaunchAgents/com.anyscribe.tray.plist` with `RunAtLoad=true`, `KeepAlive=false`, and `ProgramArguments` pointing at `{sys.executable} -m anyscribecli tray` — the module path rather than the `scribe` binary path, so it survives PATH changes (per the plan's own reasoning). `_launchctl()` is a thin `subprocess.run` wrapper so tests can monkeypatch it instead of touching the real launchd.

Both commands support `--yes`/`-y` (skip confirmation, required in non-TTY/agent contexts) and `--json`/`-j`.

## GitHub Releases automation

`.github/workflows/publish.yml` gained one step at the end of the existing tag-triggered publish job:

```yaml
- name: Create GitHub Release
  env:
    GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
  run: gh release create "${GITHUB_REF_NAME}" --title "${GITHUB_REF_NAME}" --generate-notes
```

This ticks the `v1.0.0` BACKLOG item "GitHub Releases with release notes for each tag" that had sat unchecked since the CI/PyPI automation was built. `--generate-notes` uses GitHub's own commit-comparison notes generator — no custom changelog parsing needed. All 39 historical tags were backfilled with releases using the BACKLOG.md description for that version as the body, so the Releases page has full history instead of starting from v0.13.0 onward.

## Landing page unparked

The landing page had been parked since 2026-04-18 after two design iterations didn't converge (see BACKLOG's Parked section, now rewritten). The v3 direction already on disk — dark warm charcoal, single amber accent, Unbounded/Instrument Serif/Geist type stack — was executed rather than replaced: added a quality-picker section (mirroring the accuracy↔cost feature shipped in v0.9.0) and updated claims throughout to match the current product (seven providers, quality tiers, the tray companion) instead of the earlier draft's stale copy.

`.github/workflows/pages.yml` deploys `landing/` to GitHub Pages on any push touching `landing/**` or the workflow itself, using `actions/upload-pages-artifact` + `actions/deploy-pages`. **Pages hosting is not yet enabled** for the repo — that's a one-time manual step (Settings → Pages → Source: GitHub Actions) pending user approval — so the workflow currently no-ops gracefully rather than failing.

## Test coverage

New: `tests/test_tray.py` (pidfile roundtrip/stale/garbage handling, port-probe, teardown idempotency — all GUI-free, no real pystray/launchctl calls), plus new coverage for the YouTube downloader and the vault writer. Suite: 282 passed (was 242 at v0.12.0).

## Files

- `cli/tray_cmd.py`, `cli/service_cmd.py` (new)
- `core/tray.py`, `core/service.py` (new)
- `cli/main.py` (register `tray`, `install-service`, `uninstall-service`)
- `pyproject.toml` — `[tray]` extra: `pystray`, `Pillow`, `pyobjc-framework-Cocoa` (macOS only)
- `.github/workflows/publish.yml` (`gh release create` step)
- `.github/workflows/pages.yml` (new)
- `landing/index.html` (v3 executed: quality-picker section, claims refresh)
- `tests/test_tray.py` (new), plus new YouTube downloader and vault writer test coverage
