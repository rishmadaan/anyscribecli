"""Model-cache endpoints for the Web UI's Models panel.

Day-to-day pull/delete of individual models after ``scribe local setup``
is complete. Pull runs in a background thread; the UI polls
``GET /api/models/local`` (or the parent ``/api/local/status``) to watch
for ``cached: true``.
"""

from __future__ import annotations

import asyncio
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


def _downloads_state(app) -> dict[str, dict[str, Any]]:
    """Per-size download state, stashed on app.state.

    Shape: ``{size: {running: bool, error: str|None}}``. Only one size may
    download at a time; starting a second while one runs returns 409.
    """
    state = getattr(app.state, "model_downloads", None)
    if state is None:
        state = {}
        app.state.model_downloads = state
    return state


def _any_download_running(state: dict) -> bool:
    return any(entry.get("running") for entry in state.values())


@router.get("/local")
async def list_local_models(request: Request) -> dict:
    settings = load_config()
    models = list_cached_models()
    downloads = _downloads_state(request.app)
    total_bytes = sum(int(m["bytes"]) for m in models)

    return {
        "default": settings.local_model,
        "faster_whisper_installed": faster_whisper_importable(),
        "total_disk_bytes": total_bytes,
        "models": [
            {
                "size": m["size"],
                "cached": m["cached"],
                "bytes": m["bytes"],
                "repo": m["repo"],
                "spec": m["spec"],
                "downloading": downloads.get(m["size"], {}).get("running", False),
                "error": downloads.get(m["size"], {}).get("error"),
            }
            for m in models
        ],
    }


def _background_pull(app, size: str) -> None:
    state = _downloads_state(app)
    try:
        pull_model(size)
        state[size]["error"] = None
    except Exception as e:
        state[size]["error"] = str(e)
    finally:
        state[size]["running"] = False


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

    downloads = _downloads_state(request.app)
    current = downloads.get(size, {})
    if current.get("running"):
        raise HTTPException(status_code=409, detail=f"{size} is already downloading")

    if is_cached(size):
        return {"status": "already_present", "size": size}

    if _any_download_running(downloads):
        raise HTTPException(status_code=409, detail="another model is currently downloading")

    downloads[size] = {"running": True, "error": None}
    asyncio.get_event_loop().run_in_executor(None, _background_pull, request.app, size)
    return {"status": "started", "size": size}


@router.delete("/local/{size}")
async def delete_local_model(size: str, request: Request) -> dict:
    if size not in MODEL_SIZES:
        raise HTTPException(
            status_code=400,
            detail=f"unknown size '{size}'. Choices: {', '.join(MODEL_SIZES)}",
        )
    downloads = _downloads_state(request.app)
    if downloads.get(size, {}).get("running"):
        raise HTTPException(status_code=409, detail=f"{size} is currently downloading")

    result = await asyncio.get_event_loop().run_in_executor(None, delete_model, size)
    return result
