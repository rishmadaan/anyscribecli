"""Unit tests for the tray companion — no GUI, no real launchctl."""

from __future__ import annotations

import os
import subprocess

import pytest
from typer.testing import CliRunner

from anyscribecli.core import service, tray

runner = CliRunner()


# ---- pidfile -------------------------------------------------------------


def test_pidfile_roundtrip(monkeypatch, tmp_path):
    monkeypatch.setattr(tray, "PIDFILE", tmp_path / "tray.pid")
    assert tray.read_pidfile() is None
    tray.write_pidfile()
    assert tray.read_pidfile() == os.getpid()
    tray.remove_pidfile()
    assert tray.read_pidfile() is None


def test_pidfile_stale_pid_treated_as_absent(monkeypatch, tmp_path):
    pidfile = tmp_path / "tray.pid"
    pidfile.write_text("999999999")  # implausible / dead pid
    monkeypatch.setattr(tray, "PIDFILE", pidfile)
    assert tray.read_pidfile() is None


def test_pidfile_garbage_is_absent(monkeypatch, tmp_path):
    pidfile = tmp_path / "tray.pid"
    pidfile.write_text("not-a-pid")
    monkeypatch.setattr(tray, "PIDFILE", pidfile)
    assert tray.read_pidfile() is None


# ---- port probe ----------------------------------------------------------


def test_port_probe_free_port():
    # An almost-certainly-unbound port responds False.
    assert tray.port_responding(1, timeout=0.2) is False


def test_port_probe_bound_port():
    import socket

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", 0))
    s.listen()
    port = s.getsockname()[1]
    try:
        assert tray.port_responding(port, timeout=0.5) is True
    finally:
        s.close()


# ---- plist generation ----------------------------------------------------


def test_render_plist_contents():
    xml = service.render_plist(python="/usr/bin/python3")
    assert f"<string>{service.LABEL}</string>" in xml
    assert "<string>/usr/bin/python3</string>" in xml
    assert "<string>-m</string>" in xml
    assert "<string>anyscribecli</string>" in xml
    assert "<string>tray</string>" in xml
    assert "<key>RunAtLoad</key>" in xml


# ---- install / uninstall (no real launchctl) -----------------------------


@pytest.fixture
def fake_agents(monkeypatch, tmp_path):
    agents = tmp_path / "LaunchAgents"
    monkeypatch.setattr(service, "launch_agents_dir", lambda: agents)
    calls = []
    monkeypatch.setattr(service, "_launchctl", lambda *a: calls.append(a))
    return agents, calls


def test_install_writes_plist_and_loads(fake_agents):
    agents, calls = fake_agents
    path = service.install_service()
    assert path.exists()
    assert path.read_text().startswith("<?xml")
    assert ("load", str(path)) in calls


def test_uninstall_removes_and_unloads(fake_agents):
    agents, calls = fake_agents
    path = service.install_service()
    assert service.uninstall_service() is True
    assert not path.exists()
    assert ("unload", str(path)) in calls


def test_uninstall_when_absent(fake_agents):
    assert service.uninstall_service() is False


# ---- teardown (signal / quit / exception path) ----------------------------


class FakeProc:
    """Fake Popen: ignores /shutdown, exits only after terminate()."""

    def __init__(self):
        self.terminated = False
        self.killed = False

    def wait(self, timeout=None):
        if not self.terminated:
            raise subprocess.TimeoutExpired("scribe ui", timeout)
        return 0

    def terminate(self):
        self.terminated = True

    def kill(self):
        self.killed = True


def test_teardown_stops_owned_server_and_removes_pidfile(monkeypatch, tmp_path):
    from anyscribecli.cli import tray_cmd

    monkeypatch.setattr(tray, "PIDFILE", tmp_path / "tray.pid")
    tray.write_pidfile()
    proc = FakeProc()
    state = {"proc": proc}

    tray_cmd._teardown(state, port=1)  # port 1: /shutdown POST fails fast, ignored

    assert proc.terminated is True  # stop was requested (SIGTERM after POST failed)
    assert proc.killed is False  # exited after terminate, no SIGKILL needed
    assert "proc" not in state  # idempotent — second call won't re-stop
    assert not (tmp_path / "tray.pid").exists()


def test_teardown_leaves_attached_server_alone(monkeypatch, tmp_path):
    from anyscribecli.cli import tray_cmd

    monkeypatch.setattr(tray, "PIDFILE", tmp_path / "tray.pid")
    tray.write_pidfile()

    tray_cmd._teardown({"proc": None}, port=1)  # attached: we own nothing

    assert not (tmp_path / "tray.pid").exists()  # pidfile still cleaned up


# ---- missing-extra error path --------------------------------------------


def test_tray_missing_extra(monkeypatch):
    import builtins

    from anyscribecli.cli.main import app

    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "pystray" or name.startswith("PIL"):
            raise ImportError("no tray extra")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    result = runner.invoke(app, ["tray"])
    assert result.exit_code == 1
    assert "anyscribecli[tray]" in result.output


def test_install_service_non_macos(monkeypatch):
    from anyscribecli.cli.main import app

    monkeypatch.setattr("platform.system", lambda: "Linux")
    result = runner.invoke(app, ["install-service", "--yes"])
    assert result.exit_code == 1
    assert "macOS" in result.output
