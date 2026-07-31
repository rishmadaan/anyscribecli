"""Local model transcription provider.

Uses faster-whisper (CTranslate2-based Whisper) for offline transcription.
No API key needed, no internet required. Runs on CPU or GPU.

Set up via ``scribe local setup --model <size>`` (CLI), the "Set up local
transcription" button in the Web UI, or the opt-in step in ``scribe onboard``.
"""

from __future__ import annotations

from pathlib import Path

from anyscribe.providers.base import (
    TranscriptionProvider,
    TranscriptResult,
    TranscriptSegment,
)
from anyscribe.providers.local_models import MODEL_SIZES, RECOMMENDED_MODEL


def _resolve_model_size() -> str:
    """Pick the model size for this transcription.

    Precedence: ASCLI_LOCAL_MODEL env var (power-user override) → settings.local_model
    (user-chosen default) → RECOMMENDED_MODEL (safety net if config is empty).
    """
    import os

    env_override = os.environ.get("ASCLI_LOCAL_MODEL")
    if env_override:
        return env_override

    try:
        from anyscribe.config.settings import load_config

        size = load_config().local_model
        if size:
            return size
    except Exception:
        pass

    return RECOMMENDED_MODEL


class LocalProvider(TranscriptionProvider):
    """Transcribe locally using faster-whisper.

    No API key, no internet. Weights live in the HuggingFace cache
    (``~/.cache/huggingface/hub/``) after ``scribe local setup``.
    """

    @property
    def name(self) -> str:
        return "local"

    def _get_model(self):
        """Load faster-whisper model using the configured size."""
        try:
            from faster_whisper import WhisperModel
        except ImportError:
            raise RuntimeError(
                "faster-whisper is not installed. Run "
                "`scribe local setup --model base` to install it and pull a model."
            )

        model_size = _resolve_model_size()
        if model_size not in MODEL_SIZES:
            raise ValueError(f"Unknown model '{model_size}'. Available: {', '.join(MODEL_SIZES)}")

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

        # Load by HF repo id, not size alias — newer sizes (large-v3-turbo,
        # distil-large-v3.5) aren't in every faster-whisper alias table, and the
        # repo id hits the exact cache entry `scribe model pull` downloaded.
        from anyscribe.providers.local_models import MODEL_REPOS

        return WhisperModel(MODEL_REPOS[model_size], device=device, compute_type=compute_type)

    def transcribe(
        self, audio_path: Path, language: str = "auto", diarize: bool = False
    ) -> TranscriptResult:
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
