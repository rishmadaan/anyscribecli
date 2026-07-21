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

# Overlap between adjacent chunks to avoid cutting words at boundaries
CHUNK_OVERLAP_SECONDS = 5


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
        # Each chunk captures CHUNK_DURATION + overlap, but offset advances
        # by CHUNK_DURATION only — so adjacent chunks share OVERLAP seconds.
        chunk_len = CHUNK_DURATION_SECONDS
        if offset > 0:
            chunk_len += CHUNK_OVERLAP_SECONDS  # capture overlap at start
        remaining = duration - offset
        if remaining < chunk_len:
            chunk_len = remaining  # last chunk: no padding needed
        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            str(audio_path),
            "-ss",
            str(max(0, offset - (CHUNK_OVERLAP_SECONDS if offset > 0 else 0))),
            "-t",
            str(chunk_len),
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


def deduplicate_overlap(prev_text: str, curr_text: str, overlap_words: int = 15) -> str:
    """Remove duplicate words at the boundary between two adjacent chunks.

    Finds the longest suffix of prev_text that matches a prefix of curr_text,
    and returns curr_text with the overlap removed.
    """
    if not prev_text or not curr_text:
        return curr_text

    prev_words = prev_text.split()
    curr_words = curr_text.split()

    if len(prev_words) < 3 or len(curr_words) < 3:
        return curr_text

    # Check progressively shorter suffixes of prev against prefix of curr
    max_check = min(overlap_words, len(prev_words), len(curr_words))
    best_match = 0
    for length in range(max_check, 1, -1):
        tail = prev_words[-length:]
        head = curr_words[:length]
        if tail == head:
            best_match = length
            break

    if best_match > 0:
        return " ".join(curr_words[best_match:])
    return curr_text
