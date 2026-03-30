"""Local model transcription provider.

Uses faster-whisper (CTranslate2-based Whisper) for offline transcription.
No API key needed, no internet required. Runs on CPU or GPU.

Install: pip install faster-whisper
"""

from __future__ import annotations

from pathlib import Path

from anyscribecli.providers.base import (
    TranscriptionProvider,
    TranscriptResult,
    TranscriptSegment,
)


# Available model sizes (smallest → largest)
LOCAL_MODELS = ["tiny", "base", "small", "medium", "large-v3"]
DEFAULT_MODEL = "base"


class LocalProvider(TranscriptionProvider):
    """Transcribe locally using faster-whisper.

    No API key, no internet. Models are downloaded on first use
    and cached at ~/.cache/huggingface/.
    """

    @property
    def name(self) -> str:
        return "local"

    def _get_model(self):
        """Load faster-whisper model. Downloads on first use."""
        try:
            from faster_whisper import WhisperModel
        except ImportError:
            raise RuntimeError(
                "faster-whisper is required for local transcription.\n"
                "Install it with: pip install faster-whisper\n\n"
                "Note: GPU acceleration requires CUDA. CPU works but is slower.\n"
                "For CPU-only: pip install faster-whisper"
            )

        import os

        model_size = os.environ.get("ASCLI_LOCAL_MODEL", DEFAULT_MODEL)
        if model_size not in LOCAL_MODELS:
            raise ValueError(f"Unknown model '{model_size}'. Available: {', '.join(LOCAL_MODELS)}")

        # Auto-detect compute type
        device = "cpu"
        compute_type = "int8"
        try:
            import torch

            if torch.cuda.is_available():
                device = "cuda"
                compute_type = "float16"
        except ImportError:
            pass

        return WhisperModel(model_size, device=device, compute_type=compute_type)

    def transcribe(self, audio_path: Path, language: str = "auto") -> TranscriptResult:
        model = self._get_model()

        kwargs = {}
        if language != "auto":
            kwargs["language"] = language

        segments_iter, info = model.transcribe(
            str(audio_path),
            beam_size=5,
            vad_filter=True,  # Skip silence for speed
            **kwargs,
        )

        segments: list[TranscriptSegment] = []
        text_parts: list[str] = []

        for i, seg in enumerate(segments_iter):
            segments.append(
                TranscriptSegment(
                    id=i,
                    start=seg.start,
                    end=seg.end,
                    text=seg.text.strip(),
                )
            )
            text_parts.append(seg.text.strip())

        full_text = " ".join(text_parts)
        return TranscriptResult(
            text=full_text,
            language=info.language or "unknown",
            duration=info.duration,
            segments=segments,
        )
