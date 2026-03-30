"""Input detection and downloader dispatch."""

from __future__ import annotations

from anyscribecli.downloaders.base import AbstractDownloader
from anyscribecli.downloaders.local_file import LocalFileDownloader
from anyscribecli.downloaders.youtube import YouTubeDownloader
from anyscribecli.downloaders.instagram import InstagramDownloader

# Register all available downloaders. Order matters — first match wins.
# LocalFileDownloader is first so file paths are detected before URL patterns.
DOWNLOADERS: list[AbstractDownloader] = [
    LocalFileDownloader(),
    YouTubeDownloader(),
    InstagramDownloader(),
]


def detect_platform(url: str) -> str:
    """Detect which platform a URL or file path belongs to. Raises ValueError if unknown."""
    for dl in DOWNLOADERS:
        if dl.can_handle(url):
            return dl.__class__.__name__.replace("Downloader", "").lower()
    raise ValueError(
        f"Unsupported input: {url}\nSupported: local audio/video files, YouTube, Instagram"
    )


def get_downloader(url: str) -> AbstractDownloader:
    """Get the appropriate downloader for a URL or file path."""
    for dl in DOWNLOADERS:
        if dl.can_handle(url):
            return dl
    raise ValueError(
        f"No downloader available for: {url}\n"
        "Supported: local audio/video files, YouTube, Instagram"
    )
