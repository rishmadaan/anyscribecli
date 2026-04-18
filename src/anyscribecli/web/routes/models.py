"""Model-cache endpoints for the Web UI's Models panel.

Single-worker FIFO queue for downloads — clicking Download on a second model
while another is in flight enqueues instead of erroring. Reinstall is a
convenience composite (delete + pull) exposed as one endpoint.
"""

from __future__ import annotations

import asyncio
import threading
from typing import Any

from fastapi import APIRouter, HTTPException, Request

from anyscribecli.config.settings import load_config
from anyscribecli.providers.local_models import (
    MODEL_SIZES,
    delete_model,
    faster_whisper_importable,
    is_cached,
    list_cached_models,
    pull_model,
)

router = APIRouter(prefix="/api/models", tags=["models"])


def _download_state(app) -> dict[str, Any]:
    """FIFO queue state stashed on app.state.

    Shape:
      - ``queue``: list[str] — sizes waiting, head = currently running
      - ``lock``: threading.Lock for queue mutations (worker runs in executor)
      - ``worker_running``: bool — whether the worker task is alive
      - ``results``: dict[size, {status, error?}] — last terminal state per size
    """
    state = getattr(app.state, "download_queue", None)
    if state is None:
        state = {
            "queue": [],
            "lock": threading.Lock(),
            "worker_running": False,
            "results": {},
        }
        app.state.download_queue = state
    return state


def _queue_position(state: dict, size: str) -> int:
    """Return size's position in the queue, or -1 if not queued."""
    try:
        return state["queue"].index(size)
    except ValueError:
        return -1


def _worker_loop(app) -> None:
    """Single consumer: pop from queue head, pull the model, repeat until empty."""
    state = _download_state(app)
    while True:
        with state["lock"]:
            if not state["queue"]:
                state["worker_running"] = False
                return
            size = state["queue"][0]  # running = head

        try:
            pull_model(size)
            with state["lock"]:
                state["results"][size] = {"status": "completed"}
        except Exception as e:
            with state["lock"]:
                state["results"][size] = {"status": "failed", "error": str(e)}
        finally:
            with state["lock"]:
                if state["queue"] and state["queue"][0] == size:
                    state["queue"].pop(0)


def _kick_worker(app) -> None:
    """Start the worker loop if not already running."""
    state = _download_state(app)
    with state["lock"]:
        if state["worker_running"]:
            return
        state["worker_running"] = True
    asyncio.get_event_loop().run_in_executor(None, _worker_loop, app)


@router.get("/local")
async def list_local_models(request: Request) -> dict:
    settings = load_config()
    models = list_cached_models()
    state = _download_state(request.app)
    total_bytes = sum(int(m["bytes"]) for m in models)

    with state["lock"]:
        queue = list(state["queue"])
        results = dict(state["results"])

    def _entry(m):
        size = m["size"]
        pos = queue.index(size) if size in queue else -1
        return {
            "size": size,
            "cached": m["cached"],
            "bytes": m["bytes"],
            "repo": m["repo"],
            "spec": m["spec"],
            "downloading": pos == 0,
            "queued": pos > 0,
            "queue_position": pos,
            "last_error": (results.get(size) or {}).get("error"),
        }

    return {
        "default": settings.local_model,
        "faster_whisper_installed": faster_whisper_importable(),
        "total_disk_bytes": total_bytes,
        "models": [_entry(m) for m in models],
        "queue": queue,
    }


@router.post("/local/{size}/pull")
async def pull_local_model(size: str, request: Request) -> dict:
    if size not in MODEL_SIZES:
        raise HTTPException(
            status_code=400,
            detail=f"unknown size '{size}'. Choices: {', '.join(MODEL_SIZES)}",
        )
    if not faster_whisper_importable():
        raise HTTPException(
            status_code=409,
            detail="local transcription not set up — call POST /api/local/setup first",
        )

    if is_cached(size):
        return {"status": "already_present", "size": size}

    state = _download_state(request.app)
    with state["lock"]:
        if size in state["queue"]:
            pos = state["queue"].index(size)
            return {"status": "already_in_queue", "size": size, "position": pos}
        state["queue"].append(size)
        position = len(state["queue"]) - 1

    _kick_worker(request.app)

    return {
        "status": "started" if position == 0 else "queued",
        "size": size,
        "position": position,
    }


@router.post("/local/{size}/reinstall")
async def reinstall_local_model(size: str, request: Request) -> dict:
    """Delete + download in one call. Useful for corrupted weights.

    Runs synchronously — reinstall is rare and a progress spinner is fine.
    """
    if size not in MODEL_SIZES:
        raise HTTPException(
            status_code=400,
            detail=f"unknown size '{size}'. Choices: {', '.join(MODEL_SIZES)}",
        )
    if not faster_whisper_importable():
        raise HTTPException(
            status_code=409,
            detail="local transcription not set up",
        )

    state = _download_state(request.app)
    with state["lock"]:
        if state["queue"] and state["queue"][0] == size:
            raise HTTPException(status_code=409, detail=f"{size} is currently downloading")

    loop = asyncio.get_event_loop()

    bytes_freed = 0
    if await loop.run_in_executor(None, is_cached, size):
        del_result = await loop.run_in_executor(None, delete_model, size)
        bytes_freed = int(del_result.get("bytes_freed", 0))

    try:
        pull_result = await loop.run_in_executor(None, pull_model, size)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"reinstall failed: {e}")

    return {
        "status": "reinstalled" if bytes_freed > 0 else "downloaded_only",
        "size": size,
        "bytes_freed": bytes_freed,
        "bytes_downloaded": int(pull_result.get("bytes", 0)),
    }


@router.delete("/local/{size}")
async def delete_local_model(size: str, request: Request) -> dict:
    if size not in MODEL_SIZES:
        raise HTTPException(
            status_code=400,
            detail=f"unknown size '{size}'. Choices: {', '.join(MODEL_SIZES)}",
        )
    state = _download_state(request.app)
    with state["lock"]:
        if state["queue"] and state["queue"][0] == size:
            raise HTTPException(status_code=409, detail=f"{size} is currently downloading")
        if size in state["queue"]:
            state["queue"].remove(size)
            return {"status": "cancelled", "size": size, "bytes_freed": 0}

    result = await asyncio.get_event_loop().run_in_executor(None, delete_model, size)
    return result
