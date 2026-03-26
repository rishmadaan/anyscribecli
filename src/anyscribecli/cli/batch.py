"""Batch processing command — transcribe multiple URLs from a file."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from anyscribecli.config.settings import load_config, load_env

console = Console()
err_console = Console(stderr=True)


def batch(
    file: Path = typer.Argument(..., help="File containing URLs (one per line)."),
    provider: str | None = typer.Option(None, "--provider", "-p", help="Override provider."),
    language: str | None = typer.Option(None, "--language", "-l", help="Override language."),
    output_json: bool = typer.Option(False, "--json", "-j", help="Output results as JSON."),
    keep_media: bool = typer.Option(False, "--keep-media", help="Keep audio files."),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="Suppress progress."),
    stop_on_error: bool = typer.Option(False, "--stop-on-error", help="Stop at first failure."),
) -> None:
    """[bold magenta]Batch transcribe[/bold magenta] URLs from a file.

    Reads a file with one URL per line (blank lines and #comments are skipped).
    Processes each URL sequentially and reports results.
    """
    from anyscribecli.core.orchestrator import process

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
        err_console.print("[yellow]No URLs found in file.[/yellow]")
        raise typer.Exit()

    load_env()
    settings = load_config()
    if provider:
        settings.provider = provider
    if language:
        settings.language = language
    if keep_media:
        settings.keep_media = True

    if not quiet:
        console.print(f"[bold]Batch processing {len(urls)} URL(s)...[/bold]\n")

    results: list[dict] = []
    succeeded = 0
    failed = 0

    for i, url in enumerate(urls, 1):
        if not quiet:
            console.print(f"[bold][{i}/{len(urls)}][/bold] {url}")

        try:
            result = process(url, settings, quiet=quiet)
            succeeded += 1
            results.append({
                "success": True,
                "url": url,
                "file": str(result.file_path),
                "title": result.title,
                "platform": result.platform,
                "duration": result.duration,
                "language": result.language,
                "word_count": result.word_count,
            })
            if not quiet:
                console.print(f"  [green]Done:[/green] {result.title}\n")
        except Exception as e:
            failed += 1
            results.append({
                "success": False,
                "url": url,
                "error": str(e),
            })
            if not quiet:
                err_console.print(f"  [red]Failed:[/red] {e}\n")
            if stop_on_error:
                err_console.print("[red]Stopping on error (--stop-on-error).[/red]")
                break

    # Summary
    if output_json:
        json.dump({
            "total": len(urls),
            "succeeded": succeeded,
            "failed": failed,
            "results": results,
        }, sys.stdout, indent=2)
        sys.stdout.write("\n")
    else:
        console.print(f"\n[bold]Batch complete:[/bold] {succeeded} succeeded, {failed} failed, {len(urls)} total")

        if results:
            table = Table(title="Results")
            table.add_column("#", style="dim")
            table.add_column("Status")
            table.add_column("Title / Error")

            for i, r in enumerate(results, 1):
                if r["success"]:
                    table.add_row(str(i), "[green]OK[/green]", r["title"])
                else:
                    table.add_row(str(i), "[red]FAIL[/red]", r["error"][:60])

            console.print(table)

    if failed > 0:
        raise typer.Exit(code=1)
