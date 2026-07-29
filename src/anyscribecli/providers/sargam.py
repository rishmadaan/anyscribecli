"""Sargam (Sarvam) AI transcription provider.

Sarvam provides speech-to-text with strength in Indic languages.
REST API is limited to 30-second clips (exclusive), so audio is chunked into
sub-30-second (28s) segments before transcription.

Docs: https://docs.sarvam.ai/api-reference-docs/speech-to-text/transcribe
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import httpx

from anyscribecli.core.errors import classify_api_error, with_retry
from anyscribecli.providers.base import (
    TranscriptionProvider,
    TranscriptResult,
    TranscriptSegment,
)

# Sarvam REST sync API limit is 30s and EXCLUSIVE — a clip of exactly 30.0s is
# rejected ("exceeds the maximum limit of 30 seconds"). Chunk a couple seconds
# under to stay clear of the boundary (mp3 frame rounding can also nudge it up).
# ponytail: longer audio should really use Sarvam's batch API — future work.
SARVAM_MAX_DURATION = 28


class SargamProvider(TranscriptionProvider):
    """Transcribe using Sarvam AI's speech-to-text API.

    Particularly strong for Indic languages (Hindi, Tamil, Telugu, etc.).
    Note: REST API limited to 30-second clips — audio is auto-chunked.
    """

    # saaras:v3 (default) lives on /speech-to-text with a mode param; the old
    # /speech-to-text-translate endpoint is legacy, kept only for saaras:v2.5.
    # mode=translate preserves the historical translate-to-English behaviour.
    # Both endpoints share the 30s sync limit, so chunking is identical.
    API_URL = "https://api.sarvam.ai/speech-to-text"
    LEGACY_API_URL = "https://api.sarvam.ai/speech-to-text-translate"

    @property
    def name(self) -> str:
        return "sargam"

    def _get_api_key(self) -> str:
        key = os.environ.get("SARGAM_API_KEY", "")
        if not key:
            raise RuntimeError("SARGAM_API_KEY not set. Add it to ~/.anyscribecli/.env")
        return key

    @with_retry()
    def _transcribe_single(
        self, audio_path: Path, language: str, api_key: str, diarize: bool = False
    ) -> dict:
        """Transcribe a single audio file via Sarvam API (must be <=30s)."""
        model = self.model or "saaras:v3"
        legacy = model == "saaras:v2.5"
        with open(audio_path, "rb") as f:
            files = {"file": (audio_path.name, f, "audio/mpeg")}
            data: dict[str, str] = {"model": model}
            if not legacy:
                data["mode"] = "translate"
            if language != "auto":
                data["language_code"] = language
            if diarize:
                data["with_diarization"] = "true"

            response = httpx.post(
                self.LEGACY_API_URL if legacy else self.API_URL,
                headers={"api-subscription-key": api_key},
                files=files,
                data=data,
                timeout=60.0,
            )

        if response.status_code != 200:
            raise classify_api_error(response.status_code, response.text, self.name)
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

    def transcribe(
        self, audio_path: Path, language: str = "auto", diarize: bool = False
    ) -> TranscriptResult:
        api_key = self._get_api_key()
        return self._transcribe_chunked(
            audio_path,
            self._chunk_for_sarvam(audio_path),
            language,
            lambda p: self._parse_response(
                self._transcribe_single(p, language, api_key, diarize=diarize)
            ),
        )

    def _parse_response(self, data: dict) -> TranscriptResult:
        """Parse Sarvam response into a chunk-local TranscriptResult."""
        transcript = data.get("transcript", "")
        language = data.get("language_code", "unknown")

        segments: list[TranscriptSegment] = []
        turns = data.get("turns") or data.get("diarized_transcript") or []
        for i, turn in enumerate(turns):
            speaker = turn.get("speaker")
            if speaker is None:
                speaker = turn.get("speaker_id")
            text = turn.get("text") or turn.get("transcript", "")
            start = turn.get("start", 0.0)
            end = turn.get("end", start)
            if text.strip():
                segments.append(
                    TranscriptSegment(
                        id=i,
                        start=start,
                        end=end,
                        text=text.strip(),
                        speaker=str(speaker) if speaker is not None else None,
                    )
                )

        return TranscriptResult(
            text=transcript,
            language=language,
            duration=None,
            segments=segments,
        )
