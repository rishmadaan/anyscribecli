"""Tests for chunk checkpoint save/resume."""

from unittest.mock import patch

from anyscribecli.core.checkpoint import ChunkCheckpoint


class TestChunkCheckpoint:
    def test_create_new(self, tmp_path):
        audio = tmp_path / "test.mp3"
        audio.write_bytes(b"\x00" * 1000)

        with patch("anyscribecli.core.checkpoint.CHECKPOINT_DIR", tmp_path / "ckpts"):
            ckpt = ChunkCheckpoint.load_or_create(audio, "openai", "en", 5)
            assert ckpt.total_chunks == 5
            assert ckpt.provider == "openai"
            assert len(ckpt.completed) == 0

    def test_save_and_load(self, tmp_path):
        audio = tmp_path / "test.mp3"
        audio.write_bytes(b"\x00" * 1000)

        with patch("anyscribecli.core.checkpoint.CHECKPOINT_DIR", tmp_path / "ckpts"):
            ckpt = ChunkCheckpoint.load_or_create(audio, "openai", "en", 3)
            ckpt.mark_completed(0, {"text": "hello", "language": "en", "duration": 10.0, "segments": []})
            ckpt.save()

            ckpt2 = ChunkCheckpoint.load_or_create(audio, "openai", "en", 3)
            assert ckpt2.is_completed(0)
            assert not ckpt2.is_completed(1)
            assert ckpt2.get(0)["text"] == "hello"

    def test_cleanup_removes_file(self, tmp_path):
        audio = tmp_path / "test.mp3"
        audio.write_bytes(b"\x00" * 1000)

        with patch("anyscribecli.core.checkpoint.CHECKPOINT_DIR", tmp_path / "ckpts"):
            ckpt = ChunkCheckpoint.load_or_create(audio, "openai", "en", 2)
            ckpt.mark_completed(0, {"text": "hi", "language": "en", "duration": 5.0, "segments": []})
            ckpt.save()

            # Checkpoint file should exist
            ckpt_dir = tmp_path / "ckpts"
            assert any(ckpt_dir.iterdir())

            ckpt.cleanup()
            # Checkpoint file should be gone
            remaining = [f for f in ckpt_dir.iterdir() if f.suffix == ".json"]
            assert len(remaining) == 0

    def test_corrupt_checkpoint_ignored(self, tmp_path):
        audio = tmp_path / "test.mp3"
        audio.write_bytes(b"\x00" * 1000)

        with patch("anyscribecli.core.checkpoint.CHECKPOINT_DIR", tmp_path / "ckpts"):
            ckpt = ChunkCheckpoint.load_or_create(audio, "openai", "en", 2)
            ckpt.save()

            # Corrupt the file
            from anyscribecli.core.checkpoint import _file_hash, _checkpoint_path
            h = _file_hash(audio)
            path = _checkpoint_path(h, "openai")
            path.write_text("not json")

            # Should create a fresh checkpoint, not crash
            ckpt2 = ChunkCheckpoint.load_or_create(audio, "openai", "en", 2)
            assert len(ckpt2.completed) == 0
