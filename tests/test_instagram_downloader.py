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


from pathlib import Path
from unittest.mock import MagicMock, patch


@patch("anyscribecli.downloaders.instagram.load_config")
def test_build_ytdlp_args_no_browser_omits_cookies(
    mock_load_config: MagicMock, downloader: InstagramDownloader
) -> None:
    mock_settings = MagicMock()
    mock_settings.instagram.browser = ""
    mock_load_config.return_value = mock_settings

    args = downloader._build_ytdlp_cookie_args()

    assert args == []


@patch("anyscribecli.downloaders.instagram.load_config")
def test_build_ytdlp_args_with_browser_adds_cookies(
    mock_load_config: MagicMock, downloader: InstagramDownloader
) -> None:
    mock_settings = MagicMock()
    mock_settings.instagram.browser = "firefox"
    mock_load_config.return_value = mock_settings

    args = downloader._build_ytdlp_cookie_args()

    assert args == ["--cookies-from-browser", "firefox"]


@patch("anyscribecli.downloaders.instagram.subprocess.run")
@patch("anyscribecli.downloaders.instagram.load_config")
@patch("anyscribecli.downloaders.instagram.ensure_ytdlp_current")
def test_download_invokes_ytdlp_with_audio_flags(
    mock_ensure: MagicMock,
    mock_load_config: MagicMock,
    mock_run: MagicMock,
    downloader: InstagramDownloader,
    tmp_path: Path,
) -> None:
    """Sanity-check the shape of the yt-dlp invocation.

    Mocks subprocess so this test never touches the network. We only
    verify (a) metadata is fetched first via --dump-json, (b) audio
    download uses 16k mono 64k mp3 post-processor args matching Whisper
    optimization, (c) cookie args are passed through, and (d) the
    resulting mp3 is wrapped in a DownloadResult.
    """
    mock_settings = MagicMock()
    mock_settings.instagram.browser = "firefox"
    mock_load_config.return_value = mock_settings

    metadata = {
        "title": "Test Reel",
        "duration": 42.0,
        "uploader": "someuser",
        "description": "caption text",
    }
    import json as _json
    mock_run.side_effect = [
        MagicMock(returncode=0, stdout=_json.dumps(metadata), stderr=""),
        MagicMock(returncode=0, stdout="", stderr=""),
    ]

    audio_file = tmp_path / "ABC123.mp3"
    audio_file.write_bytes(b"fake mp3 bytes")

    result = downloader.download(
        "https://www.instagram.com/reel/ABC123/", tmp_path
    )

    assert mock_run.call_count == 2
    meta_args = mock_run.call_args_list[0].args[0]
    dl_args = mock_run.call_args_list[1].args[0]

    assert "--dump-json" in meta_args
    assert "--cookies-from-browser" in meta_args
    assert "firefox" in meta_args

    assert "--extract-audio" in dl_args
    assert "--audio-format" in dl_args and "mp3" in dl_args
    assert any("16000" in a and "64k" in a for a in dl_args)
    assert "--cookies-from-browser" in dl_args

    assert result.platform == "instagram"
    assert result.title == "Test Reel"
    assert result.duration == 42.0
    assert result.channel == "someuser"
    assert result.description == "caption text"
    assert result.audio_path == audio_file
