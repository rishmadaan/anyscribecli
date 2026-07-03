"""Remove command — delete a transcript and resync the master index."""

from __future__ import annotations

import json
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


def rm(
    target: str = typer.Argument(
        ..., help="Transcript path or slug (filename without .md) to delete."
    ),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt."),
    output_json: bool = typer.Option(False, "--json", "-j", help="Output result as JSON."),
) -> None:
    """[bold red]Remove[/bold red] a transcript from the workspace and update the index.

    Accepts a full file path or a slug. Daily logs are kept as history.
    """
    from anyscribecli.vault.index import delete_transcript, find_transcript

    matches = find_transcript(target)
    if not matches:
        _fail(f"No transcript found for '{target}'. Pass a file path or a slug.", output_json)
    if len(matches) > 1:
        listing = "\n  ".join(str(m) for m in matches)
        _fail(f"Ambiguous slug '{target}' — matches:\n  {listing}\nPass a full path.", output_json)

    path = matches[0]
    if not yes:
        typer.confirm(f"Delete {path}?", abort=True)

    try:
        delete_transcript(path)
    except (ValueError, FileNotFoundError) as e:
        _fail(str(e), output_json)

    if output_json:
        json.dump(
            {"success": True, "data": {"deleted": str(path)}, "error": None}, sys.stdout, indent=2
        )
        sys.stdout.write("\n")
    else:
        console.print(f"[green]Deleted:[/green] {path}")
