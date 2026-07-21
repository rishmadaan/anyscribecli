"""`scribe tray` — menu-bar/tray companion that supervises the web server.

All pystray/Pillow imports are lazy (inside functions) so the base install
stays tray-free and `scribe tray --help` works without the `[tray]` extra.
"""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import threading
import time
import webbrowser

import typer
from rich.console import Console

from anyscribe.core import tray as core

console = Console()
err_console = Console(stderr=True)

_MISSING_EXTRA = "The tray companion needs extra packages.\nRun: pip install -U 'anyscribe[tray]'"

_SIGNALS = {signal.SIGTERM, signal.SIGINT}


def _make_image():
    """Load the bundled waveform glyph (black + alpha, template-ready).

    Falls back to a drawn circle if the asset is missing (e.g. odd
    packaging), so the tray never fails to start over an icon.
    """
    import io
    from importlib.resources import files

    from PIL import Image, ImageDraw

    try:
        data = files("anyscribe").joinpath("assets/tray-icon.png").read_bytes()
        return Image.open(io.BytesIO(data)).convert("RGBA")
    except Exception:
        size = 64
        img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        d.ellipse((10, 10, size - 10, size - 10), fill=(0, 0, 0, 255))
        return img


def _mark_template(icon) -> None:
    """pystray setup callback: show the icon, then mark it as a macOS
    template image so it adapts to light/dark menu bars.

    Passing a custom setup to ``icon.run()`` REPLACES pystray's default,
    whose whole job is ``icon.visible = True`` — so we must set it here or
    the tray never appears. Visibility also creates the native image, which
    is why setTemplate_ comes second. The template call reaches into
    pystray's darwin backend; harmless no-op elsewhere."""
    icon.visible = True
    try:
        icon._icon_image.setTemplate_(True)
    except Exception:
        pass


def _shutdown_server(proc, port: int) -> None:
    """Stop a server WE spawned: POST /shutdown → wait 5s → SIGTERM → wait 3s → SIGKILL.

    ``proc is None`` means we attached to a pre-existing server we don't own —
    leave it alone.
    """
    if proc is None:
        return
    try:
        import httpx

        httpx.post(f"http://127.0.0.1:{port}/api/shutdown", timeout=2.0)
    except Exception:
        pass
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()


def _teardown(state: dict, port: int) -> None:
    """Single teardown for menu Quit, signals, and exceptions. Idempotent."""
    _shutdown_server(state.pop("proc", None), port)
    core.remove_pidfile()


def tray(
    port: int = typer.Option(core.DEFAULT_PORT, "--port", "-p", help="Port to listen on."),
) -> None:
    r"""Run the [bold]menu-bar tray[/bold] companion (supervises the web server).

    Requires the optional extra: [bold]pip install 'anyscribe\[tray]'[/bold]
    """
    try:
        import pystray  # noqa: F401
        from PIL import Image  # noqa: F401
    except ImportError:
        err_console.print(_MISSING_EXTRA, style="red", markup=False)
        raise typer.Exit(code=1)

    # Already-running instance? Bail instead of colliding on the port.
    if core.read_pidfile() is not None:
        err_console.print("[yellow]A scribe tray is already running.[/yellow]")
        raise typer.Exit(code=1)

    _run_tray(port)


def _run_tray(port: int) -> None:
    import pystray

    core.write_pidfile()
    state: dict = {"proc": None}

    def _server_up() -> bool:
        return core.port_responding(port)

    def _start_server() -> None:
        """Spawn the uvicorn server as a subprocess unless one is already up."""
        if _server_up():
            return  # attach to an externally-started server (we don't own it)
        state["proc"] = subprocess.Popen(
            [sys.executable, "-m", "anyscribe", "ui", "--port", str(port), "--no-open"],
            # The tray blocks SIGTERM/SIGINT (see _watch_signals) and the mask
            # is inherited across exec — unblock in the child so uvicorn still
            # responds to signals.
            preexec_fn=lambda: signal.pthread_sigmask(signal.SIG_UNBLOCK, _SIGNALS),
        )

    def on_open(icon, item) -> None:  # noqa: ANN001
        webbrowser.open(f"http://127.0.0.1:{port}")

    def on_restart(icon, item) -> None:  # noqa: ANN001
        _shutdown_server(state.pop("proc", None), port)
        time.sleep(0.5)
        _start_server()

    def on_updates(icon, item) -> None:  # noqa: ANN001
        webbrowser.open(core.GITHUB_RELEASES_URL)

    def status_text(item) -> str:  # noqa: ANN001
        return f"Status: {'running' if _server_up() else 'stopped'}"

    def on_quit(icon, item) -> None:  # noqa: ANN001
        _teardown(state, port)
        icon.stop()

    # SIGTERM (launchctl unload / logout) and SIGINT must run the same teardown
    # as menu Quit. A plain signal.signal handler never fires here: the Cocoa
    # event loop blocks in ObjC, so Python bytecode (where handlers run) may
    # never execute. Block the signals and catch them in a sigwait thread.
    signal.pthread_sigmask(signal.SIG_BLOCK, _SIGNALS)

    def _watch_signals() -> None:
        signal.sigwait(_SIGNALS)
        _teardown(state, port)
        os._exit(0)  # Cocoa loop can't be trusted to unwind from a signal

    threading.Thread(target=_watch_signals, daemon=True).start()

    menu = pystray.Menu(
        pystray.MenuItem("Open UI", on_open, default=True),
        pystray.MenuItem(status_text, None, enabled=False),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Restart server", on_restart),
        pystray.MenuItem("Check for updates…", on_updates),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Quit", on_quit),
    )

    icon = pystray.Icon("anyscribe", _make_image(), "anyscribe", menu)
    _start_server()
    try:
        # setup runs once the backend has built the native image.
        icon.run(setup=_mark_template)  # blocks until on_quit -> icon.stop()
    finally:
        _teardown(state, port)  # any exit path stops the server we own
