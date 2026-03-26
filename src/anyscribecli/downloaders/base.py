"""Abstract base for platform downloaders."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path


@dataclass
class DownloadResult:
    """Result of a media download."""

    audio_path: Path
    title: str
    duration: float | None  # seconds
    platform: str
    original_url: str
    channel: str = ""
    description: str = ""


class AbstractDownloader(ABC):
    """Base class for platform-specific downloaders."""

    @abstractmethod
    def can_handle(self, url: str) -> bool:
        """Return True if this downloader can handle the given URL."""

    @abstractmethod
    def download(self, url: str, output_dir: Path) -> DownloadResult:
        """Download audio from the URL to output_dir. Return metadata."""
