"""ascli — main CLI entry point."""

from __future__ import annotations

from typing import Optional

import typer
from rich.console import Console

from anyscribecli import __version__

app = typer.Typer(
    name="ascli",
    help="Download, transcribe, and convert video/audio to structured markdown.",
    rich_markup_mode="rich",
    no_args_is_help=True,
)

console = Console()
err_console = Console(stderr=True)


def version_callback(value: bool) -> None:
    if value:
        console.print(f"ascli v{__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: Optional[bool] = typer.Option(
        None,
        "--version",
        "-v",
        help="Show version and exit.",
        callback=version_callback,
        is_eager=True,
    ),
) -> None:
    """[bold]ascli[/bold] — download, transcribe, and convert video/audio to structured markdown."""


# Register commands
from anyscribecli.cli.onboard import onboard  # noqa: E402
from anyscribecli.cli.transcribe import transcribe  # noqa: E402

app.command()(onboard)
app.command()(transcribe)
