"""File utilities - atomic writes and file locking."""

from __future__ import annotations

import os
import tempfile
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

try:
    import fcntl

    _HAS_FCNTL = True
except ImportError:
    _HAS_FCNTL = False
    import msvcrt


_THREAD_LOCKS: dict[Path, threading.Lock] = {}
_THREAD_LOCKS_GUARD = threading.Lock()


def _thread_lock_for(path: Path) -> threading.Lock:
    resolved = path.resolve()
    with _THREAD_LOCKS_GUARD:
        if resolved not in _THREAD_LOCKS:
            _THREAD_LOCKS[resolved] = threading.Lock()
        return _THREAD_LOCKS[resolved]


def atomic_write(path: Path, content: str) -> None:
    """Write content atomically via temp file + os.replace().

    os.replace() is atomic on POSIX and Windows. On crash mid-write, the
    original file is preserved.
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
    """Exclusive file lock for coordinated writes."""
    lock_path = path.with_suffix(path.suffix + ".lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    thread_lock = _thread_lock_for(lock_path)

    if not _HAS_FCNTL:
        with thread_lock:
            with open(lock_path, "a+b") as lock_file:
                lock_file.seek(0)
                try:
                    msvcrt.locking(lock_file.fileno(), msvcrt.LK_LOCK, 1)
                    yield
                finally:
                    lock_file.seek(0)
                    msvcrt.locking(lock_file.fileno(), msvcrt.LK_UNLCK, 1)
        return

    fd = os.open(str(lock_path), os.O_RDWR | os.O_CREAT)
    try:
        with thread_lock:
            fcntl.flock(fd, fcntl.LOCK_EX)
            yield
    finally:
        fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)
