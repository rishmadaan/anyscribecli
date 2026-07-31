"""Autostart route — macOS-only launchd toggle, honest 400 elsewhere."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

import anyscribe.web.routes.system as system_routes
from anyscribe.core import service
from anyscribe.web.app import create_app


@pytest.fixture
def client():
    return TestClient(create_app())


def test_autostart_status_reports_supported(client, monkeypatch, tmp_path):
    monkeypatch.setattr(system_routes.sys, "platform", "darwin")
    monkeypatch.setattr(service, "launch_agents_dir", lambda: tmp_path)
    data = client.get("/api/autostart").json()
    assert data == {"supported": True, "enabled": False}


def test_autostart_enable_writes_plist(client, monkeypatch, tmp_path):
    monkeypatch.setattr(system_routes.sys, "platform", "darwin")
    monkeypatch.setattr(service, "launch_agents_dir", lambda: tmp_path)
    monkeypatch.setattr(service, "_launchctl", lambda *a: None)
    monkeypatch.setattr(system_routes, "find_spec", lambda name: object())
    data = client.put("/api/autostart", json={"enabled": True}).json()
    assert data["enabled"] is True
    assert (tmp_path / "com.anyscribe.tray.plist").exists()
    # and off again
    data = client.put("/api/autostart", json={"enabled": False}).json()
    assert data["enabled"] is False
    assert not (tmp_path / "com.anyscribe.tray.plist").exists()


def test_autostart_enable_refused_without_tray(client, monkeypatch, tmp_path):
    """No pystray → no plist. A LaunchAgent that can't run is worse than none."""
    monkeypatch.setattr(system_routes.sys, "platform", "darwin")
    monkeypatch.setattr(service, "launch_agents_dir", lambda: tmp_path)
    monkeypatch.setattr(service, "_launchctl", lambda *a: None)
    monkeypatch.setattr(system_routes, "find_spec", lambda name: None)
    r = client.put("/api/autostart", json={"enabled": True})
    assert r.status_code == 400
    assert "anyscribe[tray]" in r.json()["detail"]
    assert not (tmp_path / "com.anyscribe.tray.plist").exists()


def test_autostart_rejected_off_macos(client, monkeypatch):
    monkeypatch.setattr(system_routes.sys, "platform", "linux")
    assert client.put("/api/autostart", json={"enabled": True}).status_code == 400
    assert client.get("/api/autostart").json() == {"supported": False, "enabled": False}
