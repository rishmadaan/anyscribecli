"""Typer runner tests for the ``scribe local`` and ``scribe model`` groups.

All subprocess work (install, download, delete) is mocked — these tests
exercise flag parsing, exit codes, JSON output, and TTY/non-TTY gating.
"""

from __future__ import annotations

import json
from unittest.mock import patch

from typer.testing import CliRunner

from anyscribecli.cli.local_cmd import local_app
from anyscribecli.cli.models_cmd import models_app

runner = CliRunner()


# ── scribe local setup ────────────────────────────────


def test_setup_without_model_exits_2_with_json_error():
    result = runner.invoke(local_app, ["setup", "--json", "--yes"])
    assert result.exit_code == 2
    err = json.loads(result.stderr.strip().splitlines()[-1])
    assert err["error"] == "--model is required"
    assert err["recommended"] == "base"
    assert "tiny" in err["choices"]


def test_setup_with_invalid_model_exits_2():
    result = runner.invoke(local_app, ["setup", "--model", "huge", "--yes", "--json"])
    assert result.exit_code == 2
    err = json.loads(result.stderr.strip().splitlines()[-1])
    assert err["error"].startswith("unknown model")


def test_setup_without_yes_in_non_tty_exits_2():
    # CliRunner reports non-TTY, so --yes is required.
    result = runner.invoke(local_app, ["setup", "--model", "base", "--json"])
    assert result.exit_code == 2
    err = json.loads(result.stderr.strip().splitlines()[-1])
    assert "non-TTY" in err["error"]


def test_setup_already_set_up_is_noop():
    fake_status = {
        "faster_whisper_installed": True,
        "models": [{"size": "base", "cached": True, "bytes": 100, "repo": "r", "spec": {}}],
    }
    # load_config / save_config are imported lazily inside the command;
    # patch them at their definition site.
    with patch("anyscribecli.cli.local_cmd.check_status", return_value=fake_status):
        with patch("anyscribecli.config.settings.load_config") as load:
            with patch("anyscribecli.config.settings.save_config") as save:
                load.return_value = type("S", (), {"local_model": "base"})()
                result = runner.invoke(local_app, ["setup", "--model", "base", "--yes", "--json"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout.strip().splitlines()[-1])
    assert payload["status"] == "already_set_up"
    assert payload["size"] == "base"
    save.assert_not_called()


def test_setup_runs_run_setup_and_reports_set_up():
    fake_status = {
        "faster_whisper_installed": False,
        "models": [{"size": "base", "cached": False, "bytes": 0, "repo": "r", "spec": {}}],
    }
    setup_result = {
        "status": "set_up",
        "install": {"status": "installed", "method": "venv", "command": []},
        "model": {"size": "base", "bytes": 123, "status": "downloaded"},
        "default_model": "base",
    }
    with patch("anyscribecli.cli.local_cmd.check_status", return_value=fake_status):
        with patch("anyscribecli.cli.local_cmd.run_setup", return_value=setup_result) as run_setup:
            result = runner.invoke(local_app, ["setup", "--model", "base", "--yes", "--json"])
    assert result.exit_code == 0
    run_setup.assert_called_once()
    # Last NDJSON line carries the top-level outcome.
    final = json.loads(result.stdout.strip().splitlines()[-1])
    assert final["status"] == "set_up"


# ── scribe local status ───────────────────────────────


def test_status_is_always_exit_zero_and_safe_before_setup():
    with patch(
        "anyscribecli.cli.local_cmd.check_status",
        return_value={
            "set_up": False,
            "faster_whisper_installed": False,
            "faster_whisper_version": None,
            "ffmpeg_ok": True,
            "ffmpeg_message": "ffmpeg 6.1",
            "default_model": "base",
            "models": [],
            "total_disk_bytes": 0,
            "install_method": "venv",
        },
    ):
        result = runner.invoke(local_app, ["status", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert data["set_up"] is False
    assert data["default_model"] == "base"


# ── scribe local teardown ─────────────────────────────


def test_teardown_without_yes_in_non_tty_exits_2():
    result = runner.invoke(local_app, ["teardown", "--json"])
    assert result.exit_code == 2


def test_teardown_calls_run_teardown():
    with patch(
        "anyscribecli.cli.local_cmd.run_teardown",
        return_value={
            "status": "removed",
            "models_deleted": ["base"],
            "bytes_freed": 1000,
            "uninstall": {"status": "removed"},
            "provider_reset": False,
        },
    ) as t:
        result = runner.invoke(local_app, ["teardown", "--yes", "--json"])
    assert result.exit_code == 0
    t.assert_called_once()


# ── scribe model list ─────────────────────────────────


def test_model_list_json_shape():
    fake_entries = [
        {
            "size": "base",
            "repo": "r",
            "cached": False,
            "bytes": 0,
            "spec": {
                "download_mb": 145,
                "ram_mb": 600,
                "relative_speed": "fast",
                "quality": "good",
            },
        }
    ]
    with patch("anyscribecli.cli.models_cmd.list_cached_models", return_value=fake_entries):
        with patch("anyscribecli.cli.models_cmd.load_config") as load:
            load.return_value = type("S", (), {"local_model": "base"})()
            result = runner.invoke(models_app, ["list", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert data[0]["size"] == "base"
    assert data[0]["default"] is True


# ── scribe model pull ─────────────────────────────────


def test_model_pull_unknown_size_exits_2():
    result = runner.invoke(models_app, ["pull", "huge", "--json"])
    assert result.exit_code == 2


def test_model_pull_reports_missing_faster_whisper():
    with patch("anyscribecli.cli.models_cmd.faster_whisper_importable", return_value=False):
        result = runner.invoke(models_app, ["pull", "base", "--json"])
    assert result.exit_code == 2
    err = json.loads(result.stderr.strip().splitlines()[-1])
    assert "not set up" in err["error"]


def test_model_pull_already_present():
    with patch("anyscribecli.cli.models_cmd.faster_whisper_importable", return_value=True):
        with patch(
            "anyscribecli.cli.models_cmd.pull_model",
            return_value={
                "status": "already_present",
                "size": "base",
                "repo": "r",
                "bytes": 100,
            },
        ):
            result = runner.invoke(models_app, ["pull", "base", "--json"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["status"] == "already_present"


# ── scribe model rm ───────────────────────────────────


def test_model_rm_not_cached_is_noop():
    with patch("anyscribecli.cli.models_cmd.is_cached", return_value=False):
        result = runner.invoke(models_app, ["rm", "base", "--json"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["status"] == "not_present"


def test_model_rm_without_yes_in_non_tty_exits_2():
    with patch("anyscribecli.cli.models_cmd.is_cached", return_value=True):
        result = runner.invoke(models_app, ["rm", "base", "--json"])
    assert result.exit_code == 2


def test_model_rm_with_yes_calls_delete_model():
    with patch("anyscribecli.cli.models_cmd.is_cached", return_value=True):
        with patch(
            "anyscribecli.cli.models_cmd.delete_model",
            return_value={"status": "removed", "size": "base", "bytes_freed": 100},
        ) as d:
            result = runner.invoke(models_app, ["rm", "base", "--yes", "--json"])
    assert result.exit_code == 0
    d.assert_called_once_with("base")


# ── scribe model reinstall ────────────────────────────


def test_model_reinstall_unknown_size_exits_2():
    result = runner.invoke(models_app, ["reinstall", "huge", "--yes", "--json"])
    assert result.exit_code == 2
    err = json.loads(result.stderr.strip().splitlines()[-1])
    assert err["error"].startswith("unknown size")


def test_model_reinstall_without_faster_whisper_exits_2():
    with patch(
        "anyscribecli.cli.models_cmd.faster_whisper_importable", return_value=False
    ):
        result = runner.invoke(
            models_app, ["reinstall", "base", "--yes", "--json"]
        )
    assert result.exit_code == 2
    err = json.loads(result.stderr.strip().splitlines()[-1])
    assert err["error"] == "local transcription not set up"


def test_model_reinstall_without_yes_in_non_tty_exits_2():
    # CliRunner reports non-TTY; destructive ops must require --yes there.
    with patch(
        "anyscribecli.cli.models_cmd.faster_whisper_importable", return_value=True
    ):
        result = runner.invoke(models_app, ["reinstall", "base", "--json"])
    assert result.exit_code == 2


def test_model_reinstall_not_cached_returns_downloaded_only():
    pull_result = {
        "status": "downloaded",
        "size": "base",
        "repo": "r",
        "bytes": 300,
    }
    with patch(
        "anyscribecli.cli.models_cmd.faster_whisper_importable", return_value=True
    ):
        with patch("anyscribecli.cli.models_cmd.is_cached", return_value=False):
            with patch(
                "anyscribecli.cli.models_cmd.pull_model", return_value=pull_result
            ) as pull:
                with patch(
                    "anyscribecli.cli.models_cmd.delete_model"
                ) as delete:
                    result = runner.invoke(
                        models_app, ["reinstall", "base", "--yes", "--json"]
                    )
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["status"] == "downloaded_only"
    assert payload["bytes_freed"] == 0
    assert payload["bytes_downloaded"] == 300
    pull.assert_called_once_with("base")
    delete.assert_not_called()  # Nothing to delete when the size wasn't cached.


def test_model_reinstall_cached_deletes_then_pulls():
    delete_result = {"status": "removed", "size": "base", "bytes_freed": 150}
    pull_result = {
        "status": "downloaded",
        "size": "base",
        "repo": "r",
        "bytes": 300,
    }
    with patch(
        "anyscribecli.cli.models_cmd.faster_whisper_importable", return_value=True
    ):
        with patch("anyscribecli.cli.models_cmd.is_cached", return_value=True):
            with patch(
                "anyscribecli.cli.models_cmd.delete_model", return_value=delete_result
            ) as delete:
                with patch(
                    "anyscribecli.cli.models_cmd.pull_model", return_value=pull_result
                ) as pull:
                    result = runner.invoke(
                        models_app, ["reinstall", "base", "--yes", "--json"]
                    )
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["status"] == "reinstalled"
    assert payload["bytes_freed"] == 150
    assert payload["bytes_downloaded"] == 300
    delete.assert_called_once_with("base")
    pull.assert_called_once_with("base")


def test_model_reinstall_pull_failure_reports_bytes_freed():
    """When the delete succeeded but the subsequent pull blew up, the error
    payload carries the bytes we already freed so the caller can tell how
    much damage was done."""
    delete_result = {"status": "removed", "size": "base", "bytes_freed": 150}
    with patch(
        "anyscribecli.cli.models_cmd.faster_whisper_importable", return_value=True
    ):
        with patch("anyscribecli.cli.models_cmd.is_cached", return_value=True):
            with patch(
                "anyscribecli.cli.models_cmd.delete_model", return_value=delete_result
            ):
                with patch(
                    "anyscribecli.cli.models_cmd.pull_model",
                    side_effect=RuntimeError("network down"),
                ):
                    result = runner.invoke(
                        models_app, ["reinstall", "base", "--yes", "--json"]
                    )
    assert result.exit_code == 1
    err = json.loads(result.stderr.strip().splitlines()[-1])
    assert "network down" in err["error"]
    assert err["bytes_freed"] == 150
