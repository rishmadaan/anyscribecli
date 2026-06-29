"""Core orchestrator — ties download, transcribe, and vault write together."""

from __future__ import annotations

import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from rich.console import Console

from anyscribecli.config.paths import RECOVERY_DIR, TMP_DIR
from anyscribecli.config.settings import Settings
from anyscribecli.downloaders.registry import get_downloader
from anyscribecli.providers import get_provider
from anyscribecli.vault.writer import write_transcript, format_duration
from anyscribecli.vault.index import update_indexes

err_console = Console(stderr=True)

# Type alias for progress callbacks (used by web UI)
OnProgress = Callable[..., None] | None


@dataclass
class ProcessResult:
    """Result returned to the CLI after processing."""

    file_path: Path
    title: str
    platform: str
    duration: str
    language: str
    word_count: int
    provider: str


def process(
    url: str,
    settings: Settings,
    quiet: bool = False,
    on_progress: OnProgress = None,
) -> ProcessResult:
    """Full pipeline: download -> transcribe -> write -> index.

    Args:
        url: Video/audio URL to process.
        settings: App settings.
        quiet: Suppress progress output.
        on_progress: Optional callback for progress events (used by web UI).
            Signature: (step, status, message, **kwargs) -> None

    Returns:
        ProcessResult with metadata about the written file.
    """
    # Auto-migrate legacy paths if needed
    from anyscribecli.core.migrate import (
        maybe_migrate_workspace,
        maybe_migrate_media_to_downloads,
        maybe_flatten_date_folders,
    )

    migrated = maybe_migrate_workspace()
    if migrated and not quiet:
        err_console.print(f"  [yellow]Workspace moved to {migrated}[/yellow]")
    maybe_migrate_media_to_downloads()

    flattened = maybe_flatten_date_folders()
    if flattened and not quiet:
        err_console.print(f"  [yellow]Flattened {flattened} files out of date folders[/yellow]")
    if flattened:
        from anyscribecli.vault.index import rebuild_master_index

        rebuild_master_index()

    # Pre-flight: validate prerequisites before doing any work
    from anyscribecli.core.preflight import preflight_check

    preflight_check(settings, url)

    TMP_DIR.mkdir(parents=True, exist_ok=True)
    tmp_dir = Path(tempfile.mkdtemp(dir=TMP_DIR))
    download_succeeded = False

    try:
        # Step 1: Download / prepare
        is_local = not url.startswith("http://") and not url.startswith("https://")
        label = "Preparing audio" if is_local else "Downloading audio"
        if not quiet:
            err_console.print(f"[bold blue]{label}...[/bold blue]")
        if on_progress:
            on_progress("download", "started", f"{label}...")

        downloader = get_downloader(url)
        download = downloader.download(url, tmp_dir)

        status = "Ready" if is_local else "Downloaded"
        if not quiet:
            err_console.print(f"  [green]{status}:[/green] {download.title}")
        if on_progress:
            on_progress("download", "completed", f"{status}: {download.title}")
        download_succeeded = True

        # Step 2: Transcribe
        if not quiet:
            err_console.print(f"[bold blue]Transcribing with {settings.provider}...[/bold blue]")
        if on_progress:
            on_progress("transcribe", "started", f"Transcribing with {settings.provider}...")

        provider = get_provider(settings.provider)
        transcript = provider.transcribe(
            download.audio_path, settings.language, diarize=settings.diarize
        )

        if not quiet:
            err_console.print(
                f"  [green]Done:[/green] {transcript.word_count} words, "
                f"language={transcript.language}"
            )
        if on_progress:
            on_progress(
                "transcribe",
                "completed",
                f"Done: {transcript.word_count} words, language={transcript.language}",
            )

        # Step 3: Write transcript to vault
        if not quiet:
            err_console.print("[bold blue]Writing to vault...[/bold blue]")
        if on_progress:
            on_progress("write", "started", "Writing to vault...")

        file_path = write_transcript(download, transcript, settings)

        if on_progress:
            on_progress("write", "completed", f"Saved: {file_path}")

        # Step 4: Update indexes
        if on_progress:
            on_progress("index", "started", "Updating indexes...")

        update_indexes(file_path, download)

        if not quiet:
            err_console.print(f"  [green]Saved:[/green] {file_path}")
        if on_progress:
            on_progress("index", "completed", "Indexes updated")

        return ProcessResult(
            file_path=file_path,
            title=download.title,
            platform=download.platform,
            duration=format_duration(download.duration or transcript.duration),
            language=transcript.language,
            word_count=transcript.word_count,
            provider=settings.provider,
        )

    except Exception:
        # Preserve downloaded audio in recovery dir so the user doesn't
        # have to re-download on retry.
        if download_succeeded and tmp_dir.exists():
            try:
                recovery = RECOVERY_DIR / tmp_dir.name
                recovery.mkdir(parents=True, exist_ok=True)
                for f in tmp_dir.glob("*.mp3"):
                    shutil.copy2(f, recovery / f.name)
                if not quiet:
                    err_console.print(f"  [yellow]Audio saved for recovery:[/yellow] {recovery}")
            except Exception:
                pass  # Don't mask the original error
        raise
    finally:
        # Cleanup temp files (unless keep_media, audio was already copied)
        if tmp_dir.exists():
            shutil.rmtree(tmp_dir, ignore_errors=True)
