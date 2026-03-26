"""Transcribe command — download and transcribe a URL."""

from __future__ import annotations

import json
import sys
from typing import Optional

import typer
from rich.console import Console

from anyscribecli.config.settings import load_config, load_env

console = Console()
err_console = Console(stderr=True)


def transcribe(
    url: str = typer.Argument(..., help="YouTube or Instagram URL to transcribe."),
    provider: Optional[str] = typer.Option(
        None, "--provider", "-p", help="Override transcription provider."
    ),
    language: Optional[str] = typer.Option(
        None, "--language", "-l", help="Language code (default: auto-detect)."
    ),
    output_json: bool = typer.Option(
        False, "--json", "-j", help="Output result as JSON (for scripting/agents)."
    ),
    keep_media: bool = typer.Option(
        False, "--keep-media", help="Keep downloaded audio file."
    ),
    quiet: bool = typer.Option(
        False, "--quiet", "-q", help="Suppress progress output."
    ),
) -> None:
    """[bold blue]Transcribe[/bold blue] a video/audio URL to markdown.

    Downloads the audio, transcribes via API, and saves a formatted
    markdown file to your Obsidian workspace.
    """
    from anyscribecli.core.orchestrator import process

    load_env()
    settings = load_config()

    # Apply per-run overrides
    if provider:
        settings.provider = provider
    if language:
        settings.language = language
    if keep_media:
        settings.keep_media = True

    try:
        result = process(url, settings, quiet=quiet)
    except Exception as e:
        if output_json:
            json.dump({"success": False, "error": str(e)}, sys.stdout, indent=2)
            sys.stdout.write("\n")
        else:
            err_console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1)

    if output_json:
        json.dump(
            {
                "success": True,
                "file": str(result.file_path),
                "title": result.title,
                "platform": result.platform,
                "duration": result.duration,
                "language": result.language,
                "word_count": result.word_count,
                "provider": result.provider,
            },
            sys.stdout,
            indent=2,
        )
        sys.stdout.write("\n")
    else:
        console.print(f"\n[green]Transcription saved:[/green] {result.file_path}")
        console.print(f"  Title:    {result.title}")
        console.print(f"  Duration: {result.duration}")
        console.print(f"  Language: {result.language}")
        console.print(f"  Words:    {result.word_count}")
