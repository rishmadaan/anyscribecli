"""Abstract base for transcription providers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path


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

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name for display and config."""

    @abstractmethod
    def transcribe(
        self, audio_path: Path, language: str = "auto", diarize: bool = False
    ) -> TranscriptResult:
        """Transcribe an audio file. Returns structured result."""
