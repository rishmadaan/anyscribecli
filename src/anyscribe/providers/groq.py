"""Groq transcription provider — fast, cheap Whisper.

Groq's speech-to-text API is OpenAI-compatible (same multipart request,
verbose_json + segment timestamps, same response shape), so this is a thin
subclass of OpenAIProvider: only the endpoint, key, and model differ. Chunking
and response parsing are inherited unchanged.
Docs: https://console.groq.com/docs/speech-to-text
"""

from __future__ import annotations

import os
from pathlib import Path

from anyscribe.providers.openai import OpenAIProvider


class GroqProvider(OpenAIProvider):
    """Transcribe using Groq's whisper-large-v3-turbo (OpenAI-compatible API)."""

    API_URL = "https://api.groq.com/openai/v1/audio/transcriptions"
    MODEL = "whisper-large-v3-turbo"

    @property
    def name(self) -> str:
        return "groq"

    def _get_api_key(self) -> str:
        key = os.environ.get("GROQ_API_KEY", "")
        if not key:
            raise RuntimeError("GROQ_API_KEY not set. Add it to ~/.anyscribe/.env")
        return key

    def _transcribe_diarize(self, audio_path: Path, language: str, api_key: str) -> dict:
        raise RuntimeError(
            "Groq has no diarization model. Use the accuracy or balanced quality tier "
            "(or --provider deepgram) for speaker labels."
        )
