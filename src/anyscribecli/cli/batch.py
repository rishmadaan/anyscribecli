"""Batch processing command — transcribe multiple URLs from a file."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, MofNCompleteColumn
from rich.table import Table

from anyscribecli.config.settings import load_config, load_env

console = Console()
err_console = Console(stderr=True)


def batch(
    file: Path = typer.Argument(..., help="File containing URLs or file paths (one per line)."),
    provider: str | None = typer.Option(None, "--provider", "-p", help="Override provider."),
    language: str | None = typer.Option(None, "--language", "-l", help="Override language."),
    output_json: bool = typer.Option(False, "--json", "-j", help="Output results as JSON."),
    keep_media: bool = typer.Option(False, "--keep-media", help="Keep audio files."),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="Suppress progress."),
    stop_on_error: bool = typer.Option(False, "--stop-on-error", help="Stop at first failure."),
) -> None:
    """[bold magenta]Batch transcribe[/bold magenta] URLs or local files from a list.

    Reads a file with one URL or file path per line (blank lines and #comments
    are skipped). Processes each entry sequentially and reports results.
    """
    if not file.exists():
        err_console.print(f"[red]File not found:[/red] {file}")
        raise typer.Exit(code=1)

    # Parse URLs from file
    urls: list[str] = []
    for line in file.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            urls.append(line)

    if not urls:
        err_console.print("[yellow]No URLs or file paths found in file.[/yellow]")
        raise typer.Exit()

    load_env()
    settings = load_config()
    if provider:
        settings.provider = provider
    if language:
        settings.language = language
    if keep_media:
        settings.keep_media = True

    results: list[dict] = []
    succeeded = 0
    failed = 0

    if quiet or output_json:
        # No progress display
        for url in urls:
            succeeded, failed = _process_url(url, settings, results, succeeded, failed, quiet=True)
            if failed and stop_on_error:
                break
    else:
        # Rich progress bar
        with Progress(
            SpinnerColumn(),
            TextColumn("[bold]{task.description}"),
            BarColumn(),
            MofNCompleteColumn(),
            console=err_console,
        ) as progress:
            task = progress.add_task("Transcribing", total=len(urls))

            for url in urls:
                progress.update(task, description=f"[bold]{_shorten_url(url)}")
                succeeded, failed = _process_url(
                    url, settings, results, succeeded, failed, quiet=True
                )
                progress.advance(task)
                if failed and stop_on_error:
                    err_console.print("[red]Stopping on error (--stop-on-error).[/red]")
                    break

    # Summary
    if output_json:
        json.dump(
            {
                "total": len(urls),
                "succeeded": succeeded,
                "failed": failed,
                "results": results,
            },
            sys.stdout,
            indent=2,
        )
        sys.stdout.write("\n")
    else:
        console.print(
            f"\n[bold]Batch complete:[/bold] {succeeded} succeeded, {failed} failed, {len(urls)} total"
        )

        if results:
            table = Table(title="Results")
            table.add_column("#", style="dim")
            table.add_column("Status")
            table.add_column("Title / Error")

            for i, r in enumerate(results, 1):
                if r["success"]:
                    table.add_row(str(i), "[green]OK[/green]", r["title"])
                else:
                    table.add_row(str(i), "[red]FAIL[/red]", r["error"][:80])

            console.print(table)

    if failed > 0:
        raise typer.Exit(code=1)


def _shorten_url(url: str, max_len: int = 50) -> str:
    """Shorten a URL for display in progress bar."""
    url = url.replace("https://", "").replace("http://", "").replace("www.", "")
    if len(url) > max_len:
        return url[: max_len - 3] + "..."
    return url


def _process_url(
    url: str,
    settings,
    results: list[dict],
    succeeded: int,
    failed: int,
    quiet: bool,
) -> tuple[int, int]:
    """Process a single URL, append to results. Returns (succeeded, failed)."""
    from anyscribecli.core.orchestrator import process

    try:
        result = process(url, settings, quiet=quiet)
        succeeded += 1
        results.append(
            {
                "success": True,
                "url": url,
                "file": str(result.file_path),
                "title": result.title,
                "platform": result.platform,
                "duration": result.duration,
                "language": result.language,
                "word_count": result.word_count,
            }
        )
    except Exception as e:
        failed += 1
        results.append(
            {
                "success": False,
                "url": url,
                "error": str(e),
            }
        )
    return succeeded, failed
