"""Tests for `scribe batch --timeout` — per-URL timeout wrapping."""

from __future__ import annotations

import json
import time

from typer.testing import CliRunner

from anyscribecli.cli.main import app

runner = CliRunner()

URLS = "https://example.com/slow\nhttps://example.com/fast\n"


def _write_urls(tmp_path, content=URLS):
    f = tmp_path / "urls.txt"
    f.write_text(content)
    return f


def test_no_timeout_flag_skips_executor(tmp_path, monkeypatch):
    """Default behavior (no --timeout): process() is called directly, no wrapping."""
    import anyscribecli.core.orchestrator as orchestrator

    calls = []

    def fake_process(url, settings, quiet=False, force=False):
        calls.append(url)
        from anyscribecli.core.orchestrator import ProcessResult

        return ProcessResult(
            file_path=tmp_path / "out.md",
            title="T",
            platform="youtube",
            duration="1:00",
            language="en",
            word_count=2,
            provider="fake",
        )

    monkeypatch.setattr(orchestrator, "process", fake_process)

    urls_file = _write_urls(tmp_path)
    result = runner.invoke(app, ["batch", str(urls_file), "--json", "--quiet"])

    assert result.exit_code == 0
    data = json.loads(result.output)["data"]
    assert data["succeeded"] == 2
    assert len(calls) == 2


def test_timeout_marks_slow_url_failed_and_continues(tmp_path, monkeypatch):
    """A URL whose processing sleeps past --timeout is marked failed; batch continues."""
    import anyscribecli.core.orchestrator as orchestrator

    def fake_process(url, settings, quiet=False, force=False):
        from anyscribecli.core.orchestrator import ProcessResult

        if "slow" in url:
            time.sleep(2)  # exceeds the 0.1s timeout below
        return ProcessResult(
            file_path=tmp_path / "out.md",
            title="T",
            platform="youtube",
            duration="1:00",
            language="en",
            word_count=2,
            provider="fake",
        )

    monkeypatch.setattr(orchestrator, "process", fake_process)

    urls_file = _write_urls(tmp_path)
    result = runner.invoke(app, ["batch", str(urls_file), "--json", "--quiet", "--timeout", "0.1"])

    assert result.exit_code == 1  # one failure
    data = json.loads(result.output)["data"]
    assert data["succeeded"] == 1
    assert data["failed"] == 1
    failed = [r for r in data["results"] if not r["success"]][0]
    assert "timed out after" in failed["error"]
