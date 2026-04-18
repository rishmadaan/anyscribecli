"""Unit tests for the local-transcription provisioning engine.

Subprocess calls are mocked; these tests never actually run pip or pipx.
Integration-style coverage (live install + pull) lives behind the
``integration`` marker in ``test_local_models.py``.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from anyscribecli.core import local_setup


def test_detect_install_method_venv(monkeypatch):
    monkeypatch.setattr(local_setup.sys, "prefix", "/Users/foo/.venv")
    monkeypatch.setattr(local_setup.sys, "base_prefix", "/usr")
    monkeypatch.setattr(local_setup.sys, "executable", "/Users/foo/.venv/bin/python")
    monkeypatch.delenv("PIPX_HOME", raising=False)
    assert local_setup.detect_install_method() == "venv"


def test_detect_install_method_system(monkeypatch):
    monkeypatch.setattr(local_setup.sys, "prefix", "/usr")
    monkeypatch.setattr(local_setup.sys, "base_prefix", "/usr")
    monkeypatch.setattr(local_setup.sys, "executable", "/usr/bin/python3")
    monkeypatch.delenv("PIPX_HOME", raising=False)
    # Also neutralise the default pipx path so it's not accidentally a prefix.
    monkeypatch.setattr(local_setup.Path, "home", classmethod(lambda cls: Path("/nowhere")))
    assert local_setup.detect_install_method() == "system"


def test_install_command_uses_pipx_inject_for_pipx_method():
    with patch.object(local_setup, "detect_install_method", return_value="pipx"):
        with patch.object(local_setup, "_pipx_venv_name", return_value="anyscribecli"):
            cmd = local_setup._install_command("pipx")
    assert cmd == ["pipx", "inject", "anyscribecli", local_setup.FASTER_WHISPER_SPEC]


def test_install_command_uses_pip_for_venv_method():
    cmd = local_setup._install_command("venv")
    assert cmd[:3] == [local_setup.sys.executable, "-m", "pip"]
    assert cmd[-1] == local_setup.FASTER_WHISPER_SPEC


def test_install_is_noop_when_already_importable():
    with patch.object(local_setup, "faster_whisper_importable", return_value=True):
        with patch.object(local_setup, "faster_whisper_version", return_value="1.0.3"):
            result = local_setup.install_faster_whisper()
    assert result["status"] == "already_installed"
    assert result["version"] == "1.0.3"


def test_install_reports_failure_with_stderr():
    with patch.object(local_setup, "faster_whisper_importable", return_value=False):
        with patch.object(local_setup, "detect_install_method", return_value="venv"):
            with patch.object(local_setup, "_run", return_value=(1, "", "error: no permission")):
                result = local_setup.install_faster_whisper()
    assert result["status"] == "failed"
    assert result["stderr"] == "error: no permission"
    assert result["command"][:3] == [local_setup.sys.executable, "-m", "pip"]


def test_pipx_install_falls_back_when_pipx_not_on_path():
    with patch.object(local_setup, "faster_whisper_importable", return_value=False):
        with patch.object(local_setup, "detect_install_method", return_value="pipx"):
            with patch.object(local_setup.shutil, "which", return_value=None):
                with patch.object(local_setup, "_run", return_value=(0, "", "")) as run:
                    local_setup.install_faster_whisper()
    # After fallback, the actual command passed to _run is pip, not pipx.
    called_cmd = run.call_args.args[0]
    assert called_cmd[0] == local_setup.sys.executable
    assert "pip" in called_cmd
    assert local_setup.FASTER_WHISPER_SPEC in called_cmd


def test_check_status_reports_missing_faster_whisper(tmp_path, monkeypatch):
    with patch.object(local_setup, "faster_whisper_importable", return_value=False):
        status = local_setup.check_status()
    assert status["set_up"] is False
    assert status["faster_whisper_installed"] is False
    assert len(status["models"]) == len(local_setup.MODEL_SIZES)
    assert all(not m["cached"] for m in status["models"])


def test_local_ready_false_when_faster_whisper_missing():
    with patch.object(local_setup, "faster_whisper_importable", return_value=False):
        assert local_setup.local_ready() is False


def test_local_ready_false_when_no_models_cached():
    with patch.object(local_setup, "faster_whisper_importable", return_value=True):
        with patch.object(
            local_setup, "_ffmpeg_status", return_value={"ok": True, "message": "ok"}
        ):
            with patch.object(local_setup, "any_model_cached", return_value=False):
                assert local_setup.local_ready() is False


def test_run_setup_rejects_unknown_size():
    with pytest.raises(ValueError):
        local_setup.run_setup("huge")


def test_run_setup_short_circuits_when_already_installed_and_cached(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    # Fake install returns already_installed, fake pull returns already_present,
    # and save_config actually writes to tmp_path via settings.
    install_result = {
        "status": "already_installed",
        "method": "venv",
        "command": None,
        "version": "1.0.3",
    }
    pull_result = {
        "status": "already_present",
        "size": "base",
        "repo": "Systran/faster-whisper-base",
        "bytes": 100,
    }
    with patch.object(local_setup, "install_faster_whisper", return_value=install_result):
        with patch.object(local_setup, "pull_model", return_value=pull_result):
            with patch.object(local_setup, "save_config") as save:
                with patch.object(
                    local_setup,
                    "load_config",
                    return_value=type(
                        "S",
                        (),
                        {"local_model": "tiny"},
                    )(),
                ):
                    result = local_setup.run_setup("base")
    assert result["status"] == "set_up"
    assert result["default_model"] == "base"
    save.assert_called_once()
