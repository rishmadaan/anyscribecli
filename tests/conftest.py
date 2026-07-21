"""Shared pytest setup."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Imported for side effect: the sweep below only re-roots modules already in
# sys.modules, so the ones that bind home paths at import time must be loaded
# before it runs. Without this a single-file run (e.g. pytest tests/test_web_
# onboarding.py) leaves them unloaded until the test body, past the fixture.
import anyscribe.cli.skill_cmd  # noqa: F401
import anyscribe.config.paths  # noqa: F401
import anyscribe.config.settings  # noqa: F401
import anyscribe.core.onboard_headless  # noqa: F401
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
    """Re-root module-level home-anchored ``Path`` constants under a throwaway dir.

    Modules bind constants like ``APP_HOME`` and ``CLAUDE_HOME`` at import time
    from ``Path.home()``, so a test that calls ``save_config``/``save_env`` or
    ``copy_skill_files`` without patching them writes into the real
    ~/.anyscribe or ~/.claude of whoever runs pytest — which then blocks their
    genuine legacy migration and strands their keys. Sweeping ``sys.modules``
    instead of a hand-maintained list means a new module cannot silently opt
    out of the isolation.

    Limits, stated plainly: this reaches only module-level ``Path`` attributes
    of ``anyscribe.*`` modules already imported when the fixture runs. A home
    path computed inside a function body, nested in a list/dict/dataclass, or
    living in a module first imported *during* the test body is NOT re-rooted —
    patch those in the test. Tests that patch these constants themselves still
    win: autouse fixtures run before the test body.
    """
    fake_home = tmp_path_factory.mktemp("home")
    real_home = Path.home()
    for mod in list(sys.modules.values()):
        if getattr(mod, "__name__", "").partition(".")[0] != "anyscribe":
            continue
        for name, value in list(vars(mod).items()):
            if isinstance(value, Path) and value != real_home and value.is_relative_to(real_home):
                monkeypatch.setattr(mod, name, fake_home / value.relative_to(real_home))
