"""Integration test for core/orchestrator.py — process() wiring + dedup."""

from __future__ import annotations

from pathlib import Path

import pytest

from anyscribe.config.settings import Settings
from anyscribe.downloaders.base import DownloadResult
from anyscribe.providers.base import TranscriptResult

URL = "https://www.youtube.com/watch?v=abc123"


class FakeDownloader:
    def __init__(self):
        self.calls = 0

    def download(self, url: str, output_dir: Path) -> DownloadResult:
        self.calls += 1
        audio = output_dir / "audio.mp3"
        audio.write_bytes(b"fake audio")
        return DownloadResult(
            audio_path=audio,
            title="Test Video",
            duration=60.0,
            platform="youtube",
            original_url=url,
        )


class FakeProvider:
    name = "fake"

    def transcribe(self, audio_path, language="auto", diarize=False):
        return TranscriptResult(text="hello world from the fake provider", language="en")


@pytest.fixture
def env(tmp_path, monkeypatch):
    """Isolated workspace + stubbed download/transcribe/migrations/preflight."""
    from anyscribe.core import dedup, migrate, orchestrator, preflight
    from anyscribe.vault import index, writer

    ws = tmp_path / "workspace"
    for mod in (dedup, writer, index):
        monkeypatch.setattr(mod, "get_workspace_dir", lambda: ws)
    monkeypatch.setattr(orchestrator, "TMP_DIR", tmp_path / "tmp")
    monkeypatch.setattr(orchestrator, "RECOVERY_DIR", tmp_path / "recovery")
    monkeypatch.setattr(migrate, "maybe_migrate_workspace", lambda: None)
    monkeypatch.setattr(migrate, "maybe_migrate_media_to_downloads", lambda: None)
    monkeypatch.setattr(migrate, "maybe_flatten_date_folders", lambda: 0)
    monkeypatch.setattr(preflight, "preflight_check", lambda settings, url: None)

    downloader = FakeDownloader()
    monkeypatch.setattr(orchestrator, "get_downloader", lambda url: downloader)
    monkeypatch.setattr(orchestrator, "get_provider", lambda name, model=None: FakeProvider())
    return ws, downloader


def test_process_dedup_and_force(env):
    from anyscribe.core.orchestrator import process

    ws, downloader = env
    settings = Settings()

    # 1. Happy path: file written + index updated
    r1 = process(URL, settings, quiet=True)
    assert r1.cached is False
    assert r1.file_path == ws / "sources" / "youtube" / "test-video.md"
    assert r1.file_path.exists()
    assert f"source: {URL}" in r1.file_path.read_text()
    assert r1.word_count == 6
    assert "test-video" in (ws / "_index.md").read_text()
    assert downloader.calls == 1

    # 2. Same URL again: cached, no download
    r2 = process(URL, settings, quiet=True)
    assert r2.cached is True
    assert r2.file_path == r1.file_path
    assert r2.title == "Test Video"
    assert r2.word_count == 6
    assert downloader.calls == 1

    # 3. force=True: re-transcribes
    r3 = process(URL, settings, quiet=True, force=True)
    assert r3.cached is False
    assert downloader.calls == 2
