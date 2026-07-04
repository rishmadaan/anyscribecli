"""`scribe install-service` / `uninstall-service` — autostart at login.

macOS launchd LaunchAgent only for now. Other platforms get a friendly
"not supported yet" error.
"""

from __future__ import annotations

import json
import platform
import sys

import typer
from rich.console import Console

console = Console()
err_console = Console(stderr=True)


def _fail(msg: str, output_json: bool) -> None:
    if output_json:
        json.dump({"success": False, "data": None, "error": msg}, sys.stdout, indent=2)
        sys.stdout.write("\n")
    else:
        err_console.print(f"[red]Error:[/red] {msg}")
    raise typer.Exit(code=1)


def _require_macos(output_json: bool) -> None:
    if platform.system() != "Darwin":
        _fail(
            f"Autostart is only supported on macOS for now (you're on {platform.system()}).",
            output_json,
        )


def install_service(
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt."),
    output_json: bool = typer.Option(False, "--json", "-j", help="Output result as JSON."),
) -> None:
    """[bold]Register[/bold] the tray companion to start automatically at login (macOS)."""
    _require_macos(output_json)
    from anyscribecli.core.service import install_service as do_install, plist_path

    if not yes and not output_json:
        typer.confirm(f"Install LaunchAgent at {plist_path()}?", abort=True)

    path = do_install()
    if output_json:
        json.dump(
            {"success": True, "data": {"plist": str(path)}, "error": None}, sys.stdout, indent=2
        )
        sys.stdout.write("\n")
    else:
        console.print(f"[green]Installed:[/green] {path}")
        console.print("[dim]The tray will start at your next login.[/dim]")


def uninstall_service(
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt."),
    output_json: bool = typer.Option(False, "--json", "-j", help="Output result as JSON."),
) -> None:
    """[bold red]Remove[/bold red] the tray companion's login autostart (macOS)."""
    _require_macos(output_json)
    from anyscribecli.core.service import plist_path, uninstall_service as do_uninstall

    if not yes and not output_json:
        typer.confirm(f"Remove LaunchAgent at {plist_path()}?", abort=True)

    existed = do_uninstall()
    if output_json:
        json.dump(
            {"success": True, "data": {"removed": existed}, "error": None}, sys.stdout, indent=2
        )
        sys.stdout.write("\n")
    elif existed:
        console.print("[green]Removed[/green] the tray LaunchAgent.")
    else:
        console.print("[dim]No tray LaunchAgent was installed.[/dim]")
