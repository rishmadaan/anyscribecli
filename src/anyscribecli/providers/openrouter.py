"""OpenRouter transcription provider.

OpenRouter doesn't have a dedicated speech-to-text endpoint. Instead, this
provider uses audio-capable chat models (like GPT-4o-audio) to transcribe
by sending audio as base64 in a chat message.

Note: This is more expensive and slower than dedicated STT APIs.
Best used when you need a specific model that's only on OpenRouter.
"""

from __future__ import annotations

import base64
import os
from pathlib import Path

import httpx

from anyscribecli.providers.base import (
    TranscriptionProvider,
    TranscriptResult,
)
from anyscribecli.core.audio import chunk_audio, needs_chunking


class OpenRouterProvider(TranscriptionProvider):
    """Transcribe using OpenRouter's audio-capable chat models.

    Since OpenRouter doesn't have a Whisper endpoint, this uses
    audio-in-chat (e.g., GPT-4o-audio-preview) with a transcription prompt.
    """

    API_URL = "https://openrouter.ai/api/v1/chat/completions"
    DEFAULT_MODEL = "openai/gpt-4o-audio-preview"

    @property
    def name(self) -> str:
        return "openrouter"

    def _get_api_key(self) -> str:
        key = os.environ.get("OPENROUTER_API_KEY", "")
        if not key:
            raise RuntimeError("OPENROUTER_API_KEY not set. Add it to ~/.anyscribecli/.env")
        return key

    def _transcribe_single(self, audio_path: Path, language: str, api_key: str) -> str:
        """Transcribe a single audio file via OpenRouter chat API."""
        audio_bytes = audio_path.read_bytes()
        audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")

        lang_instruction = ""
        if language != "auto":
            lang_instruction = f" The audio is in {language}."

        response = httpx.post(
            self.API_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "HTTP-Referer": "https://github.com/rishmadaan/anyscribecli",
                "X-Title": "anyscribecli",
                "Content-Type": "application/json",
            },
            json={
                "model": os.environ.get("OPENROUTER_MODEL", self.DEFAULT_MODEL),
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": (
                                    "Transcribe this audio accurately and completely. "
                                    "Output only the transcript text, no commentary."
                                    f"{lang_instruction}"
                                ),
                            },
                            {
                                "type": "input_audio",
                                "input_audio": {
                                    "data": audio_b64,
                                    "format": "mp3",
                                },
                            },
                        ],
                    }
                ],
            },
            timeout=300.0,
        )

        if response.status_code != 200:
            raise RuntimeError(f"OpenRouter API error ({response.status_code}): {response.text}")

        data = response.json()
        return data["choices"][0]["message"]["content"]

    def transcribe(self, audio_path: Path, language: str = "auto") -> TranscriptResult:
        api_key = self._get_api_key()

        if not needs_chunking(audio_path):
            text = self._transcribe_single(audio_path, language, api_key)
            return TranscriptResult(
                text=text, language=language if language != "auto" else "unknown"
            )

        # Chunk large files
        chunks = chunk_audio(audio_path)
        all_text_parts: list[str] = []

        for chunk_path, offset in chunks:
            try:
                text = self._transcribe_single(chunk_path, language, api_key)
                all_text_parts.append(text)
            finally:
                chunk_path.unlink(missing_ok=True)

        full_text = " ".join(all_text_parts)
        return TranscriptResult(
            text=full_text,
            language=language if language != "auto" else "unknown",
            segments=[],  # Chat-based transcription doesn't provide timestamps
        )
