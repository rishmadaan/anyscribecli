"""Tests for YouTubeDownloader — subprocess mocked, no network access."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from anyscribecli.downloaders.youtube import YouTubeDownloader


@pytest.fixture
def downloader() -> YouTubeDownloader:
    return YouTubeDownloader()


@pytest.mark.parametrize(
    "url",
    [
        "https://www.youtube.com/watch?v=abc123",
        "https://youtu.be/abc123",
        "https://www.youtube.com/shorts/abc123",
        "https://www.youtube.com/live/abc123",
    ],
)
def test_can_handle_youtube_urls(downloader: YouTubeDownloader, url: str) -> None:
    assert downloader.can_handle(url) is True


@pytest.mark.parametrize(
    "url",
    [
        "https://www.instagram.com/p/ABC123/",
        "https://twitter.com/user/status/123",
        "not a url at all",
        "",
    ],
)
def test_rejects_non_youtube_urls(downloader: YouTubeDownloader, url: str) -> None:
    assert downloader.can_handle(url) is False


@patch("anyscribecli.downloaders.youtube.subprocess.run")
@patch("anyscribecli.core.deps.ensure_ytdlp_current")
def test_download_success_parses_metadata(
    mock_ensure: MagicMock, mock_run: MagicMock, downloader: YouTubeDownloader, tmp_path: Path
) -> None:
    metadata = {
        "title": "Test Video",
        "id": "abc123",
        "duration": 125.0,
        "channel": "Some Channel",
        "description": "a description",
    }
    mock_run.side_effect = [
        MagicMock(returncode=0, stdout=json.dumps(metadata), stderr=""),
        MagicMock(returncode=0, stdout="", stderr=""),
    ]

    audio_file = tmp_path / "Test Video.mp3"
    audio_file.write_bytes(b"fake mp3 bytes")

    result = downloader.download("https://www.youtube.com/watch?v=abc123", tmp_path)

    assert result.platform == "youtube"
    assert result.title == "Test Video"
    assert result.duration == 125.0
    assert result.channel == "Some Channel"
    assert result.description == "a description"
    assert result.audio_path == audio_file
    assert result.original_url == "https://www.youtube.com/watch?v=abc123"


@patch("anyscribecli.downloaders.youtube.subprocess.run")
@patch("anyscribecli.core.deps.ensure_ytdlp_current")
def test_download_metadata_failure_raises_runtime_error(
    mock_ensure: MagicMock, mock_run: MagicMock, downloader: YouTubeDownloader, tmp_path: Path
) -> None:
    mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="ERROR: video unavailable")

    with pytest.raises(RuntimeError, match="yt-dlp metadata failed"):
        downloader.download("https://www.youtube.com/watch?v=abc123", tmp_path)


@patch("anyscribecli.downloaders.youtube.subprocess.run")
@patch("anyscribecli.core.deps.ensure_ytdlp_current")
def test_download_audio_extraction_failure_raises_runtime_error(
    mock_ensure: MagicMock, mock_run: MagicMock, downloader: YouTubeDownloader, tmp_path: Path
) -> None:
    metadata = {"title": "Test Video", "duration": 10.0}
    mock_run.side_effect = [
        MagicMock(returncode=0, stdout=json.dumps(metadata), stderr=""),
        MagicMock(returncode=1, stdout="", stderr="ERROR: postprocessing failed"),
    ]

    with pytest.raises(RuntimeError, match="yt-dlp download failed"):
        downloader.download("https://www.youtube.com/watch?v=abc123", tmp_path)


@patch("anyscribecli.downloaders.youtube.subprocess.run")
@patch("anyscribecli.core.deps.ensure_ytdlp_current")
def test_download_no_mp3_found_raises_runtime_error(
    mock_ensure: MagicMock, mock_run: MagicMock, downloader: YouTubeDownloader, tmp_path: Path
) -> None:
    metadata = {"title": "Test Video", "duration": 10.0}
    mock_run.side_effect = [
        MagicMock(returncode=0, stdout=json.dumps(metadata), stderr=""),
        MagicMock(returncode=0, stdout="", stderr=""),
    ]

    with pytest.raises(RuntimeError, match="no mp3 file found"):
        downloader.download("https://www.youtube.com/watch?v=abc123", tmp_path)


@patch("anyscribecli.downloaders.youtube.subprocess.run")
@patch("anyscribecli.core.deps.ensure_ytdlp_current")
def test_download_invokes_ytdlp_with_expected_flags(
    mock_ensure: MagicMock, mock_run: MagicMock, downloader: YouTubeDownloader, tmp_path: Path
) -> None:
    """Verify subprocess invocations use get_command() and expected yt-dlp flags."""
    metadata = {"title": "Test Video", "duration": 10.0}
    mock_run.side_effect = [
        MagicMock(returncode=0, stdout=json.dumps(metadata), stderr=""),
        MagicMock(returncode=0, stdout="", stderr=""),
    ]
    (tmp_path / "Test Video.mp3").write_bytes(b"fake mp3 bytes")

    downloader.download("https://www.youtube.com/watch?v=abc123", tmp_path)

    expected_prefix = [sys.executable, "-m", "yt_dlp"]

    meta_args = mock_run.call_args_list[0].args[0]
    dl_args = mock_run.call_args_list[1].args[0]

    assert meta_args[:3] == expected_prefix
    assert "--dump-json" in meta_args
    assert "--no-download" in meta_args

    assert dl_args[:3] == expected_prefix
    assert "--extract-audio" in dl_args
    assert "--audio-format" in dl_args and "mp3" in dl_args
    assert any("16000" in a and "64k" in a for a in dl_args)
    assert "--output" in dl_args
    assert "--no-playlist" in dl_args
    assert "--no-overwrites" in dl_args
