"""YouTube downloader using yt-dlp subprocess."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from anyscribecli.downloaders.base import AbstractDownloader, DownloadResult


class YouTubeDownloader(AbstractDownloader):
    """Download audio from YouTube using yt-dlp.

    Mirrors the approach from the Dropzone YouTube Downloader bundle:
    yt-dlp subprocess with optimized audio parameters for Whisper.
    """

    PATTERNS = [
        "youtube.com/watch",
        "youtu.be/",
        "youtube.com/shorts/",
        "youtube.com/live/",
    ]

    def can_handle(self, url: str) -> bool:
        return any(p in url for p in self.PATTERNS)

    def download(self, url: str, output_dir: Path) -> DownloadResult:
        from anyscribecli.core.deps import ensure_ytdlp_current, get_command

        ensure_ytdlp_current()
        ytdlp = get_command("yt-dlp")

        output_dir.mkdir(parents=True, exist_ok=True)
        output_template = str(output_dir / "%(title).80s.%(ext)s")

        # Step 1: Get metadata via --dump-json
        meta_cmd = [*ytdlp, "--dump-json", "--no-download", url]
        meta_result = subprocess.run(meta_cmd, capture_output=True, text=True, timeout=60)
        if meta_result.returncode != 0:
            raise RuntimeError(f"yt-dlp metadata failed: {meta_result.stderr.strip()}")

        metadata = json.loads(meta_result.stdout)
        title = metadata.get("title", "untitled")
        duration = metadata.get("duration")
        channel = metadata.get("channel", metadata.get("uploader", ""))
        description = metadata.get("description", "")

        # Step 2: Download audio optimized for Whisper
        # 16kHz mono 64kbps mp3 — proven optimal from AnyScribe web app
        dl_cmd = [
            *ytdlp,
            "--extract-audio",
            "--audio-format",
            "mp3",
            "--postprocessor-args",
            "ffmpeg:-ar 16000 -ac 1 -b:a 64k",
            "--output",
            output_template,
            "--no-playlist",
            "--no-overwrites",
            url,
        ]
        dl_result = subprocess.run(dl_cmd, capture_output=True, text=True, timeout=600)
        if dl_result.returncode != 0:
            raise RuntimeError(f"yt-dlp download failed: {dl_result.stderr.strip()}")

        # Find the downloaded file
        mp3_files = list(output_dir.glob("*.mp3"))
        if not mp3_files:
            raise RuntimeError("Download completed but no mp3 file found.")
        audio_path = mp3_files[0]

        return DownloadResult(
            audio_path=audio_path,
            title=title,
            duration=duration,
            platform="youtube",
            original_url=url,
            channel=channel,
            description=description,
        )
