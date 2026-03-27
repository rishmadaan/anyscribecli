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
    url: Optional[str] = typer.Argument(None, help="YouTube or Instagram URL to transcribe."),
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
    clipboard: bool = typer.Option(
        False, "--clipboard", "-c", help="Read URL from clipboard."
    ),
) -> None:
    """[bold blue]Transcribe[/bold blue] a video/audio URL to markdown.

    Downloads the audio, transcribes via API, and saves a formatted
    markdown file to your Obsidian workspace.

    [dim]Tip: If the URL contains special characters (like ?), either
    wrap it in quotes or just run `ascli transcribe` without a URL
    and you'll be prompted to paste it.[/dim]
    """
    from anyscribecli.core.orchestrator import process

    # Resolve the URL from argument, clipboard, or interactive prompt
    if clipboard:
        url = _read_clipboard()
        if not url:
            err_console.print("[red]Error:[/red] No URL found in clipboard.")
            raise typer.Exit(code=1)
        if not quiet:
            err_console.print(f"[dim]URL from clipboard:[/dim] {url}")

    if not url:
        # No URL provided — prompt interactively
        console.print("  Paste a YouTube or Instagram URL (no quotes needed here):")
        url = typer.prompt("  URL")

    if not url:
        err_console.print("[red]Error:[/red] No URL provided.")
        raise typer.Exit(code=1)

    # Detect URLs mangled by zsh glob expansion (? stripped)
    url = _validate_url(url)

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


def _validate_url(url: str) -> str:
    """Validate and clean the URL. Detect common shell mangling issues."""
    url = url.strip()

    # Detect truncated YouTube URLs (zsh ate the ?v= part)
    if "youtube.com/watch" in url and "?" not in url:
        err_console.print(
            "[red]Error:[/red] This URL looks incomplete — the `?v=...` part is missing.\n\n"
            "  This usually happens because your shell (zsh) interprets `?` as a\n"
            "  special character. Wrap the URL in quotes:\n\n"
            '  [bold cyan]ascli transcribe "https://www.youtube.com/watch?v=VIDEO_ID"[/bold cyan]\n\n'
            "  Or run [bold]ascli transcribe[/bold] without a URL to paste it interactively."
        )
        raise typer.Exit(code=2)

    # Basic URL validation
    if not url.startswith("http://") and not url.startswith("https://"):
        err_console.print(
            f"[red]Error:[/red] '{url}' doesn't look like a URL.\n\n"
            "  Expected a YouTube or Instagram URL like:\n"
            '  [bold cyan]ascli transcribe "https://www.youtube.com/watch?v=VIDEO_ID"[/bold cyan]\n\n'
            "  Make sure to wrap the URL in quotes."
        )
        raise typer.Exit(code=2)

    return url


def _read_clipboard() -> str | None:
    """Read URL from system clipboard. Returns None if unavailable."""
    try:
        import subprocess
        import platform

        if platform.system() == "Darwin":
            result = subprocess.run(["pbpaste"], capture_output=True, text=True, timeout=5)
        else:
            result = subprocess.run(
                ["xclip", "-selection", "clipboard", "-o"],
                capture_output=True, text=True, timeout=5,
            )
        text = result.stdout.strip()
        # Basic validation — should look like a URL
        if text and ("youtube.com" in text or "youtu.be" in text or "instagram.com" in text):
            return text
        return text if text.startswith("http") else None
    except Exception:
        return None
