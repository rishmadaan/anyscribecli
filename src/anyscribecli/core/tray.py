"""Tray companion core — process supervision, port probe, pidfile.

GUI-free helpers so they stay unit-testable. The pystray loop lives in
``cli/tray_cmd.py`` and imports these. All pystray/Pillow imports are lazy
inside the command, never here or at module import — base install stays
tray-free.
"""

from __future__ import annotations

import os
import socket

from anyscribecli.config.paths import APP_HOME

PIDFILE = APP_HOME / "tray.pid"
GITHUB_RELEASES_URL = "https://github.com/rishmadaan/anyscribecli/releases"
DEFAULT_PORT = 8457


def port_responding(port: int, host: str = "127.0.0.1", timeout: float = 0.5) -> bool:
    """True if something is listening on host:port (a server is up)."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(timeout)
        return s.connect_ex((host, port)) == 0


def _pid_alive(pid: int) -> bool:
    """True if a process with this pid exists (signal 0 = existence probe)."""
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True  # exists, owned by someone else
    return True


def read_pidfile() -> int | None:
    """Return the live pid recorded in the pidfile, or None.

    Stale pidfiles (process gone) are treated as absent — so a crash doesn't
    lock out the next launch.
    """
    try:
        pid = int(PIDFILE.read_text().strip())
    except (FileNotFoundError, ValueError, OSError):
        return None
    return pid if _pid_alive(pid) else None


def write_pidfile() -> None:
    PIDFILE.parent.mkdir(parents=True, exist_ok=True)
    PIDFILE.write_text(str(os.getpid()))


def remove_pidfile() -> None:
    try:
        PIDFILE.unlink()
    except FileNotFoundError:
        pass
