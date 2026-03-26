"""URL detection and downloader dispatch."""

from __future__ import annotations

from anyscribecli.downloaders.base import AbstractDownloader
from anyscribecli.downloaders.youtube import YouTubeDownloader


def _load_downloaders() -> list[AbstractDownloader]:
    """Load all available downloaders. Instagram is optional (requires instaloader)."""
    downloaders: list[AbstractDownloader] = [
        YouTubeDownloader(),
    ]
    try:
        from anyscribecli.downloaders.instagram import InstagramDownloader
        downloaders.append(InstagramDownloader())
    except ImportError:
        pass  # instaloader not installed — Instagram support unavailable
    return downloaders


# Register all available downloaders. Order matters — first match wins.
DOWNLOADERS: list[AbstractDownloader] = _load_downloaders()


def detect_platform(url: str) -> str:
    """Detect which platform a URL belongs to. Raises ValueError if unknown."""
    for dl in DOWNLOADERS:
        if dl.can_handle(url):
            return dl.__class__.__name__.replace("Downloader", "").lower()
    raise ValueError(
        f"Unsupported URL: {url}\n"
        "Supported platforms: YouTube, Instagram"
    )


def get_downloader(url: str) -> AbstractDownloader:
    """Get the appropriate downloader for a URL."""
    for dl in DOWNLOADERS:
        if dl.can_handle(url):
            return dl
    raise ValueError(
        f"No downloader available for: {url}\n"
        "Supported platforms: YouTube, Instagram"
    )
