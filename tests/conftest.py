"""Shared pytest setup."""

from __future__ import annotations

import pytest

from anyscribecli.core import migrate


@pytest.fixture(autouse=True)
def _no_real_app_home_migration(monkeypatch):
    """Keep the app-home migration away from the real home dir during tests.

    ``load_config``/``load_env``/``ensure_app_dirs`` run it on first call, so
    any test touching them would otherwise move the actual ~/.anyscribecli of
    whoever runs pytest. Pre-setting the once-flag makes it a no-op; the tests
    that exercise the migration reset the flag in their own fixture.
    """
    monkeypatch.setattr(migrate, "_app_home_migrated", True)
