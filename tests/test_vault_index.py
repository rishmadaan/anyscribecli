"""Tests for vault/index.py path resolution."""

from __future__ import annotations


def test_find_transcript_absolute_missing_path_returns_empty(tmp_path):
    # rglob rejects absolute patterns — a deleted file's absolute path must
    # return no matches, not crash (regression: NotImplementedError on rm).
    from anyscribecli.vault.index import find_transcript

    missing = tmp_path / "nope" / "gone.md"
    assert find_transcript(str(missing), workspace=tmp_path) == []


def test_find_transcript_slug_still_globs(tmp_path):
    from anyscribecli.vault.index import find_transcript

    f = tmp_path / "sources" / "local" / "my-clip.md"
    f.parent.mkdir(parents=True)
    f.write_text("x")
    assert find_transcript("my-clip", workspace=tmp_path) == [f]
