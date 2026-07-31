"""Smoke tests for the download command — guards against wiring breaks.

The v0.10.1 audit found `scribe download` crashed on every invocation because
it imported a function that had been renamed in transcribe.py. These tests
exercise the command far enough to catch that class of bug without hitting
the network.
"""

from __future__ import annotations

from typer.testing import CliRunner

from anyscribe.cli.main import app

runner = CliRunner()


def test_download_help():
    result = runner.invoke(app, ["download", "--help"])
    assert result.exit_code == 0


def test_download_imports_resolve():
    # Invoking with an invalid URL must get past the import block (line that
    # broke in 0.10.1) and fail with a validation error, not a NameError.
    result = runner.invoke(app, ["download", "not-a-url"])
    assert result.exit_code != 0
    assert "NameError" not in str(result.output)
    assert result.exception is None or not isinstance(result.exception, (NameError, ImportError))
