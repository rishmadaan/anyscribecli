"""Sargam (Sarvam) AI transcription provider.

Sarvam provides speech-to-text with strength in Indic languages.
REST API is limited to 30-second clips, so audio is chunked into
30-second segments before transcription.

Docs: https://docs.sarvam.ai/api-reference-docs/speech-to-text/transcribe
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import httpx

from anyscribecli.providers.base import (
    TranscriptionProvider,
    TranscriptResult,
)

# Sarvam REST API limit: 30 seconds per request
SARVAM_MAX_DURATION = 30


class SargamProvider(TranscriptionProvider):
    """Transcribe using Sarvam AI's speech-to-text API.

    Particularly strong for Indic languages (Hindi, Tamil, Telugu, etc.).
    Note: REST API limited to 30-second clips — audio is auto-chunked.
    """

    API_URL = "https://api.sarvam.ai/speech-to-text-translate"

    @property
    def name(self) -> str:
        return "sargam"

    def _get_api_key(self) -> str:
        key = os.environ.get("SARGAM_API_KEY", "")
        if not key:
            raise RuntimeError("SARGAM_API_KEY not set. Add it to ~/.anyscribecli/.env")
        return key

    def _transcribe_single(self, audio_path: Path, language: str, api_key: str) -> dict:
        """Transcribe a single audio file via Sarvam API (must be <=30s)."""
        with open(audio_path, "rb") as f:
            files = {"file": (audio_path.name, f, "audio/mpeg")}
            data: dict[str, str] = {
                "model": "saaras:v2",
            }
            if language != "auto":
                data["language_code"] = language

            response = httpx.post(
                self.API_URL,
                headers={"api-subscription-key": api_key},
                files=files,
                data=data,
                timeout=60.0,
            )

        if response.status_code != 200:
            raise RuntimeError(f"Sarvam API error ({response.status_code}): {response.text}")
        return response.json()

    def _chunk_for_sarvam(self, audio_path: Path) -> list[tuple[Path, float]]:
        """Split audio into 30-second chunks for Sarvam's REST API limit."""
        from anyscribecli.core.audio import get_audio_duration

        duration = get_audio_duration(audio_path)
        if duration <= SARVAM_MAX_DURATION:
            return [(audio_path, 0.0)]

        chunks: list[tuple[Path, float]] = []
        chunk_dir = audio_path.parent
        stem = audio_path.stem
        offset = 0.0
        chunk_num = 0

        while offset < duration:
            chunk_path = chunk_dir / f"{stem}_sarvam{chunk_num:03d}.mp3"
            cmd = [
                "ffmpeg",
                "-y",
                "-i",
                str(audio_path),
                "-ss",
                str(offset),
                "-t",
                str(SARVAM_MAX_DURATION),
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
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode != 0:
                raise RuntimeError(f"ffmpeg chunking failed: {result.stderr.strip()[:200]}")

            chunks.append((chunk_path, offset))
            offset += SARVAM_MAX_DURATION
            chunk_num += 1

        return chunks

    def transcribe(self, audio_path: Path, language: str = "auto") -> TranscriptResult:
        api_key = self._get_api_key()

        chunks = self._chunk_for_sarvam(audio_path)
        all_text_parts: list[str] = []
        detected_language = ""

        for chunk_path, offset in chunks:
            try:
                resp = self._transcribe_single(chunk_path, language, api_key)
                result = self._parse_response(resp)
                all_text_parts.append(result.text)
                if not detected_language:
                    detected_language = result.language
            finally:
                # Don't delete the original file
                if chunk_path != audio_path:
                    chunk_path.unlink(missing_ok=True)

        full_text = " ".join(all_text_parts)
        return TranscriptResult(
            text=full_text,
            language=detected_language,
            duration=None,
            segments=[],
            word_count=len(full_text.split()),
        )

    def _parse_response(self, data: dict) -> TranscriptResult:
        """Parse Sarvam response into TranscriptResult."""
        transcript = data.get("transcript", "")
        language = data.get("language_code", "unknown")

        return TranscriptResult(
            text=transcript,
            language=language,
            duration=None,
            segments=[],
        )
