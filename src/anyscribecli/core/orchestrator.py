"""Core orchestrator — ties download, transcribe, and vault write together."""

from __future__ import annotations

import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path

from rich.console import Console

from anyscribecli.config.paths import TMP_DIR
from anyscribecli.config.settings import Settings
from anyscribecli.downloaders.registry import get_downloader
from anyscribecli.providers import get_provider
from anyscribecli.vault.writer import write_transcript, format_duration
from anyscribecli.vault.index import update_indexes

err_console = Console(stderr=True)


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


def process(url: str, settings: Settings, quiet: bool = False) -> ProcessResult:
    """Full pipeline: download -> transcribe -> write -> index.

    Args:
        url: Video/audio URL to process.
        settings: App settings.
        quiet: Suppress progress output.

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

    TMP_DIR.mkdir(parents=True, exist_ok=True)
    tmp_dir = Path(tempfile.mkdtemp(dir=TMP_DIR))

    try:
        # Step 1: Download / prepare
        is_local = not url.startswith("http://") and not url.startswith("https://")
        if not quiet:
            label = "Preparing audio" if is_local else "Downloading audio"
            err_console.print(f"[bold blue]{label}...[/bold blue]")

        downloader = get_downloader(url)
        download = downloader.download(url, tmp_dir)

        if not quiet:
            status = "Ready" if is_local else "Downloaded"
            err_console.print(f"  [green]{status}:[/green] {download.title}")

        # Step 2: Transcribe
        if not quiet:
            err_console.print(f"[bold blue]Transcribing with {settings.provider}...[/bold blue]")

        provider = get_provider(settings.provider)
        transcript = provider.transcribe(
            download.audio_path, settings.language, diarize=settings.diarize
        )

        if not quiet:
            err_console.print(
                f"  [green]Done:[/green] {transcript.word_count} words, "
                f"language={transcript.language}"
            )

        # Step 3: Write transcript to vault
        if not quiet:
            err_console.print("[bold blue]Writing to vault...[/bold blue]")

        file_path = write_transcript(download, transcript, settings)

        # Step 4: Update indexes
        update_indexes(file_path, download)

        if not quiet:
            err_console.print(f"  [green]Saved:[/green] {file_path}")

        return ProcessResult(
            file_path=file_path,
            title=download.title,
            platform=download.platform,
            duration=format_duration(download.duration or transcript.duration),
            language=transcript.language,
            word_count=transcript.word_count,
            provider=settings.provider,
        )

    finally:
        # Cleanup temp files (unless keep_media, audio was already copied)
        if tmp_dir.exists():
            shutil.rmtree(tmp_dir, ignore_errors=True)
