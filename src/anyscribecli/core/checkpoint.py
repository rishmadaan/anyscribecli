"""Chunk checkpoint — save/resume partial transcriptions."""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from anyscribecli.config.paths import CHECKPOINT_DIR

logger = logging.getLogger(__name__)


@dataclass
class ChunkCheckpoint:
    """Tracks progress of chunked transcription for resume capability."""

    audio_hash: str
    provider: str
    language: str
    total_chunks: int
    completed: dict[str, dict[str, Any]] = field(default_factory=dict)
    # completed maps chunk index (as string) -> {text, segments, language, duration}

    @classmethod
    def load_or_create(
        cls,
        audio_path: Path,
        provider: str,
        language: str,
        total_chunks: int,
    ) -> ChunkCheckpoint:
        """Load existing checkpoint or create a new one."""
        audio_hash = _file_hash(audio_path)
        path = _checkpoint_path(audio_hash, provider)

        if path.exists():
            try:
                data = json.loads(path.read_text())
                ckpt = cls(
                    audio_hash=data["audio_hash"],
                    provider=data["provider"],
                    language=data["language"],
                    total_chunks=data["total_chunks"],
                    completed=data.get("completed", {}),
                )
                if (
                    ckpt.audio_hash == audio_hash
                    and ckpt.provider == provider
                    and ckpt.total_chunks == total_chunks
                ):
                    resumed = len(ckpt.completed)
                    if resumed > 0:
                        logger.info(
                            "Resuming from checkpoint: %d/%d chunks done",
                            resumed,
                            total_chunks,
                        )
                    return ckpt
            except (json.JSONDecodeError, KeyError):
                pass  # Corrupt checkpoint — start fresh

        return cls(
            audio_hash=audio_hash,
            provider=provider,
            language=language,
            total_chunks=total_chunks,
        )

    def is_completed(self, chunk_index: int) -> bool:
        return str(chunk_index) in self.completed

    def get(self, chunk_index: int) -> dict[str, Any]:
        return self.completed[str(chunk_index)]

    def mark_completed(self, chunk_index: int, data: dict[str, Any]) -> None:
        # Strip non-serializable segment objects — store as dicts
        segments = data.get("segments", [])
        if segments and hasattr(segments[0], "__dict__"):
            data["segments"] = [
                asdict(s) if hasattr(s, "__dataclass_fields__") else s for s in segments
            ]
        self.completed[str(chunk_index)] = data

    def save(self) -> None:
        CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
        path = _checkpoint_path(self.audio_hash, self.provider)
        path.write_text(json.dumps(asdict(self), indent=2))

    def cleanup(self) -> None:
        """Remove checkpoint file after successful completion."""
        path = _checkpoint_path(self.audio_hash, self.provider)
        path.unlink(missing_ok=True)


def _file_hash(path: Path) -> str:
    """Fast hash of a file (first 64KB + size)."""
    h = hashlib.md5()
    h.update(str(path.stat().st_size).encode())
    with open(path, "rb") as f:
        h.update(f.read(65536))
    return h.hexdigest()[:12]


def _checkpoint_path(audio_hash: str, provider: str) -> Path:
    return CHECKPOINT_DIR / f"{audio_hash}_{provider}.json"
