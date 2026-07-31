"""Tests for `scribe logs` — viewer over daily processing logs + recovery artifacts."""

from __future__ import annotations

import json

from typer.testing import CliRunner

from anyscribe.cli.main import app

runner = CliRunner()


def _write_daily_log(ws, date: str, rows: list[tuple[str, str, str, str]]) -> None:
    daily_dir = ws / "daily"
    daily_dir.mkdir(parents=True, exist_ok=True)
    lines = [
        f"# Processing Log — {date}",
        "",
        "| Time | Platform | Entry | Duration |",
        "|------|----------|-------|----------|",
    ]
    for time, platform, entry, duration in rows:
        lines.append(f"| {time} | {platform} | {entry} | {duration} |")
    (daily_dir / f"{date}.md").write_text("\n".join(lines) + "\n")


def _patch_workspace(monkeypatch, tmp_path):
    import anyscribe.cli.logs_cmd as logs_cmd

    ws = tmp_path / "workspace"
    monkeypatch.setattr(logs_cmd, "get_workspace_dir", lambda: ws)
    monkeypatch.setattr(logs_cmd, "RECOVERY_DIR", tmp_path / "recovery")
    return ws


def test_empty_state(tmp_path, monkeypatch):
    _patch_workspace(monkeypatch, tmp_path)
    result = runner.invoke(app, ["logs"])
    assert result.exit_code == 0
    assert "No activity logged yet." in result.output


def test_empty_state_json(tmp_path, monkeypatch):
    _patch_workspace(monkeypatch, tmp_path)
    result = runner.invoke(app, ["logs", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["success"] is True
    assert data["data"]["entries"] == []
    assert data["data"]["recovery"] == []


def test_default_shows_recent_entries_newest_first(tmp_path, monkeypatch):
    ws = _patch_workspace(monkeypatch, tmp_path)
    _write_daily_log(ws, "2026-07-01", [("09:00", "youtube", "[[a|Video A]]", "1:00")])
    _write_daily_log(ws, "2026-07-02", [("10:00", "instagram", "[[b|Video B]]", "2:00")])

    result = runner.invoke(app, ["logs"])
    assert result.exit_code == 0
    # newest date first
    assert result.output.index("2026-07-02") < result.output.index("2026-07-01")
    assert "Video A" in result.output
    assert "Video B" in result.output


def test_limit_flag(tmp_path, monkeypatch):
    ws = _patch_workspace(monkeypatch, tmp_path)
    rows = [(f"{h:02d}:00", "youtube", f"[[e{h}|Entry {h}]]", "1:00") for h in range(5)]
    _write_daily_log(ws, "2026-07-01", rows)

    result = runner.invoke(app, ["logs", "--limit", "2", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert len(data["data"]["entries"]) == 2


def test_recovery_artifacts_listed(tmp_path, monkeypatch):
    _patch_workspace(monkeypatch, tmp_path)
    recovery_dir = tmp_path / "recovery" / "tmp123"
    recovery_dir.mkdir(parents=True)
    (recovery_dir / "audio.mp3").write_bytes(b"x" * 1024)

    result = runner.invoke(app, ["logs", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert len(data["data"]["recovery"]) == 1
    entry = data["data"]["recovery"][0]
    assert entry["name"] == "tmp123/audio.mp3"
    assert entry["size"] == 1024

    # Non-JSON output includes a hint about what recovery files are.
    result = runner.invoke(app, ["logs"])
    assert "audio.mp3" in result.output
    assert "recovery" in result.output.lower()
