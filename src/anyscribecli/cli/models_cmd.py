"""``scribe model`` — day-to-day Whisper model cache management.

These commands operate on the HuggingFace cache directly. They never install
or uninstall faster-whisper — that's ``scribe local setup/teardown``'s job.
If local transcription isn't set up, pull/rm error cleanly and point at the
right command; list still works (showing everything as not-cached).

All commands support ``--json`` for agent consumption.
"""

from __future__ import annotations

import json
import sys

import typer
from rich.console import Console
from rich.table import Table

from anyscribecli.config.settings import load_config
from anyscribecli.providers.local_models import (
    MODEL_SIZES,
    MODEL_SPECS,
    delete_model,
    faster_whisper_importable,
    is_cached,
    list_cached_models,
    pull_model,
    validate_size,
)

console = Console()
err_console = Console(stderr=True)

models_app = typer.Typer(
    name="model",
    help="List, download, and delete local Whisper models.",
    rich_markup_mode="rich",
    no_args_is_help=True,
)


def _write_json(data) -> None:
    json.dump(data, sys.stdout, indent=2)
    sys.stdout.write("\n")


def _write_json_err(data) -> None:
    json.dump(data, sys.stderr)
    sys.stderr.write("\n")


@models_app.command("list")
def model_list(
    output_json: bool = typer.Option(False, "--json", "-j", help="Output as JSON."),
) -> None:
    """[bold]List[/bold] all Whisper models with cache status and disk usage."""
    settings = load_config()
    models = list_cached_models()

    if output_json:
        payload = [
            {
                "size": m["size"],
                "cached": m["cached"],
                "bytes": m["bytes"],
                "repo": m["repo"],
                "default": m["size"] == settings.local_model,
                "spec": m["spec"],
            }
            for m in models
        ]
        _write_json(payload)
        if not faster_whisper_importable():
            err_console.print("hint: faster-whisper not installed — run `scribe local setup`")
        return

    table = Table(title="Whisper models")
    table.add_column("Size", style="bold")
    table.add_column("Status")
    table.add_column("Disk")
    table.add_column("Download size")
    table.add_column("Quality")

    for m in models:
        cached_mb = int(m["bytes"]) // (1024 * 1024) if m["cached"] else 0
        status = "[green]cached[/green]" if m["cached"] else "[dim]not cached[/dim]"
        marker = " (default)" if m["size"] == settings.local_model else ""
        table.add_row(
            f"{m['size']}{marker}",
            status,
            f"{cached_mb} MB" if m["cached"] else "—",
            f"~{m['spec']['download_mb']} MB",
            m["spec"]["quality"],
        )
    console.print(table)
    if not faster_whisper_importable():
        console.print(
            "\n[yellow]Local transcription is not set up.[/yellow] "
            "Run [bold]scribe local setup --model base[/bold] to install."
        )


@models_app.command("pull")
def model_pull(
    size: str = typer.Argument(..., help="Model size to download."),
    yes: bool = typer.Option(False, "--yes", "-y", help="Reserved; pull is safe, never prompts."),
    output_json: bool = typer.Option(False, "--json", "-j", help="Output as JSON."),
) -> None:
    """[bold]Download[/bold] a Whisper model to the local cache. Idempotent."""
    _ = yes  # accepted for API symmetry with rm
    if size not in MODEL_SIZES:
        err = {"error": f"unknown size '{size}'", "choices": list(MODEL_SIZES)}
        if output_json:
            _write_json_err(err)
        else:
            err_console.print(
                f"[red]Unknown size '{size}'.[/red] Choices: {', '.join(MODEL_SIZES)}."
            )
        raise typer.Exit(code=2)

    if not faster_whisper_importable():
        err = {
            "error": "local transcription not set up",
            "hint": f"run `scribe local setup --model {size}`",
        }
        if output_json:
            _write_json_err(err)
        else:
            err_console.print(
                "[red]faster-whisper not installed.[/red] "
                f"Run [bold]scribe local setup --model {size}[/bold] first."
            )
        raise typer.Exit(code=2)

    try:
        result = pull_model(size)
    except Exception as e:
        err = {"error": str(e)}
        if output_json:
            _write_json_err(err)
        else:
            err_console.print(f"[red]Download failed:[/red] {e}")
        raise typer.Exit(code=1)

    if output_json:
        _write_json(result)
    else:
        mb = int(result.get("bytes", 0)) // (1024 * 1024)
        if result["status"] == "already_present":
            console.print(f"[green]{size} already cached[/green] ({mb} MB).")
        else:
            console.print(f"[green]Downloaded {size}[/green] ({mb} MB).")


@models_app.command("rm")
def model_rm(
    size: str = typer.Argument(..., help="Model size to delete from the cache."),
    yes: bool = typer.Option(
        False, "--yes", "-y", help="Skip confirmation. Required for destructive action."
    ),
    output_json: bool = typer.Option(False, "--json", "-j", help="Output as JSON."),
) -> None:
    """[bold]Remove[/bold] a cached Whisper model from disk."""
    if size not in MODEL_SIZES:
        err = {"error": f"unknown size '{size}'", "choices": list(MODEL_SIZES)}
        if output_json:
            _write_json_err(err)
        else:
            err_console.print(
                f"[red]Unknown size '{size}'.[/red] Choices: {', '.join(MODEL_SIZES)}."
            )
        raise typer.Exit(code=2)

    if not is_cached(size):
        payload = {"status": "not_present", "size": size, "bytes_freed": 0}
        if output_json:
            _write_json(payload)
        else:
            console.print(f"[dim]{size} is not cached — nothing to remove.[/dim]")
        return

    is_tty = sys.stdin.isatty() and sys.stdout.isatty()
    if not yes:
        if not is_tty:
            err = {"error": "refusing to remove without --yes"}
            if output_json:
                _write_json_err(err)
            else:
                err_console.print("[red]Non-interactive run — pass --yes to confirm.[/red]")
            raise typer.Exit(code=2)
        if not typer.confirm(f"Delete cached {size} model?", default=False):
            if output_json:
                _write_json({"status": "cancelled", "size": size})
            else:
                console.print("[yellow]Cancelled.[/yellow]")
            raise typer.Exit(code=0)

    result = delete_model(size)
    if output_json:
        _write_json(result)
    else:
        mb = int(result["bytes_freed"]) // (1024 * 1024)
        console.print(f"[green]Removed {size}[/green] — freed {mb} MB.")


@models_app.command("reinstall")
def model_reinstall(
    size: str = typer.Argument(..., help="Model size to reinstall."),
    yes: bool = typer.Option(
        False,
        "--yes",
        "-y",
        help="Skip confirmation. Required — reinstall deletes the existing weights.",
    ),
    output_json: bool = typer.Option(False, "--json", "-j", help="Output as JSON."),
) -> None:
    """[bold]Reinstall[/bold] a Whisper model — delete + re-download in one step.

    Useful if cached weights look corrupted. If the model wasn't cached, this
    is equivalent to ``scribe model pull`` (no delete needed).
    """
    if size not in MODEL_SIZES:
        err = {"error": f"unknown size '{size}'", "choices": list(MODEL_SIZES)}
        if output_json:
            _write_json_err(err)
        else:
            err_console.print(
                f"[red]Unknown size '{size}'.[/red] Choices: {', '.join(MODEL_SIZES)}."
            )
        raise typer.Exit(code=2)

    if not faster_whisper_importable():
        err = {
            "error": "local transcription not set up",
            "hint": f"run `scribe local setup --model {size}`",
        }
        if output_json:
            _write_json_err(err)
        else:
            err_console.print(
                "[red]faster-whisper not installed.[/red] "
                f"Run [bold]scribe local setup --model {size}[/bold] first."
            )
        raise typer.Exit(code=2)

    is_tty = sys.stdin.isatty() and sys.stdout.isatty()
    if not yes:
        if not is_tty:
            err = {"error": "refusing to reinstall without --yes"}
            if output_json:
                _write_json_err(err)
            else:
                err_console.print("[red]Non-interactive run — pass --yes to confirm.[/red]")
            raise typer.Exit(code=2)
        if not typer.confirm(f"Delete and re-download {size} model?", default=False):
            if output_json:
                _write_json({"status": "cancelled", "size": size})
            else:
                console.print("[yellow]Cancelled.[/yellow]")
            raise typer.Exit(code=0)

    bytes_freed = 0
    if is_cached(size):
        delete_result = delete_model(size)
        bytes_freed = int(delete_result.get("bytes_freed", 0))

    try:
        pull_result = pull_model(size)
    except Exception as e:
        err = {"error": str(e), "bytes_freed": bytes_freed}
        if output_json:
            _write_json_err(err)
        else:
            err_console.print(f"[red]Reinstall failed:[/red] {e}")
        raise typer.Exit(code=1)

    bytes_downloaded = int(pull_result.get("bytes", 0))
    if bytes_freed > 0:
        status = "reinstalled"
    else:
        status = "downloaded_only"

    payload = {
        "status": status,
        "size": size,
        "bytes_freed": bytes_freed,
        "bytes_downloaded": bytes_downloaded,
    }

    if output_json:
        _write_json(payload)
    else:
        freed_mb = bytes_freed // (1024 * 1024)
        dl_mb = bytes_downloaded // (1024 * 1024)
        if status == "reinstalled":
            console.print(
                f"[green]Reinstalled {size}[/green] — freed {freed_mb} MB, downloaded {dl_mb} MB."
            )
        else:
            console.print(
                f"[green]Installed {size}[/green] — downloaded {dl_mb} MB. "
                "(Wasn't previously cached; no delete needed.)"
            )


@models_app.command("info")
def model_info(
    size: str = typer.Argument(..., help="Model size to inspect."),
    output_json: bool = typer.Option(False, "--json", "-j", help="Output as JSON."),
) -> None:
    """[bold]Inspect[/bold] a single Whisper model."""
    try:
        validate_size(size)
    except ValueError as e:
        err = {"error": str(e), "choices": list(MODEL_SIZES)}
        if output_json:
            _write_json_err(err)
        else:
            err_console.print(f"[red]{e}[/red]")
        raise typer.Exit(code=2)

    cached = is_cached(size)
    bytes_on_disk = 0
    for entry in list_cached_models():
        if entry["size"] == size:
            bytes_on_disk = int(entry["bytes"])
            break

    settings = load_config()
    payload = {
        "size": size,
        "cached": cached,
        "bytes": bytes_on_disk,
        "repo": f"Systran/faster-whisper-{size}",
        "default": size == settings.local_model,
        "spec": MODEL_SPECS[size],
    }
    if output_json:
        _write_json(payload)
    else:
        console.print(f"[bold]{size}[/bold]")
        console.print(f"  Repo:     [cyan]{payload['repo']}[/cyan]")
        console.print(f"  Status:   {'cached' if cached else 'not cached'}")
        if cached:
            console.print(f"  Disk:     {bytes_on_disk // (1024 * 1024)} MB")
        console.print(f"  Download: ~{payload['spec']['download_mb']} MB")
        console.print(f"  RAM:      ~{payload['spec']['ram_mb']} MB")
        console.print(f"  Speed:    {payload['spec']['relative_speed']}")
        console.print(f"  Quality:  {payload['spec']['quality']}")
        if payload["default"]:
            console.print("  [green]This is the default model.[/green]")
