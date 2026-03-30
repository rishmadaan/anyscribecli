"""Migrations for workspace and directory renames across versions."""

from __future__ import annotations

import re
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


def maybe_migrate_media_to_downloads() -> bool:
    """Rename ~/.anyscribecli/media/ to ~/.anyscribecli/downloads/.

    Returns True if migrated, False otherwise.
    """
    from anyscribecli.config.paths import DOWNLOADS_DIR, LEGACY_MEDIA_DIR

    if LEGACY_MEDIA_DIR.exists() and not DOWNLOADS_DIR.exists():
        shutil.move(str(LEGACY_MEDIA_DIR), str(DOWNLOADS_DIR))
        return True
    return False


_DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _flatten_dir(parent: Path) -> int:
    """Move files from YYYY-MM-DD subdirs up to their parent. Returns count moved."""
    moved = 0
    if not parent.is_dir():
        return 0

    for platform_dir in parent.iterdir():
        if not platform_dir.is_dir():
            continue
        for sub in list(platform_dir.iterdir()):
            if not sub.is_dir() or not _DATE_PATTERN.match(sub.name):
                continue
            # Move each file from the date subdir up to platform level
            for f in list(sub.iterdir()):
                dest = platform_dir / f.name
                # Handle collisions
                if dest.exists():
                    stem, suffix = f.stem, f.suffix
                    counter = 2
                    while dest.exists():
                        dest = platform_dir / f"{stem}-{counter}{suffix}"
                        counter += 1
                shutil.move(str(f), str(dest))
                moved += 1
            # Remove empty date dir
            if not any(sub.iterdir()):
                sub.rmdir()
    return moved


def maybe_flatten_date_folders() -> int:
    """Move files from date subdirs up to platform level. Returns count moved.

    Flattens:
    - workspace/sources/<platform>/YYYY-MM-DD/*.md → sources/<platform>/
    - downloads/audio/<platform>/YYYY-MM-DD/ → audio/<platform>/
    - downloads/video/<platform>/YYYY-MM-DD/ → video/<platform>/
    """
    from anyscribecli.config.paths import AUDIO_DIR, VIDEO_DIR, get_workspace_dir

    total = 0
    ws = get_workspace_dir()
    sources = ws / "sources"
    total += _flatten_dir(sources)
    total += _flatten_dir(AUDIO_DIR)
    total += _flatten_dir(VIDEO_DIR)
    return total
