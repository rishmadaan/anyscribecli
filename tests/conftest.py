"""Shared pytest setup."""

from __future__ import annotations

from pathlib import Path

import pytest

from anyscribe.config import paths, settings
from anyscribe.core import migrate


@pytest.fixture(autouse=True)
def _no_real_app_home_migration(monkeypatch):
    """Keep the app-home migration away from the real home dir during tests.

    ``load_config``/``load_env``/``ensure_app_dirs`` run it on first call, so
    any test touching them would otherwise move the actual legacy app home
    (``LEGACY_APP_HOME``) of whoever runs pytest, API keys and all.
    Pre-setting the once-flag makes it a no-op; the tests
    that exercise the migration reset the flag in their own fixture.
    """
    monkeypatch.setattr(migrate, "_app_home_migrated", True)


@pytest.fixture(autouse=True)
def _isolate_real_home(tmp_path_factory, monkeypatch):
    """Re-root every home-anchored path constant under a throwaway dir.

    ``paths``/``settings`` bind their constants at import time from
    ``Path.home()``, so a test that calls ``save_config``/``save_env`` without
    patching them writes into the real ~/.anyscribe of whoever runs pytest —
    which then blocks their genuine legacy migration and strands their keys.
    Tests that patch these constants themselves still win: autouse fixtures
    run before the test body.
    """
    fake_home = tmp_path_factory.mktemp("home")
    real_home = Path.home()
    for mod in (paths, settings):
        for name, value in list(vars(mod).items()):
            if isinstance(value, Path) and value != real_home and value.is_relative_to(real_home):
                monkeypatch.setattr(mod, name, fake_home / value.relative_to(real_home))
