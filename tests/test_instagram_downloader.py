"""Tests for InstagramDownloader URL handling.

These tests pin behavior that must not regress across the instaloader→yt-dlp
migration: pattern matching and shortcode extraction. Network is never touched.
"""

from __future__ import annotations

import pytest

from anyscribecli.downloaders.instagram import InstagramDownloader


@pytest.fixture
def downloader() -> InstagramDownloader:
    return InstagramDownloader()


@pytest.mark.parametrize(
    "url",
    [
        "https://www.instagram.com/p/ABC123/",
        "https://instagram.com/p/ABC123",
        "https://www.instagram.com/reel/XYZ789/",
        "https://www.instagram.com/someuser/p/ABC123/",
        "https://www.instagram.com/someuser/reel/XYZ789/",
    ],
)
def test_can_handle_instagram_urls(downloader: InstagramDownloader, url: str) -> None:
    assert downloader.can_handle(url) is True


@pytest.mark.parametrize(
    "url",
    [
        "https://www.youtube.com/watch?v=abc",
        "https://twitter.com/user/status/123",
        "https://www.instagram.com/someuser/",  # profile, not a post/reel
        "not a url at all",
        "",
    ],
)
def test_rejects_non_instagram_post_urls(
    downloader: InstagramDownloader, url: str
) -> None:
    assert downloader.can_handle(url) is False


@pytest.mark.parametrize(
    "url, expected",
    [
        ("https://www.instagram.com/p/ABC123/", "ABC123"),
        ("https://www.instagram.com/p/ABC123", "ABC123"),
        ("https://www.instagram.com/reel/XYZ789/", "XYZ789"),
        ("https://www.instagram.com/reel/XYZ789?igsh=foo", "XYZ789"),
        ("https://www.instagram.com/someuser/p/ABC123/", "ABC123"),
        ("https://www.instagram.com/someuser/reel/XYZ789/", "XYZ789"),
    ],
)
def test_extract_shortcode(
    downloader: InstagramDownloader, url: str, expected: str
) -> None:
    assert downloader._extract_shortcode(url) == expected


def test_extract_shortcode_raises_on_bad_url(
    downloader: InstagramDownloader,
) -> None:
    with pytest.raises(ValueError, match="Could not extract shortcode"):
        downloader._extract_shortcode("https://example.com/foo")
