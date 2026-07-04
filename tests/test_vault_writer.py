"""Tests for vault/writer.py — transcript writing, slugify, collisions."""

from __future__ import annotations

from pathlib import Path

import pytest

from anyscribecli.config.settings import Settings
from anyscribecli.downloaders.base import DownloadResult
from anyscribecli.providers.base import TranscriptResult, TranscriptSegment
from anyscribecli.vault.writer import slugify, write_transcript


def make_download(**overrides) -> DownloadResult:
    defaults = dict(
        audio_path=Path("/tmp/does-not-matter.mp3"),
        title="My Test Video",
        duration=90.0,
        platform="youtube",
        original_url="https://www.youtube.com/watch?v=abc123",
        channel="Some Channel",
    )
    defaults.update(overrides)
    return DownloadResult(**defaults)


def make_transcript(**overrides) -> TranscriptResult:
    defaults = dict(text="hello world this is a transcript", language="en")
    defaults.update(overrides)
    return TranscriptResult(**defaults)


def test_write_transcript_frontmatter_keys(tmp_path: Path) -> None:
    download = make_download()
    transcript = make_transcript()
    settings = Settings(provider="openai")

    out_path = write_transcript(download, transcript, settings, workspace=tmp_path)
    content = out_path.read_text()

    assert content.startswith("---\n")
    assert "source: https://www.youtube.com/watch?v=abc123" in content
    assert "platform: youtube" in content
    assert 'title: "My Test Video"' in content
    assert "language: en" in content
    assert "provider: openai" in content
    assert f"word_count: {transcript.word_count}" in content
    assert "- transcript" in content
    assert "- youtube" in content
    # diarize is False by default — key should be absent
    assert "diarized: true" not in content


def test_write_transcript_diarized_flag_in_frontmatter(tmp_path: Path) -> None:
    download = make_download()
    transcript = make_transcript()
    settings = Settings(diarize=True)

    out_path = write_transcript(download, transcript, settings, workspace=tmp_path)
    content = out_path.read_text()

    assert "diarized: true" in content


@pytest.mark.parametrize(
    "text, expected",
    [
        ("Hello World", "hello-world"),
        ("  spaces   everywhere  ", "spaces-everywhere"),
        ("Ünïcödé Tîtlé", "ünïcödé-tîtlé"),  # \w is unicode-aware — accented letters kept
        ("", ""),
        ("!!!", ""),
    ],
)
def test_slugify_edge_cases(text: str, expected: str) -> None:
    assert slugify(text) == expected


def test_slugify_emoji_strips_to_empty() -> None:
    # emoji are non-word chars under \w, so they're stripped entirely
    assert slugify("\U0001f600\U0001f601") == ""


def test_write_transcript_empty_title_falls_back_to_untitled(tmp_path: Path) -> None:
    """slugify('') == '' — writer.py falls back to the literal 'untitled' slug."""
    download = make_download(title="!!!")
    transcript = make_transcript()
    settings = Settings()

    out_path = write_transcript(download, transcript, settings, workspace=tmp_path)

    assert out_path.name == "untitled.md"


def test_write_transcript_slug_collision_appends_counter(tmp_path: Path) -> None:
    download = make_download(title="Same Title")
    transcript = make_transcript()
    settings = Settings()

    first = write_transcript(download, transcript, settings, workspace=tmp_path)
    second = write_transcript(download, transcript, settings, workspace=tmp_path)
    third = write_transcript(download, transcript, settings, workspace=tmp_path)

    assert first.name == "same-title.md"
    assert second.name == "same-title-2.md"
    assert third.name == "same-title-3.md"


def test_write_transcript_clean_format_has_plain_text_body(tmp_path: Path) -> None:
    segments = [
        TranscriptSegment(id=0, start=0.0, end=2.0, text="hello"),
        TranscriptSegment(id=1, start=2.0, end=4.0, text="world"),
    ]
    download = make_download()
    transcript = make_transcript(text="hello world", segments=segments)
    settings = Settings(output_format="clean")

    out_path = write_transcript(download, transcript, settings, workspace=tmp_path)
    content = out_path.read_text()

    assert "## Transcript\n\nhello world" in content
    assert "[00:00]" not in content


def test_write_transcript_timestamped_format(tmp_path: Path) -> None:
    segments = [
        TranscriptSegment(id=0, start=0.0, end=2.0, text="hello"),
        TranscriptSegment(id=1, start=65.0, end=68.0, text="world"),
    ]
    download = make_download()
    transcript = make_transcript(text="hello world", segments=segments)
    settings = Settings(output_format="timestamped")

    out_path = write_transcript(download, transcript, settings, workspace=tmp_path)
    content = out_path.read_text()

    assert "**[0:00]** hello" in content
    assert "**[1:05]** world" in content


def test_write_transcript_diarized_format_groups_by_speaker(tmp_path: Path) -> None:
    segments = [
        TranscriptSegment(id=0, start=0.0, end=2.0, text="hi there", speaker="Speaker 0"),
        TranscriptSegment(id=1, start=2.0, end=4.0, text="how are you", speaker="Speaker 0"),
        TranscriptSegment(id=2, start=5.0, end=7.0, text="good thanks", speaker="Speaker 1"),
    ]
    download = make_download()
    transcript = make_transcript(text="hi there how are you good thanks", segments=segments)
    settings = Settings(output_format="diarized")

    out_path = write_transcript(download, transcript, settings, workspace=tmp_path)
    content = out_path.read_text()

    assert "**Speaker 0** *[0:00]*: hi there how are you" in content
    assert "**Speaker 1** *[0:05]*: good thanks" in content


def test_write_transcript_diarized_format_without_speakers_falls_back_to_timestamped(
    tmp_path: Path,
) -> None:
    segments = [TranscriptSegment(id=0, start=0.0, end=2.0, text="no speaker data")]
    download = make_download()
    transcript = make_transcript(text="no speaker data", segments=segments)
    settings = Settings(output_format="diarized")

    out_path = write_transcript(download, transcript, settings, workspace=tmp_path)
    content = out_path.read_text()

    assert "**[0:00]** no speaker data" in content
