"""Local file 'downloader' — converts local audio/video files for transcription."""

from __future__ import annotations

import subprocess
from pathlib import Path

from anyscribecli.core.audio import get_audio_duration
from anyscribecli.downloaders.base import AbstractDownloader, DownloadResult

# Audio and video formats that ffmpeg can handle
SUPPORTED_EXTENSIONS = {
    ".mp3",
    ".mp4",
    ".m4a",
    ".wav",
    ".opus",
    ".ogg",
    ".flac",
    ".webm",
    ".aac",
    ".wma",
}


class LocalFileDownloader(AbstractDownloader):
    """Handle local audio/video files instead of URLs."""

    def can_handle(self, url: str) -> bool:
        """Return True if input is an existing local file with a supported extension."""
        if url.startswith("http://") or url.startswith("https://"):
            return False
        path = Path(url).expanduser().resolve()
        return path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS

    def download(self, url: str, output_dir: Path) -> DownloadResult:
        """Convert the local file to Whisper-optimized mp3 and return metadata."""
        input_path = Path(url).expanduser().resolve()
        if not input_path.exists():
            raise FileNotFoundError(f"File not found: {input_path}")

        output_dir.mkdir(parents=True, exist_ok=True)
        title = input_path.stem
        audio_path = output_dir / f"{title}.mp3"

        # Convert to 16kHz mono 64kbps mp3 (Whisper-optimized)
        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            str(input_path),
            "-ar",
            "16000",
            "-ac",
            "1",
            "-b:a",
            "64k",
            "-f",
            "mp3",
            str(audio_path),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        if result.returncode != 0:
            raise RuntimeError(f"ffmpeg conversion failed: {result.stderr.strip()}")

        duration = get_audio_duration(audio_path)

        return DownloadResult(
            audio_path=audio_path,
            title=title,
            duration=duration,
            platform="local",
            original_url=str(input_path),
        )
