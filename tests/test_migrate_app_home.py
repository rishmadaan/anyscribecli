"""Tests for the legacy app home -> ~/.anyscribe app-home migration.

Real filesystem only: every case builds actual dirs/files under tmp_path and
asserts what ends up on disk.
"""

from __future__ import annotations

import os
import shutil
import time
from pathlib import Path

import pytest

from anyscribe.config import paths
from anyscribe.core import migrate
from anyscribe.core.migrate import maybe_migrate_app_home, migrate_app_home_once

# Captured before any fixture patches it, so the tests exercise the real
# legacy dir name without hardcoding the old package name here.
LEGACY_NAME = paths.LEGACY_APP_HOME.name


@pytest.fixture
def home(tmp_path, monkeypatch):
    """Point the app home constants at a throwaway home dir."""
    monkeypatch.setattr(Path, "home", staticmethod(lambda: tmp_path))
    # paths.py binds APP_HOME at import time, so patching Path.home alone
    # wouldn't reach the already-computed constants.
    monkeypatch.setattr(paths, "APP_HOME", tmp_path / ".anyscribe")
    monkeypatch.setattr(paths, "LEGACY_APP_HOME", tmp_path / LEGACY_NAME)
    monkeypatch.setattr(migrate, "_app_home_migrated", False)
    return tmp_path


def _legacy(home: Path) -> Path:
    return home / LEGACY_NAME


def _new(home: Path) -> Path:
    return home / ".anyscribe"


def _make_legacy(home: Path, **files: str) -> Path:
    legacy = _legacy(home)
    legacy.mkdir()
    for name, content in files.items():
        (legacy / name).write_text(content)
    return legacy


# --- decision table -------------------------------------------------------


def test_legacy_missing_returns_false(home):
    assert maybe_migrate_app_home() is False
    assert not _new(home).exists()


def test_legacy_is_a_file_returns_false(home):
    _legacy(home).write_text("not a directory")
    assert maybe_migrate_app_home() is False
    assert not _new(home).exists()


def test_legacy_exists_new_missing_moves_whole_dir(home):
    legacy = _make_legacy(home, **{"config.yaml": "provider: openai\n", ".env": "K=v\n"})
    (legacy / "logs").mkdir()
    (legacy / "logs" / "scribe.log").write_text("hello")

    assert maybe_migrate_app_home() is True

    new = _new(home)
    assert not legacy.exists()
    assert (new / "config.yaml").read_text() == "provider: openai\n"
    assert (new / ".env").read_text() == "K=v\n"
    assert (new / "logs" / "scribe.log").read_text() == "hello"


def test_empty_new_home_gets_legacy_entries_merged_in(home):
    # The trap this migration exists for: a first post-upgrade command created
    # an empty ~/.anyscribe, so a "target must be missing" guard would strand
    # the user's keys forever.
    legacy = _make_legacy(home, **{"config.yaml": "provider: deepgram\n", ".env": "DG=1\n"})
    new = _new(home)
    new.mkdir()
    (new / "logs").mkdir()  # created by ensure_app_dirs, no real config

    assert maybe_migrate_app_home() is True
    assert (new / "config.yaml").read_text() == "provider: deepgram\n"
    assert (new / ".env").read_text() == "DG=1\n"
    assert not (legacy / "config.yaml").exists()


def test_new_home_with_config_yaml_is_left_alone(home):
    _make_legacy(home, **{"config.yaml": "provider: openai\n"})
    new = _new(home)
    new.mkdir()
    (new / "config.yaml").write_text("provider: local\n")

    assert maybe_migrate_app_home() is False
    assert (new / "config.yaml").read_text() == "provider: local\n"
    assert (_legacy(home) / "config.yaml").read_text() == "provider: openai\n"


def test_new_home_with_env_only_is_left_alone(home):
    _make_legacy(home, **{".env": "OLD=1\n", "config.yaml": "provider: openai\n"})
    new = _new(home)
    new.mkdir()
    (new / ".env").write_text("NEW=1\n")

    assert maybe_migrate_app_home() is False
    assert (new / ".env").read_text() == "NEW=1\n"
    assert not (new / "config.yaml").exists()  # nothing pulled across
    assert (_legacy(home) / "config.yaml").exists()


# --- collision, mid-flight, idempotency -----------------------------------


def test_collision_target_wins_and_legacy_copy_survives(home):
    # Merge path (new home holds neither config.yaml nor .env) but one entry
    # name collides: the target's copy must win and the legacy file must NOT
    # be deleted.
    legacy = _make_legacy(home, **{"config.yaml": "provider: openai\n", ".env": "K=legacy\n"})
    new = _new(home)
    new.mkdir()
    (new / "logs").mkdir()
    (new / "logs" / "scribe.log").write_text("new log")
    (legacy / "logs").mkdir()
    (legacy / "logs" / "scribe.log").write_text("legacy log")

    assert maybe_migrate_app_home() is True

    assert (new / "logs" / "scribe.log").read_text() == "new log"
    assert (legacy / "logs" / "scribe.log").read_text() == "legacy log"  # not lost
    assert (new / "config.yaml").read_text() == "provider: openai\n"  # non-colliding moved


def test_mid_flight_tmp_file_blocks_migration(home):
    legacy = _make_legacy(home, **{"config.yaml": "provider: openai\n"})
    (legacy / "tmp").mkdir()
    (legacy / "tmp" / "chunk-000.mp3").write_bytes(b"audio")

    assert maybe_migrate_app_home() is False
    assert (legacy / "config.yaml").exists()
    assert not _new(home).exists()


def test_stale_tmp_file_does_not_block_migration(home):
    legacy = _make_legacy(home, **{"config.yaml": "provider: openai\n"})
    (legacy / "tmp").mkdir()
    stale = legacy / "tmp" / "chunk-000.mp3"
    stale.write_bytes(b"audio")
    old = time.time() - 3600
    os.utime(stale, (old, old))
    os.utime(legacy / "tmp", (old, old))

    assert maybe_migrate_app_home() is True
    assert (_new(home) / "config.yaml").exists()


def test_empty_tmp_dir_does_not_block_migration(home):
    legacy = _make_legacy(home, **{"config.yaml": "provider: openai\n"})
    (legacy / "tmp").mkdir()  # fresh mtime, but no files inside

    assert maybe_migrate_app_home() is True
    assert (_new(home) / "config.yaml").exists()


def test_idempotent_second_call_is_a_noop(home):
    _make_legacy(home, **{"config.yaml": "provider: openai\n"})

    assert maybe_migrate_app_home() is True
    assert maybe_migrate_app_home() is False
    assert (_new(home) / "config.yaml").read_text() == "provider: openai\n"


# --- once-per-process wrapper + choke points ------------------------------


def test_migrate_app_home_once_runs_only_once(home):
    _make_legacy(home, **{"config.yaml": "provider: openai\n"})
    migrate_app_home_once()
    assert (_new(home) / "config.yaml").exists()

    # Rebuild a state the migration *would* act on (legacy present, no new
    # home at all). Only the once-flag can stop the second call.
    shutil.rmtree(_new(home))
    _make_legacy(home, **{"stray": "x"})
    migrate_app_home_once()
    assert (_legacy(home) / "stray").exists()
    assert not _new(home).exists()


def test_os_error_fails_closed_with_one_line_and_no_traceback(home, capsys):
    """A deterministic failure must stop the process, not silently continue.

    Continuing would drop the user into an empty ~/.anyscribe and strand their
    keys in the legacy dir — the exact trap this migration exists to close.
    """
    _make_legacy(home, **{"config.yaml": "provider: openai\n"})
    _new(home).write_text("this is a file, not a directory")

    with pytest.raises(SystemExit) as exc:
        migrate_app_home_once()

    assert exc.value.code == 1
    err = capsys.readouterr().err
    assert "Traceback" not in err
    assert str(_new(home)) in err
    assert "anyscribe migrate" in err
    # Legacy dir untouched — nothing was half-moved.
    assert (_legacy(home) / "config.yaml").read_text() == "provider: openai\n"


@pytest.mark.parametrize("entrypoint", ["load_config", "load_env", "ensure_app_dirs"])
def test_choke_points_trigger_migration(home, monkeypatch, entrypoint):
    _make_legacy(home, **{"config.yaml": "provider: deepgram\n", ".env": "DG=1\n"})
    monkeypatch.setenv("DG", "")  # load_env writes to os.environ; keep it scoped
    new = _new(home)
    monkeypatch.setattr(paths, "LOGS_DIR", new / "logs")
    monkeypatch.setattr(paths, "SESSIONS_DIR", new / "sessions")
    monkeypatch.setattr(paths, "TMP_DIR", new / "tmp")

    if entrypoint == "ensure_app_dirs":
        paths.ensure_app_dirs()
    else:
        from anyscribe.config import settings

        monkeypatch.setattr(settings, "CONFIG_FILE", new / "config.yaml")
        monkeypatch.setattr(settings, "ENV_FILE", new / ".env")
        getattr(settings, entrypoint)()

    assert (new / "config.yaml").read_text() == "provider: deepgram\n"
    assert not _legacy(home).exists()
