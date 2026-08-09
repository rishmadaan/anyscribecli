"""`anyscribe ui` port-conflict auto-retry."""

from __future__ import annotations

import socket

import pytest
from typer.testing import CliRunner

from anyscribe.cli.main import app

runner = CliRunner()


@pytest.fixture
def busy_port():
    """A port with a real listener on it, released after the test."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", 0))
    s.listen(1)
    yield s.getsockname()[1]
    s.close()


@pytest.fixture
def started(monkeypatch):
    """Record the port `ui` actually hands to the web server."""
    calls: list[int] = []
    monkeypatch.setattr(
        "anyscribe.web.app.run", lambda port, open_browser=True: calls.append(port)
    )
    return calls


def test_busy_port_rolls_forward_and_says_so(busy_port, started):
    result = runner.invoke(app, ["ui", "--port", str(busy_port), "--no-open"])
    assert result.exit_code == 0, result.output
    assert started and started[0] > busy_port
    assert f"Port {busy_port} busy — using {started[0]}" in result.output


def test_free_port_is_used_as_asked_with_no_notice(started):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", 0))
    free = s.getsockname()[1]
    s.close()
    result = runner.invoke(app, ["ui", "--port", str(free), "--no-open"])
    assert result.exit_code == 0, result.output
    assert started == [free]
    assert "busy" not in result.output


def test_exhausted_scan_errors_out_with_the_port_hint(busy_port, started, monkeypatch):
    # Span 0 = probe only the requested port, so one listener exhausts the scan.
    monkeypatch.setattr("anyscribe.cli.main.PORT_SCAN_SPAN", 0)
    result = runner.invoke(app, ["ui", "--port", str(busy_port), "--no-open"])
    assert result.exit_code == 1
    assert started == []
    assert f"Port {busy_port} is already in use." in result.output
    assert "anyscribe ui --port" in result.output
