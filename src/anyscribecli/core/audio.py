"""Audio processing — chunking for files exceeding Whisper's size limit."""

from __future__ import annotations

import subprocess
from pathlib import Path

# Whisper API limit is 25MB
WHISPER_MAX_BYTES = 25 * 1024 * 1024

# Max duration to send as a single request.
# Even files under 25MB can timeout if the audio is too long — Whisper's
# processing time scales with duration, not file size. At 64kbps mono,
# a 75-min file is only ~20MB (under the size limit) but takes ~700s to
# process, well over the 300s HTTP timeout. 30 minutes is a safe ceiling.
WHISPER_MAX_DURATION_SECONDS = 30 * 60

# 18-minute chunks stay well under 25MB at 64kbps mono
# (18 min * 60 sec * 64kbit/8 = ~8.6MB per chunk)
CHUNK_DURATION_SECONDS = 18 * 60


def needs_chunking(audio_path: Path) -> bool:
    """Check if an audio file needs chunking before upload.

    Triggers on file size (>25MB) OR duration (>30 min). The duration check
    catches files that are small due to aggressive compression but too long
    for the API to process within the HTTP timeout.
    """
    if audio_path.stat().st_size > WHISPER_MAX_BYTES:
        return True
    try:
        duration = get_audio_duration(audio_path)
        return duration > WHISPER_MAX_DURATION_SECONDS
    except Exception:
        # If we can't determine duration, fall back to size-only check
        return False


def get_audio_duration(audio_path: Path) -> float:
    """Get duration of an audio file in seconds using ffprobe."""
    cmd = [
        "ffprobe",
        "-v",
        "quiet",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(audio_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if result.returncode != 0:
        raise RuntimeError(f"ffprobe failed: {result.stderr.strip()}")
    return float(result.stdout.strip())


def chunk_audio(audio_path: Path) -> list[tuple[Path, float]]:
    """Split audio into chunks for Whisper API.

    Returns list of (chunk_path, offset_seconds) tuples.
    Chunks are written to the same directory as the source file.
    """
    duration = get_audio_duration(audio_path)
    if duration <= CHUNK_DURATION_SECONDS:
        return [(audio_path, 0.0)]

    chunks: list[tuple[Path, float]] = []
    chunk_dir = audio_path.parent
    stem = audio_path.stem
    offset = 0.0
    chunk_num = 0

    while offset < duration:
        chunk_path = chunk_dir / f"{stem}_chunk{chunk_num:03d}.mp3"
        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            str(audio_path),
            "-ss",
            str(offset),
            "-t",
            str(CHUNK_DURATION_SECONDS),
            "-ar",
            "16000",
            "-ac",
            "1",
            "-b:a",
            "64k",
            "-f",
            "mp3",
            str(chunk_path),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode != 0:
            raise RuntimeError(f"ffmpeg chunking failed: {result.stderr.strip()}")

        chunks.append((chunk_path, offset))
        offset += CHUNK_DURATION_SECONDS
        chunk_num += 1

    return chunks
