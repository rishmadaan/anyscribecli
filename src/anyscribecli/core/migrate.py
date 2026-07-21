"""Migrations for workspace and directory renames across versions."""

from __future__ import annotations

import re
import shutil
import time
from pathlib import Path

_app_home_migrated = False


def migrate_app_home_once() -> None:
    """Run ``maybe_migrate_app_home`` at most once per process.

    ``load_config``/``load_env``/``ensure_app_dirs`` call this on every
    invocation; without the flag they'd stat the filesystem each time.
    """
    global _app_home_migrated
    if _app_home_migrated:
        return
    _app_home_migrated = True
    maybe_migrate_app_home()


def maybe_migrate_app_home() -> bool:
    """Move ~/.anyscribecli/ to ~/.anyscribe/. Returns True if anything moved.

    Idempotent. Never overwrites: an entry already present in the new home
    wins and its legacy twin is left on disk untouched.
    """
    from anyscribecli.config.paths import APP_HOME, LEGACY_APP_HOME

    if not LEGACY_APP_HOME.is_dir():
        return False

    # ponytail: crude mtime guard — a recent write under the legacy tmp dir
    # means another process may be mid-transcription, so leave it alone.
    # A real lock file only if this ever bites.
    legacy_tmp = LEGACY_APP_HOME / "tmp"
    if legacy_tmp.is_dir():
        cutoff = time.time() - 300
        if any(p.stat().st_mtime > cutoff for p in legacy_tmp.rglob("*")):
            return False

    if not APP_HOME.exists():
        shutil.move(str(LEGACY_APP_HOME), str(APP_HOME))
        return True

    # New home already exists. If it holds real config, it's either already
    # migrated or a genuine new-style setup — don't touch either.
    if (APP_HOME / "config.yaml").exists() or (APP_HOME / ".env").exists():
        return False

    # Empty-ish new home, created by a post-upgrade command that ran before
    # the migration existed. Rescue every entry that doesn't collide.
    moved = 0
    for entry in sorted(LEGACY_APP_HOME.iterdir()):
        dest = APP_HOME / entry.name
        if dest.exists():
            continue
        shutil.move(str(entry), str(dest))
        moved += 1
    return moved > 0


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
