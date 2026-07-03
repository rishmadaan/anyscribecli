"""Tests for transcript deletion — vault helper, index resync, web endpoint."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from anyscribecli.config.settings import Settings
from anyscribecli.downloaders.base import DownloadResult
from anyscribecli.providers.base import TranscriptResult
from anyscribecli.vault.index import delete_transcript, update_indexes
from anyscribecli.vault.writer import write_transcript


def _make_transcript(ws: Path, title: str) -> Path:
    """Create a real transcript + index entry using the vault functions."""
    download = DownloadResult(
        audio_path=ws / "fake.mp3",  # never touched (keep_media=False)
        title=title,
        duration=60.0,
        platform="youtube",
        original_url=f"https://youtube.com/watch?v={title}",
    )
    transcript = TranscriptResult(text="hello world", language="en")
    path = write_transcript(download, transcript, Settings(), workspace=ws)
    update_indexes(path, download, workspace=ws)
    return path


class TestVaultDelete:
    def test_delete_removes_file_and_index_row(self, tmp_path):
        keep = _make_transcript(tmp_path, "Keep Me")
        gone = _make_transcript(tmp_path, "Delete Me")
        index = tmp_path / "_index.md"
        assert "Delete Me" in index.read_text()

        delete_transcript(gone, workspace=tmp_path)

        assert not gone.exists()
        assert keep.exists()
        content = index.read_text()
        assert "Delete Me" not in content
        assert "Keep Me" in content

    def test_daily_log_untouched(self, tmp_path):
        gone = _make_transcript(tmp_path, "Delete Me")
        daily = list((tmp_path / "daily").glob("*.md"))[0]
        before = daily.read_text()

        delete_transcript(gone, workspace=tmp_path)

        assert daily.read_text() == before

    def test_rejects_path_outside_workspace(self, tmp_path):
        with pytest.raises(ValueError):
            delete_transcript(
                tmp_path / "sources" / ".." / ".." / "etc" / "passwd", workspace=tmp_path
            )
        with pytest.raises(ValueError):
            delete_transcript(Path("/etc/passwd"), workspace=tmp_path)

    def test_missing_file_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            delete_transcript(tmp_path / "sources" / "youtube" / "nope.md", workspace=tmp_path)


class TestWebDelete:
    @pytest.fixture
    def client(self, tmp_path, monkeypatch):
        import anyscribecli.vault.index as vault_index
        import anyscribecli.web.routes.history as history

        monkeypatch.setattr(history, "get_workspace_dir", lambda: tmp_path)
        monkeypatch.setattr(vault_index, "get_workspace_dir", lambda: tmp_path)

        from anyscribecli.web.app import create_app

        return TestClient(create_app())

    def test_delete_transcript(self, client, tmp_path):
        path = _make_transcript(tmp_path, "Web Delete Me")

        r = client.delete(f"/api/transcripts/{path.stem}")

        assert r.status_code == 200
        assert r.json()["success"] is True
        assert not path.exists()
        assert "Web Delete Me" not in (tmp_path / "_index.md").read_text()

    def test_delete_not_found(self, client, tmp_path):
        _make_transcript(tmp_path, "Something")
        r = client.delete("/api/transcripts/does-not-exist")
        assert r.status_code == 404

    def test_delete_no_sources_dir(self, client):
        r = client.delete("/api/transcripts/anything")
        assert r.status_code == 404
