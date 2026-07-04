"""Autostart service (macOS launchd LaunchAgent).

macOS only for now. Registers `scribe tray` as a per-user LaunchAgent so the
tray companion starts at login.

Uses ``{python} -m anyscribecli tray`` rather than the ``scribe`` binary path:
the module path is stable within a given Python install, so it survives PATH
changes that would leave a hardcoded binary path dangling (per the plan).
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

LABEL = "com.anyscribe.tray"


def launch_agents_dir() -> Path:
    return Path.home() / "Library" / "LaunchAgents"


def plist_path() -> Path:
    return launch_agents_dir() / f"{LABEL}.plist"


def render_plist(python: str | None = None, label: str = LABEL) -> str:
    """Return the launchd plist XML for the tray LaunchAgent."""
    python = python or sys.executable
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>{label}</string>
    <key>ProgramArguments</key>
    <array>
        <string>{python}</string>
        <string>-m</string>
        <string>anyscribecli</string>
        <string>tray</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <false/>
</dict>
</plist>
"""


def _launchctl(*args: str) -> None:
    """Run launchctl. Wrapped so tests can monkeypatch it (no real load)."""
    subprocess.run(["launchctl", *args], check=False)


def install_service() -> Path:
    """Write the LaunchAgent plist and load it. Returns the plist path."""
    path = plist_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_plist())
    _launchctl("load", str(path))
    return path


def uninstall_service() -> bool:
    """Unload and remove the LaunchAgent plist. Returns True if it existed."""
    path = plist_path()
    existed = path.exists()
    if existed:
        _launchctl("unload", str(path))
        path.unlink()
    return existed
