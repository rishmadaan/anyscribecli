"""Tests for atomic writes and file locking."""

import threading

from anyscribecli.core.fileutil import atomic_write, file_lock


class TestAtomicWrite:
    def test_creates_file(self, tmp_path):
        p = tmp_path / "test.txt"
        atomic_write(p, "hello")
        assert p.read_text() == "hello"

    def test_overwrites_existing(self, tmp_path):
        p = tmp_path / "test.txt"
        p.write_text("old")
        atomic_write(p, "new")
        assert p.read_text() == "new"

    def test_creates_parent_dirs(self, tmp_path):
        p = tmp_path / "a" / "b" / "test.txt"
        atomic_write(p, "nested")
        assert p.read_text() == "nested"

    def test_no_temp_file_left_on_success(self, tmp_path):
        p = tmp_path / "test.txt"
        atomic_write(p, "clean")
        files = list(tmp_path.iterdir())
        assert len(files) == 1
        assert files[0].name == "test.txt"


class TestFileLock:
    def test_lock_allows_sequential_access(self, tmp_path):
        p = tmp_path / "data.txt"
        p.write_text("0")

        with file_lock(p):
            val = int(p.read_text())
            atomic_write(p, str(val + 1))

        assert p.read_text() == "1"

    def test_lock_blocks_concurrent_access(self, tmp_path):
        p = tmp_path / "counter.txt"
        p.write_text("0")
        results = []

        def increment():
            with file_lock(p):
                val = int(p.read_text())
                results.append(val)
                atomic_write(p, str(val + 1))

        threads = [threading.Thread(target=increment) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # If locking works, final value should be 5
        assert p.read_text() == "5"
        # Each thread should have seen a unique value
        assert sorted(results) == [0, 1, 2, 3, 4]
