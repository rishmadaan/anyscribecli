"""OpenAI Whisper transcription provider."""

from __future__ import annotations

import os
from pathlib import Path

import httpx

from anyscribecli.providers.base import (
    TranscriptionProvider,
    TranscriptResult,
    TranscriptSegment,
)
from anyscribecli.core.audio import chunk_audio, needs_chunking


class OpenAIProvider(TranscriptionProvider):
    """Transcribe using OpenAI's Whisper API.

    Uses the same parameters proven in the AnyScribe web app:
    model=whisper-1, response_format=verbose_json, timestamp_granularities=[segment]
    """

    API_URL = "https://api.openai.com/v1/audio/transcriptions"

    @property
    def name(self) -> str:
        return "openai"

    def _get_api_key(self) -> str:
        key = os.environ.get("OPENAI_API_KEY", "")
        if not key:
            raise RuntimeError(
                "OPENAI_API_KEY not set. Run 'scribe onboard' or set it in ~/.anyscribecli/.env"
            )
        return key

    def _transcribe_single(self, audio_path: Path, language: str, api_key: str) -> dict:
        """Transcribe a single audio file (must be <= 25MB)."""
        with open(audio_path, "rb") as f:
            files = {"file": (audio_path.name, f, "audio/mpeg")}
            data: dict[str, str] = {
                "model": "whisper-1",
                "response_format": "verbose_json",
                "timestamp_granularities[]": "segment",
            }
            if language != "auto":
                data["language"] = language

            response = httpx.post(
                self.API_URL,
                headers={"Authorization": f"Bearer {api_key}"},
                files=files,
                data=data,
                timeout=300.0,
            )

        if response.status_code != 200:
            raise RuntimeError(f"Whisper API error ({response.status_code}): {response.text}")
        return response.json()

    def _transcribe_diarize(self, audio_path: Path, language: str, api_key: str) -> dict:
        """Transcribe with speaker diarization using gpt-4o-transcribe-diarize."""
        with open(audio_path, "rb") as f:
            files = {"file": (audio_path.name, f, "audio/mpeg")}
            data: dict[str, str] = {
                "model": "gpt-4o-transcribe-diarize",
                "response_format": "verbose_json",
            }
            if language != "auto":
                data["language"] = language

            response = httpx.post(
                self.API_URL,
                headers={"Authorization": f"Bearer {api_key}"},
                files=files,
                data=data,
                timeout=600.0,
            )

        if response.status_code != 200:
            raise RuntimeError(
                f"OpenAI diarize API error ({response.status_code}): {response.text}"
            )
        return response.json()

    def transcribe(
        self, audio_path: Path, language: str = "auto", diarize: bool = False
    ) -> TranscriptResult:
        api_key = self._get_api_key()

        if diarize:
            # gpt-4o-transcribe-diarize handles chunking server-side
            return self._parse_response(
                self._transcribe_diarize(audio_path, language, api_key), diarize=True
            )

        if not needs_chunking(audio_path):
            return self._parse_response(self._transcribe_single(audio_path, language, api_key))

        # Chunk large files (>25MB) — pattern from AnyScribe web app
        chunks = chunk_audio(audio_path)
        all_text_parts: list[str] = []
        all_segments: list[TranscriptSegment] = []
        detected_language = ""
        total_duration = 0.0
        segment_id = 0

        for chunk_path, offset in chunks:
            try:
                resp = self._transcribe_single(chunk_path, language, api_key)
                result = self._parse_response(resp)

                all_text_parts.append(result.text)
                if not detected_language:
                    detected_language = result.language

                # Offset segment timestamps
                for seg in result.segments:
                    seg.id = segment_id
                    seg.start += offset
                    seg.end += offset
                    segment_id += 1
                    all_segments.append(seg)

                if result.duration:
                    total_duration = max(total_duration, offset + result.duration)
            finally:
                chunk_path.unlink(missing_ok=True)

        full_text = " ".join(all_text_parts)
        return TranscriptResult(
            text=full_text,
            language=detected_language,
            duration=total_duration or None,
            segments=all_segments,
            word_count=len(full_text.split()),
        )

    def _parse_response(self, data: dict, diarize: bool = False) -> TranscriptResult:
        """Parse Whisper/diarize API verbose_json response into TranscriptResult."""
        segments = []
        for i, seg in enumerate(data.get("segments", [])):
            speaker = None
            if diarize:
                speaker = seg.get("speaker")
            segments.append(
                TranscriptSegment(
                    id=seg.get("id", i),
                    start=seg["start"],
                    end=seg["end"],
                    text=seg["text"].strip(),
                    speaker=speaker,
                )
            )

        text = data.get("text", "")
        return TranscriptResult(
            text=text,
            language=data.get("language", "unknown"),
            duration=data.get("duration"),
            segments=segments,
        )
