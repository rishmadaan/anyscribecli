"""Download command — download video only, no transcription."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

from anyscribecli.config.paths import TMP_DIR, VIDEO_DIR, AUDIO_DIR
from anyscribecli.config.settings import load_env

console = Console()
err_console = Console(stderr=True)


def download(
    url: Optional[str] = typer.Argument(None, help="YouTube or Instagram URL to download."),
    video: bool = typer.Option(
        True, "--video/--audio-only", help="Download video (default) or audio only."
    ),
    output_json: bool = typer.Option(False, "--json", "-j", help="Output result as JSON."),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="Suppress progress output."),
    clipboard: bool = typer.Option(False, "--clipboard", "-c", help="Read URL from clipboard."),
) -> None:
    """[bold green]Download[/bold green] video or audio from a URL — no transcription.

    Saves to ~/.anyscribecli/downloads/video/ or ~/.anyscribecli/downloads/audio/.

    [dim]Tip: Wrap URLs in quotes to avoid shell issues.[/dim]
    """
    from anyscribecli.cli.transcribe import _read_clipboard, _validate_url
    from anyscribecli.downloaders.registry import get_downloader, detect_platform

    # Resolve URL
    if clipboard:
        url = _read_clipboard()
        if not url:
            err_console.print("[red]Error:[/red] No URL found in clipboard.")
            raise typer.Exit(code=1)

    if not url:
        console.print("  Paste a YouTube or Instagram URL:")
        url = typer.prompt("  URL")

    if not url:
        err_console.print("[red]Error:[/red] No URL provided.")
        raise typer.Exit(code=1)

    url = _validate_url(url)
    load_env()

    from anyscribecli.vault.writer import slugify

    TMP_DIR.mkdir(parents=True, exist_ok=True)
    tmp_dir = Path(tempfile.mkdtemp(dir=TMP_DIR))

    try:
        if not quiet:
            err_console.print("[bold blue]Downloading...[/bold blue]")

        downloader = get_downloader(url)
        platform = detect_platform(url)

        if video:
            # Download full video
            result = _download_video(url, platform, tmp_dir, quiet)
        else:
            # Download audio only (same as transcribe pipeline)
            dl_result = downloader.download(url, tmp_dir)
            slug = slugify(dl_result.title) or "untitled"
            dest_dir = AUDIO_DIR / platform
            dest_dir.mkdir(parents=True, exist_ok=True)
            dest = dest_dir / f"{slug}{dl_result.audio_path.suffix}"
            shutil.copy2(dl_result.audio_path, dest)
            result = {
                "file": str(dest),
                "title": dl_result.title,
                "platform": platform,
                "type": "audio",
                "duration": dl_result.duration,
            }

        if output_json:
            json.dump({"success": True, "data": result, "error": None}, sys.stdout, indent=2)
            sys.stdout.write("\n")
        else:
            console.print(f"\n[green]Downloaded:[/green] {result['file']}")
            console.print(f"  Title: {result['title']}")
            console.print(f"  Type:  {result['type']}")

    except Exception as e:
        if output_json:
            json.dump({"success": False, "data": None, "error": str(e)}, sys.stdout, indent=2)
            sys.stdout.write("\n")
        else:
            err_console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1)
    finally:
        if tmp_dir.exists():
            shutil.rmtree(tmp_dir, ignore_errors=True)


def _download_video(url: str, platform: str, tmp_dir: Path, quiet: bool) -> dict:
    """Download full video using yt-dlp (works for both YouTube and Instagram)."""
    from anyscribecli.core.deps import ensure_ytdlp_current, get_command
    from anyscribecli.vault.writer import slugify

    ensure_ytdlp_current()

    # yt-dlp can handle both YouTube and Instagram video URLs
    output_template = str(tmp_dir / "%(title).80s.%(ext)s")
    cmd = [
        *get_command("yt-dlp"),
        "--format",
        "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "--merge-output-format",
        "mp4",
        "--output",
        output_template,
        "--no-playlist",
        "--print-json",
    ]
    if quiet:
        cmd.append("--quiet")
    cmd.append(url)

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    if result.returncode != 0:
        raise RuntimeError(f"Download failed: {result.stderr.strip()[:300]}")

    import json as _json

    metadata = _json.loads(result.stdout.split("\n")[0])
    title = metadata.get("title", "untitled")

    # Find the downloaded video
    video_files = (
        list(tmp_dir.glob("*.mp4")) + list(tmp_dir.glob("*.mkv")) + list(tmp_dir.glob("*.webm"))
    )
    if not video_files:
        raise RuntimeError("Download completed but no video file found.")
    video_path = video_files[0]

    # Move to downloads/video/<platform>/<slug>.mp4
    slug = slugify(title) or "untitled"
    dest_dir = VIDEO_DIR / platform
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / f"{slug}{video_path.suffix}"
    shutil.move(str(video_path), str(dest))

    if not quiet:
        err_console.print(f"  [green]Saved:[/green] {title}")

    return {
        "file": str(dest),
        "title": title,
        "platform": platform,
        "type": "video",
        "duration": metadata.get("duration"),
    }
