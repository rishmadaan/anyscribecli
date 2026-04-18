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

from anyscribecli.core.errors import classify_api_error, with_retry
from anyscribecli.core.audio import deduplicate_overlap
from anyscribecli.providers.base import (
    TranscriptionProvider,
    TranscriptResult,
    TranscriptSegment,
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

    @with_retry()
    def _transcribe_single(
        self, audio_path: Path, language: str, api_key: str, diarize: bool = False
    ) -> dict:
        """Transcribe a single audio file via Sarvam API (must be <=30s)."""
        with open(audio_path, "rb") as f:
            files = {"file": (audio_path.name, f, "audio/mpeg")}
            data: dict[str, str] = {
                "model": "saaras:v2",
            }
            if language != "auto":
                data["language_code"] = language
            if diarize:
                data["with_diarization"] = "true"

            response = httpx.post(
                self.API_URL,
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

        from anyscribecli.core.checkpoint import ChunkCheckpoint

        chunks = self._chunk_for_sarvam(audio_path)
        ckpt = ChunkCheckpoint.load_or_create(audio_path, self.name, language, len(chunks))
        all_text_parts: list[str] = []
        all_segments: list[TranscriptSegment] = []
        detected_language = ""
        segment_id = 0

        for i, (chunk_path, offset) in enumerate(chunks):
            if ckpt.is_completed(i):
                saved = ckpt.get(i)
                all_text_parts.append(saved["text"])
                if not detected_language:
                    detected_language = saved.get("language", "")
                for seg_data in saved.get("segments", []):
                    all_segments.append(TranscriptSegment(**seg_data))
                    segment_id += 1
                if chunk_path != audio_path:
                    chunk_path.unlink(missing_ok=True)
                continue
            try:
                resp = self._transcribe_single(chunk_path, language, api_key, diarize=diarize)
                result = self._parse_response(resp, offset=offset, start_id=segment_id)
                text = deduplicate_overlap(all_text_parts[-1], result.text) if all_text_parts else result.text
                all_text_parts.append(text)
                if not detected_language:
                    detected_language = result.language
                for seg in result.segments:
                    all_segments.append(seg)
                    segment_id += 1

                ckpt.mark_completed(i, {
                    "text": result.text,
                    "language": result.language,
                    "duration": None,
                    "segments": result.segments,
                })
                ckpt.save()
            finally:
                # Don't delete the original file
                if chunk_path != audio_path:
                    chunk_path.unlink(missing_ok=True)

        ckpt.cleanup()
        full_text = " ".join(all_text_parts)
        return TranscriptResult(
            text=full_text,
            language=detected_language,
            duration=None,
            segments=all_segments,
            word_count=len(full_text.split()),
        )

    def _parse_response(
        self, data: dict, offset: float = 0.0, start_id: int = 0
    ) -> TranscriptResult:
        """Parse Sarvam response into TranscriptResult."""
        transcript = data.get("transcript", "")
        language = data.get("language_code", "unknown")

        segments: list[TranscriptSegment] = []

        # Parse diarized output if available
        turns = data.get("turns") or data.get("diarized_transcript") or []
        if turns:
            for i, turn in enumerate(turns):
                speaker = turn.get("speaker") or turn.get("speaker_id")
                text = turn.get("text") or turn.get("transcript", "")
                start = turn.get("start", 0.0) + offset
                end = turn.get("end", start) + offset
                if text.strip():
                    segments.append(
                        TranscriptSegment(
                            id=start_id + i,
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
