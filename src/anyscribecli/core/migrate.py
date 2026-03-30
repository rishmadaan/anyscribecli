"""Workspace migration — move legacy ~/.anyscribecli/workspace/ to ~/anyscribe."""

from __future__ import annotations

import shutil
from pathlib import Path


def maybe_migrate_workspace() -> Path | None:
    """If legacy workspace exists and new default doesn't, move it.

    Returns the new path if migrated, None otherwise.
    """
    from anyscribecli.config.paths import DEFAULT_WORKSPACE, LEGACY_WORKSPACE, get_workspace_dir

    target = get_workspace_dir()

    # Only migrate if:
    # 1. Target is the default (user hasn't set a custom path)
    # 2. Legacy workspace exists with content
    # 3. Target doesn't already exist
    if (
        target == DEFAULT_WORKSPACE
        and LEGACY_WORKSPACE.exists()
        and (LEGACY_WORKSPACE / "_index.md").exists()
        and not DEFAULT_WORKSPACE.exists()
    ):
        shutil.move(str(LEGACY_WORKSPACE), str(DEFAULT_WORKSPACE))
        return DEFAULT_WORKSPACE
    return None
