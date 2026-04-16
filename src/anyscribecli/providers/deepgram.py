"""Deepgram Nova transcription provider.

Deepgram provides fast, accurate speech-to-text with native speaker
diarization and support for Hindi Latin script (hi-Latn).

Docs: https://developers.deepgram.com/docs/getting-started-with-pre-recorded-audio
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
from anyscribecli.core.audio import chunk_audio, needs_chunking


class DeepgramProvider(TranscriptionProvider):
    """Transcribe using Deepgram's Nova API.

    Supports speaker diarization, Hindi Latin (hi-Latn), and smart formatting.
    """

    API_URL = "https://api.deepgram.com/v1/listen"

    @property
    def name(self) -> str:
        return "deepgram"

    def _get_api_key(self) -> str:
        key = os.environ.get("DEEPGRAM_API_KEY", "")
        if not key:
            raise RuntimeError(
                "DEEPGRAM_API_KEY not set. Run 'scribe onboard' or set it in ~/.anyscribecli/.env"
            )
        return key

    def _build_params(self, language: str, diarize: bool) -> dict[str, str]:
        """Build query parameters for the Deepgram API."""
        model = "nova" if language.lower() in {"hi-latn"} else "nova-3"
        params: dict[str, str] = {
            "model": model,
            "smart_format": "true",
            "punctuate": "true",
        }
        if language != "auto":
            params["language"] = language
        if diarize:
            params["diarize"] = "true"
        return params

    def _transcribe_single(
        self, audio_path: Path, language: str, api_key: str, diarize: bool = False
    ) -> dict:
        """Transcribe a single audio file via Deepgram API."""
        with open(audio_path, "rb") as f:
            audio_data = f.read()

        params = self._build_params(language, diarize)

        response = httpx.post(
            self.API_URL,
            params=params,
            headers={
                "Authorization": f"Token {api_key}",
                "Content-Type": "audio/mpeg",
            },
            content=audio_data,
            timeout=300.0,
        )

        if response.status_code != 200:
            raise RuntimeError(f"Deepgram API error ({response.status_code}): {response.text}")
        return response.json()

    def transcribe(
        self, audio_path: Path, language: str = "auto", diarize: bool = False
    ) -> TranscriptResult:
        api_key = self._get_api_key()

        if not needs_chunking(audio_path):
            return self._parse_response(
                self._transcribe_single(audio_path, language, api_key, diarize=diarize),
                diarize=diarize,
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
                resp = self._transcribe_single(chunk_path, language, api_key, diarize=diarize)
                result = self._parse_response(resp, diarize=diarize)

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

    def _parse_response(self, data: dict, diarize: bool = False) -> TranscriptResult:
        """Parse Deepgram API response into TranscriptResult.

        Groups consecutive words by speaker into segments when diarized.
        Without diarization, groups words into natural segments.
        """
        channels = data.get("results", {}).get("channels", [])
        if not channels:
            return TranscriptResult(text="", language="unknown")

        alt = channels[0].get("alternatives", [{}])[0]
        full_text = alt.get("transcript", "")
        words = alt.get("words", [])
        detected_lang = alt.get("detected_language") or data.get("results", {}).get(
            "channels", [{}]
        )[0].get("detected_language", "unknown")

        # Calculate duration from last word
        duration = None
        if words:
            duration = words[-1].get("end", 0.0)

        segments: list[TranscriptSegment] = []

        if diarize and words:
            # Group consecutive words by speaker
            current_speaker: int | None = None
            current_words: list[str] = []
            block_start = 0.0
            block_end = 0.0
            seg_id = 0

            for word in words:
                speaker = word.get("speaker")
                punct_word = word.get("punctuated_word") or word.get("word", "")

                if speaker != current_speaker and current_words:
                    # Emit previous block
                    segments.append(
                        TranscriptSegment(
                            id=seg_id,
                            start=block_start,
                            end=block_end,
                            text=" ".join(current_words),
                            speaker=f"Speaker {current_speaker}"
                            if current_speaker is not None
                            else None,
                        )
                    )
                    seg_id += 1
                    current_words = []

                if not current_words:
                    block_start = word.get("start", 0.0)
                    current_speaker = speaker

                current_words.append(punct_word)
                block_end = word.get("end", block_start)

            # Emit final block
            if current_words:
                segments.append(
                    TranscriptSegment(
                        id=seg_id,
                        start=block_start,
                        end=block_end,
                        text=" ".join(current_words),
                        speaker=f"Speaker {current_speaker}"
                        if current_speaker is not None
                        else None,
                    )
                )
        elif words:
            # No diarization — group words into ~30-word segments for timestamps
            chunk_size = 30
            for i in range(0, len(words), chunk_size):
                chunk = words[i : i + chunk_size]
                text = " ".join(w.get("punctuated_word") or w.get("word", "") for w in chunk)
                segments.append(
                    TranscriptSegment(
                        id=len(segments),
                        start=chunk[0].get("start", 0.0),
                        end=chunk[-1].get("end", 0.0),
                        text=text,
                    )
                )

        return TranscriptResult(
            text=full_text,
            language=detected_lang,
            duration=duration,
            segments=segments,
        )
