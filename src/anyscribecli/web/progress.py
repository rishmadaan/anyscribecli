"""Progress event model for the web UI job system."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Protocol


class ProgressCallback(Protocol):
    """Callable signature for progress updates from the orchestrator."""

    def __call__(self, step: str, status: str, message: str, **kwargs: Any) -> None: ...


@dataclass
class ProgressEvent:
    """A single progress update emitted during transcription."""

    step: str  # download, transcribe, write, index, done, error
    status: str  # started, completed, error
    message: str
    percent: int | None = None
    data: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        # Drop None fields for cleaner JSON
        return {k: v for k, v in d.items() if v is not None}
