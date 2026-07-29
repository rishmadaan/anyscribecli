"""Canary: the conftest HOME isolation must hold for the whole suite."""

from __future__ import annotations

import os
from pathlib import Path


def test_home_isolation_canary():
    from anyscribecli.config.paths import APP_HOME, CONFIG_FILE
    from anyscribecli.config.settings import CONFIG_FILE as SETTINGS_CONFIG_FILE

    assert str(Path.home()).startswith("/") and "ascli-test-home-" in str(Path.home())
    assert str(APP_HOME).startswith(str(Path.home()))
    assert str(CONFIG_FILE).startswith(str(Path.home()))
    assert str(SETTINGS_CONFIG_FILE).startswith(str(Path.home()))
    assert os.environ["HOME"] == str(Path.home())
