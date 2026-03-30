"""Write transcript markdown files with frontmatter."""

from __future__ import annotations

import re
import shutil
from datetime import date
from pathlib import Path

from anyscribecli.config.paths import get_workspace_dir, AUDIO_DIR
from anyscribecli.config.settings import Settings
from anyscribecli.downloaders.base import DownloadResult
from anyscribecli.providers.base import TranscriptResult


def slugify(text: str, max_length: int = 60) -> str:
    """Convert text to a URL/filename-safe slug."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    text = re.sub(r"-+", "-", text)
    text = text.strip("-")
    return text[:max_length]


def format_duration(seconds: float | None) -> str:
    """Format seconds as mm:ss or hh:mm:ss."""
    if seconds is None:
        return "unknown"
    total = int(seconds)
    h, remainder = divmod(total, 3600)
    m, s = divmod(remainder, 60)
    if h > 0:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


def estimate_reading_time(word_count: int) -> str:
    """Estimate reading time at 200 wpm."""
    minutes = max(1, round(word_count / 200))
    return f"{minutes} min"


def write_transcript(
    download: DownloadResult,
    transcript: TranscriptResult,
    settings: Settings,
    workspace: Path | None = None,
) -> Path:
    """Write a transcript to the vault as a markdown file.

    Returns the path to the written file.
    """
    ws = workspace or get_workspace_dir()
    today = date.today().isoformat()
    slug = slugify(download.title)
    if not slug:
        slug = "untitled"

    # Determine output path: sources/<platform>/YYYY-MM-DD/<slug>.md
    out_dir = ws / "sources" / download.platform / today
    out_dir.mkdir(parents=True, exist_ok=True)

    # Handle slug collisions
    out_path = out_dir / f"{slug}.md"
    counter = 2
    while out_path.exists():
        out_path = out_dir / f"{slug}-{counter}.md"
        counter += 1

    # Build frontmatter
    duration_str = format_duration(download.duration or transcript.duration)
    word_count = transcript.word_count
    reading_time = estimate_reading_time(word_count)

    frontmatter = (
        f"---\n"
        f"source: {download.original_url}\n"
        f"platform: {download.platform}\n"
        f'title: "{download.title}"\n'
        f'duration: "{duration_str}"\n'
        f"language: {transcript.language}\n"
        f"provider: {settings.provider}\n"
        f"date_processed: {today}\n"
        f"word_count: {word_count}\n"
        f'reading_time: "{reading_time}"\n'
        f"tags:\n"
        f"  - transcript\n"
        f"  - {download.platform}\n"
        f'tldr: "{download.title}"\n'
        f"---\n"
    )

    # Build body
    body_parts = [
        f"# {download.title}\n",
    ]

    if download.channel:
        body_parts.append(f"**Channel:** {download.channel}\n")

    if download.platform == "local":
        body_parts.append(f"**Source:** local file (`{download.original_url}`)\n")
    else:
        body_parts.append(f"**Source:** [{download.platform}]({download.original_url})\n")
    body_parts.append(
        f"**Duration:** {duration_str} | **Words:** {word_count} | **Reading time:** {reading_time}\n"
    )
    body_parts.append("\n---\n")

    # Transcript body — format depends on output_format setting
    if settings.output_format == "timestamped" and transcript.segments:
        body_parts.append("\n## Transcript\n")
        for seg in transcript.segments:
            ts = format_duration(seg.start)
            body_parts.append(f"\n**[{ts}]** {seg.text}\n")
    else:
        body_parts.append(f"\n## Transcript\n\n{transcript.text}\n")

    content = frontmatter + "\n" + "\n".join(body_parts)
    out_path.write_text(content)

    # Handle media file retention
    if download.platform == "local":
        _handle_local_file_media(download, settings, slug, today)
    elif settings.keep_media and download.audio_path.exists():
        # URL downloads: save converted audio to media dir
        audio_dir = AUDIO_DIR / download.platform / today
        audio_dir.mkdir(parents=True, exist_ok=True)
        dest = audio_dir / f"{slug}{download.audio_path.suffix}"
        shutil.copy2(download.audio_path, dest)

    return out_path


def _handle_local_file_media(
    download: DownloadResult,
    settings: Settings,
    slug: str,
    today: str,
) -> None:
    """Handle the original source file for local file transcriptions."""
    from rich.console import Console

    action = settings.local_file_media
    original = Path(download.original_url)

    if action == "skip":
        return

    if action == "ask":
        import typer

        err_console = Console(stderr=True)
        err_console.print(f"\n  Original file: [cyan]{original}[/cyan]")
        choice = (
            typer.prompt(
                "  What to do with the original file? (skip/copy/move)",
                default="skip",
            )
            .strip()
            .lower()
        )
        if choice not in ("copy", "move"):
            return
        action = choice

    if not original.exists():
        return

    audio_dir = AUDIO_DIR / "local" / today
    audio_dir.mkdir(parents=True, exist_ok=True)
    dest = audio_dir / f"{slug}{original.suffix}"

    if action == "copy":
        shutil.copy2(original, dest)
    elif action == "move":
        shutil.move(str(original), str(dest))
