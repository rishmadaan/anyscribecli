"""ElevenLabs speech-to-text provider.

Uses ElevenLabs' Speech to Text API for transcription.
Docs: https://elevenlabs.io/docs/api-reference/speech-to-text
"""

from __future__ import annotations

import os
from pathlib import Path

import httpx

from anyscribecli.providers.base import (
    TranscriptionProvider,
    TranscriptResult,
    TranscriptSegment,
)
from anyscribecli.core.audio import WHISPER_MAX_BYTES, chunk_audio


class ElevenLabsProvider(TranscriptionProvider):
    """Transcribe using ElevenLabs Speech to Text API."""

    API_URL = "https://api.elevenlabs.io/v1/speech-to-text"

    @property
    def name(self) -> str:
        return "elevenlabs"

    def _get_api_key(self) -> str:
        key = os.environ.get("ELEVENLABS_API_KEY", "")
        if not key:
            raise RuntimeError(
                "ELEVENLABS_API_KEY not set. Add it to ~/.anyscribecli/.env"
            )
        return key

    def _transcribe_single(
        self, audio_path: Path, language: str, api_key: str
    ) -> dict:
        """Transcribe a single audio file via ElevenLabs."""
        with open(audio_path, "rb") as f:
            files = {"file": (audio_path.name, f, "audio/mpeg")}
            data: dict[str, str] = {
                "model_id": "scribe_v1",
            }
            if language != "auto":
                data["language_code"] = language

            response = httpx.post(
                self.API_URL,
                headers={"xi-api-key": api_key},
                files=files,
                data=data,
                timeout=300.0,
            )

        if response.status_code != 200:
            raise RuntimeError(
                f"ElevenLabs API error ({response.status_code}): {response.text}"
            )
        return response.json()

    def transcribe(self, audio_path: Path, language: str = "auto") -> TranscriptResult:
        api_key = self._get_api_key()
        file_size = audio_path.stat().st_size

        if file_size <= WHISPER_MAX_BYTES:
            return self._parse_response(
                self._transcribe_single(audio_path, language, api_key)
            )

        # Chunk large files
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

    def _parse_response(self, data: dict) -> TranscriptResult:
        """Parse ElevenLabs response into TranscriptResult.

        ElevenLabs returns: {text, language_code, words: [{text, start, end, type}...]}
        """
        text = data.get("text", "")
        language = data.get("language_code", "unknown")

        # Build segments from word-level data grouped by sentences
        segments: list[TranscriptSegment] = []
        words = data.get("words", [])

        if words:
            # Group words into ~30-word segments for readability
            chunk_size = 30
            for i in range(0, len(words), chunk_size):
                word_chunk = words[i : i + chunk_size]
                seg_text = " ".join(w.get("text", "") for w in word_chunk).strip()
                start = word_chunk[0].get("start", 0)
                end = word_chunk[-1].get("end", 0)
                if seg_text:
                    segments.append(
                        TranscriptSegment(
                            id=len(segments),
                            start=start,
                            end=end,
                            text=seg_text,
                        )
                    )

        duration = words[-1].get("end") if words else None

        return TranscriptResult(
            text=text,
            language=language,
            duration=duration,
            segments=segments,
        )
