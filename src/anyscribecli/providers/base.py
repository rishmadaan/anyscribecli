"""Abstract base for transcription providers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable


@dataclass
class TranscriptSegment:
    """A single segment of a transcript with timing info."""

    id: int
    start: float  # seconds
    end: float  # seconds
    text: str
    speaker: str | None = None  # speaker label (e.g. "Speaker 0")


@dataclass
class TranscriptResult:
    """Result of a transcription."""

    text: str
    language: str
    duration: float | None = None  # seconds
    segments: list[TranscriptSegment] = field(default_factory=list)
    word_count: int = 0

    def __post_init__(self) -> None:
        if self.word_count == 0 and self.text:
            self.word_count = len(self.text.split())


class TranscriptionProvider(ABC):
    """Base class for transcription API providers."""

    # Pinned model id set by get_provider(); None = provider's own default.
    model: str | None = None

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name for display and config."""

    @abstractmethod
    def transcribe(
        self, audio_path: Path, language: str = "auto", diarize: bool = False
    ) -> TranscriptResult:
        """Transcribe an audio file. Returns structured result."""

    def _transcribe_chunked(
        self,
        audio_path: Path,
        chunks: list[tuple[Path, float]],
        language: str,
        transcribe_chunk: Callable[[Path], TranscriptResult],
    ) -> TranscriptResult:
        """Shared chunk loop: checkpoint resume, overlap dedup, timestamp offsets.

        ``transcribe_chunk`` maps one chunk file to a chunk-local
        TranscriptResult (timestamps from 0; ids arbitrary — renumbered here).
        Chunk files are deleted as processed; ``audio_path`` itself never is.
        Checkpoint payload format matches pre-0.13.4 checkpoints exactly.
        """
        from anyscribecli.core.audio import deduplicate_overlap
        from anyscribecli.core.checkpoint import ChunkCheckpoint

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
                if chunk_path != audio_path:
                    chunk_path.unlink(missing_ok=True)
                continue
            try:
                result = transcribe_chunk(chunk_path)
                text = (
                    deduplicate_overlap(all_text_parts[-1], result.text)
                    if all_text_parts
                    else result.text
                )
                all_text_parts.append(text)
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
                ckpt.mark_completed(
                    i,
                    {
                        "text": result.text,
                        "language": result.language,
                        "duration": result.duration,
                        "segments": result.segments,
                    },
                )
                ckpt.save()
            finally:
                if chunk_path != audio_path:
                    chunk_path.unlink(missing_ok=True)

        ckpt.cleanup()
        full_text = " ".join(all_text_parts)
        return TranscriptResult(
            text=full_text,
            language=detected_language,
            duration=total_duration or None,
            segments=all_segments,
        )
