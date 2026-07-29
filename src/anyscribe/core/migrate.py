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
    invocation; without the flag they'd stat the filesystem each time. Those
    three are the only choke points, so the failure handling lives here rather
    than in each caller.

    On OSError we fail CLOSED: one actionable line, no traceback, exit 1.
    Do NOT soften this to a warning-and-continue. If the move fails and we
    carry on, the user lands in an empty ~/.anyscribe, re-onboards into it,
    and their existing keys are stranded in the legacy dir — the exact trap
    this migration exists to close. Better to stop and be told why.

    The flag is armed by SUCCESS, not by the attempt: a SystemExit raised on a
    web worker thread is swallowed by the Future, so an attempt-armed flag
    would turn every later call into a silent no-op and re-open exactly that
    trap. Failing again on every call is the point.
    """
    global _app_home_migrated
    if _app_home_migrated:
        return
    try:
        maybe_migrate_app_home()
    except OSError as e:
        import sys

        from anyscribe.config.paths import APP_HOME, LEGACY_APP_HOME

        print(
            f"anyscribe: could not move {LEGACY_APP_HOME} to {APP_HOME} "
            f"({e.filename or APP_HOME}: {e.strerror or e}).\n"
            f"Fix that path, then run 'anyscribe migrate'.",
            file=sys.stderr,
        )
        raise SystemExit(1) from None
    _app_home_migrated = True


def app_home_moves() -> list[tuple[Path, Path]]:
    """The app-home decision table, read-only: the (src, dest) pairs to move.

    Split out of ``maybe_migrate_app_home`` so ``anyscribe migrate --dry-run``
    can report exactly what a real run will do. Both go through this one
    function, so a dry-run report cannot drift from the real behaviour.

    Never overwrites: an entry already present in the new home wins and its
    legacy twin is left on disk untouched.
    """
    from anyscribe.config.paths import APP_HOME, LEGACY_APP_HOME

    if not LEGACY_APP_HOME.is_dir():
        return []

    # ponytail: crude mtime guard — a recent write under the legacy tmp dir
    # means another process may be mid-transcription, so leave it alone.
    # A real lock file only if this ever bites.
    legacy_tmp = LEGACY_APP_HOME / "tmp"
    if legacy_tmp.is_dir():
        cutoff = time.time() - 300
        try:
            if any(p.stat().st_mtime > cutoff for p in legacy_tmp.rglob("*")):
                return []
        except OSError:
            # A chunk vanished between rglob and stat — that IS a live writer.
            return []

    if not APP_HOME.exists():
        return [(LEGACY_APP_HOME, APP_HOME)]

    # New home already exists. If it holds real config, it's either already
    # migrated or a genuine new-style setup — don't touch either.
    if (APP_HOME / "config.yaml").exists() or (APP_HOME / ".env").exists():
        return []

    # Empty-ish new home, created by a post-upgrade command that ran before
    # the migration existed. Rescue every entry that doesn't collide.
    return [
        (entry, APP_HOME / entry.name)
        for entry in sorted(LEGACY_APP_HOME.iterdir())
        if not (APP_HOME / entry.name).exists()
    ]


def maybe_migrate_app_home() -> bool:
    """Move LEGACY_APP_HOME to ~/.anyscribe/. Returns True if anything moved.

    Idempotent. See ``app_home_moves`` for the decision table.
    """
    moves = app_home_moves()
    for src, dest in moves:
        shutil.move(str(src), str(dest))
    return bool(moves)


def maybe_migrate_workspace() -> Path | None:
    """If legacy workspace exists and new default doesn't, move it.

    Returns the new path if migrated, None otherwise.
    """
    from anyscribe.config.paths import DEFAULT_WORKSPACE, LEGACY_WORKSPACE, get_workspace_dir

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
    """Rename ~/.anyscribe/media/ to ~/.anyscribe/downloads/.

    Returns True if migrated, False otherwise.
    """
    from anyscribe.config.paths import DOWNLOADS_DIR, LEGACY_MEDIA_DIR

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
    from anyscribe.config.paths import AUDIO_DIR, VIDEO_DIR, get_workspace_dir

    total = 0
    ws = get_workspace_dir()
    sources = ws / "sources"
    total += _flatten_dir(sources)
    total += _flatten_dir(AUDIO_DIR)
    total += _flatten_dir(VIDEO_DIR)
    return total
