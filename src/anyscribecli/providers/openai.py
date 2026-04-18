"""OpenAI Whisper transcription provider."""

from __future__ import annotations

import os
from pathlib import Path

import httpx

from anyscribecli.core.errors import classify_api_error, with_retry
from anyscribecli.providers.base import (
    TranscriptionProvider,
    TranscriptResult,
    TranscriptSegment,
)
from anyscribecli.core.audio import chunk_audio, deduplicate_overlap, needs_chunking


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

    @with_retry()
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
            raise classify_api_error(response.status_code, response.text, self.name)
        return response.json()

    @with_retry()
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
            raise classify_api_error(response.status_code, response.text, self.name)
        return response.json()

    def transcribe(
        self, audio_path: Path, language: str = "auto", diarize: bool = False
    ) -> TranscriptResult:
        api_key = self._get_api_key()

        if diarize:
            if needs_chunking(audio_path):
                size_mb = audio_path.stat().st_size / (1024 * 1024)
                raise RuntimeError(
                    f"File is {size_mb:.0f}MB — OpenAI's diarize endpoint has a 25MB limit "
                    f"and doesn't support chunking.\n\n"
                    f"Use Deepgram instead (handles large files natively with better speaker detection):\n"
                    f"  scribe config set deepgram_api_key YOUR_KEY\n"
                    f"  scribe \"{audio_path.name}\" --diarize\n\n"
                    f"Or transcribe without diarization (will chunk automatically):\n"
                    f"  scribe \"{audio_path.name}\" -p openai"
                )
            return self._parse_response(
                self._transcribe_diarize(audio_path, language, api_key), diarize=True
            )

        if not needs_chunking(audio_path):
            return self._parse_response(self._transcribe_single(audio_path, language, api_key))

        # Chunk large files (>25MB) — pattern from AnyScribe web app
        from anyscribecli.core.checkpoint import ChunkCheckpoint

        chunks = chunk_audio(audio_path)
        ckpt = ChunkCheckpoint.load_or_create(audio_path, self.name, language, len(chunks))
        all_text_parts: list[str] = []
        all_segments: list[TranscriptSegment] = []
        detected_language = ""
        total_duration = 0.0
        segment_id = 0

        for i, (chunk_path, offset) in enumerate(chunks):
            if ckpt.is_completed(i):
                saved = ckpt.get(i)
                all_text_parts.append(saved["text"])
                if not detected_language:
                    detected_language = saved.get("language", "")
                for seg_data in saved.get("segments", []):
                    all_segments.append(TranscriptSegment(**seg_data))
                    segment_id = max(segment_id, seg_data.get("id", 0) + 1)
                if saved.get("duration"):
                    total_duration = max(total_duration, offset + saved["duration"])
                chunk_path.unlink(missing_ok=True)
                continue
            try:
                resp = self._transcribe_single(chunk_path, language, api_key)
                result = self._parse_response(resp)

                text = deduplicate_overlap(all_text_parts[-1], result.text) if all_text_parts else result.text
                all_text_parts.append(text)
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

                ckpt.mark_completed(i, {
                    "text": result.text,
                    "language": result.language,
                    "duration": result.duration,
                    "segments": result.segments,
                })
                ckpt.save()
            finally:
                chunk_path.unlink(missing_ok=True)

        ckpt.cleanup()
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
