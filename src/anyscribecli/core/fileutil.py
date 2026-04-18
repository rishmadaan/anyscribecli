"""File utilities — atomic writes and file locking."""

from __future__ import annotations

import os
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

try:
    import fcntl

    _HAS_FCNTL = True
except ImportError:
    _HAS_FCNTL = False  # Windows — locking is a no-op


def atomic_write(path: Path, content: str) -> None:
    """Write content atomically via temp file + os.replace().

    os.replace() is atomic on POSIX. On crash mid-write, the original
    file is preserved (only the temp file is corrupted).
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        os.write(fd, content.encode())
        os.close(fd)
        os.replace(tmp, str(path))
    except BaseException:
        try:
            os.close(fd)
        except OSError:
            pass
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


@contextmanager
def file_lock(path: Path) -> Generator[None, None, None]:
    """Exclusive file lock via flock. Falls back to no-op on Windows.

    Usage::

        with file_lock(index_file):
            content = index_file.read_text()
            # ... modify ...
            atomic_write(index_file, new_content)
    """
    if not _HAS_FCNTL:
        yield
        return

    lock_path = path.with_suffix(path.suffix + ".lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(str(lock_path), os.O_RDWR | os.O_CREAT)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        yield
    finally:
        fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)
