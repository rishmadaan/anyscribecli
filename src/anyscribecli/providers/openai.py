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
from anyscribecli.core.audio import chunk_audio, needs_chunking


class OpenAIProvider(TranscriptionProvider):
    """Transcribe using OpenAI's Whisper API.

    Uses the same parameters proven in the AnyScribe web app:
    model=whisper-1, response_format=verbose_json, timestamp_granularities=[segment]
    """

    API_URL = "https://api.openai.com/v1/audio/transcriptions"
    MODEL = "whisper-1"  # default; subclasses (e.g. Groq) override this

    # Models that only accept response_format=json — no verbose_json, so no
    # segment timestamps (timestamped/diarized output falls back to clean text).
    # whisper-1 stays the default because it's the only file model with
    # segments; gpt-transcribe is cheaper and more accurate for plain text.
    NO_SEGMENT_MODELS = {"gpt-transcribe", "gpt-4o-transcribe", "gpt-4o-mini-transcribe"}

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
        model = self.model or self.MODEL
        with open(audio_path, "rb") as f:
            files = {"file": (audio_path.name, f, "audio/mpeg")}
            data: dict[str, str] = {
                "model": model,
                "response_format": "verbose_json",
                "timestamp_granularities[]": "segment",
            }
            if model in self.NO_SEGMENT_MODELS:
                data = {"model": model, "response_format": "json"}
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
            # Spec: this model supports json/text/diarized_json only —
            # diarized_json is required for speaker labels, and
            # chunking_strategy is required for audio longer than 30s.
            data: dict[str, str] = {
                "model": "gpt-4o-transcribe-diarize",
                "response_format": "diarized_json",
                "chunking_strategy": "auto",
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
                    f'  scribe "{audio_path.name}" --diarize\n\n'
                    f"Or transcribe without diarization (will chunk automatically):\n"
                    f'  scribe "{audio_path.name}" -p openai'
                )
            result = self._parse_response(
                self._transcribe_diarize(audio_path, language, api_key), diarize=True
            )
            # diarized_json responses carry no language field — echo the
            # requested language rather than writing "unknown" to frontmatter.
            if result.language == "unknown" and language != "auto":
                result.language = language
            return result

        if not needs_chunking(audio_path):
            return self._parse_response(self._transcribe_single(audio_path, language, api_key))

        return self._transcribe_chunked(
            audio_path,
            chunk_audio(audio_path),
            language,
            lambda p: self._parse_response(self._transcribe_single(p, language, api_key)),
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
        # gpt-transcribe's json format reports detected languages as a list of
        # objects ("languages": [{"code": "fr"}]) instead of whisper-1's single
        # "language" string. Tolerate bare strings too.
        language = data.get("language")
        if not language:
            first = next(iter(data.get("languages") or []), None)
            language = first.get("code") if isinstance(first, dict) else first
        language = language or "unknown"
        return TranscriptResult(
            text=text,
            language=language,
            duration=data.get("duration"),
            segments=segments,
        )
