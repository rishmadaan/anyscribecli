---
type: project-note
tags: [windows, cross-platform, yt-dlp, subprocess, PATH, dependency-management]
tldr: "v0.5.4 — Fixed Windows compatibility by invoking yt-dlp as `python -m yt_dlp` instead of bare `yt-dlp`, fixing Python detection via `sys.version_info`, and using `sys.executable -m pip` for installs."
---

# v0.5.4: Windows Compatibility

## What Changed

Three fixes to make ascli work natively on Windows:

1. **yt-dlp invocation**: All subprocess calls changed from `["yt-dlp", ...]` to `[sys.executable, "-m", "yt_dlp", ...]` via a new `get_command(name)` function in `core/deps.py`
2. **Python detection**: `check_dependencies()` was using `shutil.which("python3")` — doesn't exist on Windows (it's `python.exe`). Now uses `sys.version_info` directly since we're already running inside Python
3. **pip install**: `install_dependency()` was running bare `pip install ...`. Now rewrites to `sys.executable -m pip install ...` to target the correct Python environment

## Why

A user installed ascli on Windows via `pip install anyscribecli`. Everything installed fine, but:

- `ascli onboard` couldn't find `yt-dlp` even after pip installed it — because `yt-dlp.exe` was in `C:\Users\<user>\AppData\Roaming\Python\Python314\Scripts` which wasn't on PATH
- `shutil.which("python3")` returned `None` because Windows uses `python` not `python3`
- Even if onboarding was bypassed, runtime `subprocess.run(["yt-dlp", ...])` calls would fail

This is a common Windows pattern — pip installs entry points to a Scripts directory that users rarely add to PATH, especially with `--user` installs.

## Design Decision: `python -m module` over PATH resolution

Considered two approaches:

1. **Scan Scripts directories** (`site.getusersitepackages()/../Scripts`, `sys.prefix/Scripts`) — fragile, many edge cases (conda, virtualenv, Microsoft Store Python, Scoop, Chocolatey)
2. **Use `python -m yt_dlp`** — leverages the same Python interpreter already running; works on every platform, every install method, no PATH needed

Chose option 2. It's the Pythonic way to invoke pip-installed tools. `yt_dlp` supports `python -m yt_dlp` with all the same CLI flags as the binary.

## Implementation Details

- `Dependency` dataclass gets a new `module_name: str | None` field — `"yt_dlp"` for yt-dlp, `None` for system binaries (ffmpeg, ffprobe)
- `get_command(name) -> list[str]` — returns `[sys.executable, "-m", module_name]` for pip-installed tools, `[command]` for system binaries
- `_check_module(module_name)` — checks availability via `subprocess.run([sys.executable, "-m", module, "--version"])`
- `_build_install_cmd(cmd_str)` — rewrites `pip install X` to `sys.executable -m pip install X`
- `_detect_os()` now returns `"windows"` for Windows (was falling through to `"other"`)
- Three call sites updated: `YouTubeDownloader.download()`, `_download_video()`, `ensure_ytdlp_current()`

## What This Doesn't Fix

- **ffmpeg/ffprobe PATH issues on Windows**: These are system binaries, not pip packages. Users still need ffmpeg on PATH (typically installed via `choco install ffmpeg`, `winget install ffmpeg`, or manual download). The onboarding wizard can't auto-install these on Windows.
- **`ascli` command itself not on PATH**: If the user's Python Scripts directory isn't on PATH, they need to add it manually or use the full path. This is a Python/pip limitation, not something we can fix in the tool.

## Chat Summary

1. User shared terminal output from a Windows user who installed ascli via pip
2. Install succeeded but `ascli onboard` showed yt-dlp as "Missing" even after installing it
3. Identified three root causes: bare `yt-dlp` command, `python3` detection, bare `pip install`
4. First approach (scan Scripts directories) was rejected as fragile for different Windows setups
5. Implemented `python -m yt_dlp` approach — works universally across platforms and install methods
6. Updated all three subprocess call sites plus dependency checker and installer

## Links

(no external URLs referenced)
