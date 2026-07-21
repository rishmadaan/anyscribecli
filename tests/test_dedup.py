"""Tests for core/dedup.py — duplicate transcript detection."""

from __future__ import annotations

from pathlib import Path

from anyscribe.core import dedup

URL = "https://www.youtube.com/watch?v=abc123"


def _make_transcript(ws: Path, source: str, name: str = "video.md") -> Path:
    out = ws / "sources" / "youtube" / name
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        "---\n"
        f"source: {source}\n"
        "platform: youtube\n"
        'title: "Some Video"\n'
        "word_count: 42\n"
        "---\n\n# Some Video\n"
    )
    return out


def test_finds_matching_source(tmp_path, monkeypatch):
    monkeypatch.setattr(dedup, "get_workspace_dir", lambda: tmp_path)
    existing = _make_transcript(tmp_path, URL)
    assert dedup.find_existing_transcript(URL) == existing


def test_no_match_returns_none(tmp_path, monkeypatch):
    monkeypatch.setattr(dedup, "get_workspace_dir", lambda: tmp_path)
    _make_transcript(tmp_path, URL)
    assert dedup.find_existing_transcript("https://youtu.be/other") is None


def test_missing_workspace_returns_none(tmp_path, monkeypatch):
    monkeypatch.setattr(dedup, "get_workspace_dir", lambda: tmp_path / "nope")
    assert dedup.find_existing_transcript(URL) is None


def test_malformed_frontmatter_is_skipped(tmp_path, monkeypatch):
    monkeypatch.setattr(dedup, "get_workspace_dir", lambda: tmp_path)
    bad = tmp_path / "sources" / "youtube" / "bad.md"
    bad.parent.mkdir(parents=True, exist_ok=True)
    bad.write_text(f"no frontmatter here\nsource: {URL}\n")  # source outside frontmatter
    assert dedup.find_existing_transcript(URL) is None


def test_index_files_are_ignored(tmp_path, monkeypatch):
    monkeypatch.setattr(dedup, "get_workspace_dir", lambda: tmp_path)
    _make_transcript(tmp_path, URL, name="_index.md")
    assert dedup.find_existing_transcript(URL) is None


def test_read_frontmatter(tmp_path, monkeypatch):
    monkeypatch.setattr(dedup, "get_workspace_dir", lambda: tmp_path)
    path = _make_transcript(tmp_path, URL)
    fm = dedup.read_frontmatter(path)
    assert fm["title"] == "Some Video"
    assert fm["word_count"] == 42


def test_read_frontmatter_malformed_returns_empty(tmp_path):
    path = tmp_path / "bad.md"
    path.write_text("just text")
    assert dedup.read_frontmatter(path) == {}
