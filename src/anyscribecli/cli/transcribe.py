"""Transcribe command — download and transcribe a URL."""

from __future__ import annotations

import json
import os
import sys
from typing import Optional

import typer
from rich.console import Console

from anyscribecli.config.settings import load_config, load_env

console = Console()
err_console = Console(stderr=True)


def transcribe(
    url: Optional[str] = typer.Argument(None, help="URL or local file path to transcribe."),
    provider: Optional[str] = typer.Option(
        None, "--provider", "-p", help="Override transcription provider."
    ),
    language: Optional[str] = typer.Option(
        None, "--language", "-l", help="Language code (default: auto-detect)."
    ),
    output_json: bool = typer.Option(
        False, "--json", "-j", help="Output result as JSON (for scripting/agents)."
    ),
    keep_media: bool = typer.Option(False, "--keep-media", help="Keep downloaded audio file."),
    diarize: bool = typer.Option(
        False, "--diarize", "-d", help="Enable speaker diarization (multi-speaker transcripts)."
    ),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="Suppress progress output."),
    clipboard: bool = typer.Option(False, "--clipboard", "-c", help="Read URL from clipboard."),
) -> None:
    """[bold blue]Transcribe[/bold blue] a video/audio URL or local file to markdown.

    Accepts a YouTube/Instagram URL or a local audio/video file path.
    Transcribes via API and saves a formatted markdown file to your
    Obsidian workspace.

    [dim]Supported file formats: mp3, mp4, m4a, wav, opus, ogg, flac, webm, aac, wma[/dim]

    [dim]Tip: If the URL contains special characters (like ?), either
    wrap it in quotes or just run `scribe` without a URL
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
        # No input provided — prompt interactively
        console.print("  Paste a URL or local file path (no quotes needed here):")
        url = typer.prompt("  Input")

    if not url:
        err_console.print("[red]Error:[/red] No URL or file path provided.")
        raise typer.Exit(code=1)

    # Validate input — either a URL or a local file path
    url = _validate_input(url)

    load_env()
    settings = load_config()

    # Apply per-run overrides
    if provider:
        settings.provider = provider
    if language:
        settings.language = language
    if keep_media:
        settings.keep_media = True
    if diarize:
        settings.diarize = True
        if settings.output_format == "clean":
            settings.output_format = "diarized"
        # Auto-switch to Deepgram for diarization — it handles large files
        # natively and produces consistent speaker labels without chunking.
        # Only if user didn't explicitly pick a provider.
        if not provider and settings.provider != "deepgram":
            if os.environ.get("DEEPGRAM_API_KEY"):
                if not quiet:
                    err_console.print(
                        f"  [dim]Switching from {settings.provider} → deepgram for diarization[/dim]"
                    )
                settings.provider = "deepgram"

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

        # Post-transcription download prompt (skip for local files)
        if url.startswith("http://") or url.startswith("https://"):
            _maybe_download_after(url, settings, quiet)


def _maybe_download_after(url: str, settings, quiet: bool) -> None:
    """Prompt to download video/audio after transcription, based on config."""
    if settings.prompt_download == "never" or quiet:
        return

    should_download = False
    if settings.prompt_download == "always":
        should_download = True
    elif settings.prompt_download == "ask":
        console.print()
        should_download = typer.confirm("  Download the video/audio file too?", default=False)

    if should_download:
        from pathlib import Path
        from anyscribecli.cli.download import _download_video
        from anyscribecli.config.paths import TMP_DIR
        from anyscribecli.downloaders.registry import detect_platform
        import tempfile
        import shutil

        TMP_DIR.mkdir(parents=True, exist_ok=True)
        tmp_dir = Path(tempfile.mkdtemp(dir=TMP_DIR))
        try:
            platform = detect_platform(url)
            err_console.print("[bold blue]Downloading video...[/bold blue]")
            result = _download_video(url, platform, tmp_dir, quiet=False)
            console.print(f"  [green]Video saved:[/green] {result['file']}")
        except Exception as e:
            err_console.print(f"  [yellow]Download failed:[/yellow] {e}")
        finally:
            if tmp_dir.exists():
                shutil.rmtree(tmp_dir, ignore_errors=True)


def _validate_input(url: str) -> str:
    """Validate input as a URL or local file path."""
    from pathlib import Path

    url = url.strip()

    # Check if it's a local file path
    path = Path(url).expanduser()
    if path.exists() and path.is_file():
        return str(path.resolve())

    # Detect truncated YouTube URLs (zsh ate the ?v= part)
    if "youtube.com/watch" in url and "?" not in url:
        err_console.print(
            "[red]Error:[/red] This URL looks incomplete — the `?v=...` part is missing.\n\n"
            "  This usually happens because your shell (zsh) interprets `?` as a\n"
            "  special character. Wrap the URL in quotes:\n\n"
            '  [bold cyan]scribe "https://www.youtube.com/watch?v=VIDEO_ID"[/bold cyan]\n\n'
            "  Or run [bold]scribe[/bold] without a URL to paste it interactively."
        )
        raise typer.Exit(code=2)

    # Basic URL validation
    if not url.startswith("http://") and not url.startswith("https://"):
        err_console.print(
            f"[red]Error:[/red] '{url}' doesn't look like a URL or file path.\n\n"
            "  Expected a URL or a local audio/video file:\n"
            '  [bold cyan]scribe "https://www.youtube.com/watch?v=VIDEO_ID"[/bold cyan]\n'
            "  [bold cyan]scribe /path/to/audio.mp3[/bold cyan]\n\n"
            "  Supported formats: mp3, mp4, m4a, wav, opus, ogg, flac, webm, aac, wma"
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
                capture_output=True,
                text=True,
                timeout=5,
            )
        text = result.stdout.strip()
        # Basic validation — should look like a URL
        if text and ("youtube.com" in text or "youtu.be" in text or "instagram.com" in text):
            return text
        return text if text.startswith("http") else None
    except Exception:
        return None
