"""Local transcription provisioning endpoints.

Three endpoints. ``GET /api/local/status`` is cheap and safe to poll; the
setup/teardown POSTs kick off background asyncio tasks and return immediately.
The front-end polls ``status`` to watch ``setup_running`` flip.

We keep setup state on ``app.state`` rather than in a module global so a
single running server can own a single in-flight setup at a time; a concurrent
POST while another is running returns 409.
"""

from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, HTTPException, Request

from anyscribecli.core.local_setup import (
    check_status,
    run_setup,
    run_teardown,
)
from anyscribecli.providers.local_models import MODEL_SIZES, RECOMMENDED_MODEL
from anyscribecli.web.models import LocalSetupRequest

router = APIRouter(prefix="/api/local", tags=["local"])


def _setup_state(app) -> dict[str, Any]:
    state = getattr(app.state, "local_setup", None)
    if state is None:
        state = {"running": False, "phase": None, "error": None, "last_model": None}
        app.state.local_setup = state
    return state


@router.get("/status")
async def local_status(request: Request) -> dict:
    state = _setup_state(request.app)
    status = check_status()
    status["setup_running"] = bool(state["running"])
    status["setup_phase"] = state["phase"]
    status["setup_error"] = state["error"]
    status["setup_last_model"] = state["last_model"]
    status["recommended_model"] = RECOMMENDED_MODEL
    status["choices"] = list(MODEL_SIZES)
    return status


def _background_setup(app, model: str) -> None:
    """Run run_setup synchronously in a thread — faster-whisper/HF calls block."""
    state = _setup_state(app)

    def on_progress(ev: dict) -> None:
        state["phase"] = ev.get("event")

    try:
        result = run_setup(model, on_progress=on_progress)
        if result.get("status") == "failed":
            phase = result.get("phase")
            install_stderr = (result.get("install", {}) or {}).get("stderr") or ""
            error_msg = result.get("error") or install_stderr or f"setup failed in {phase}"
            state["error"] = error_msg
        else:
            state["error"] = None
    except Exception as e:
        state["error"] = str(e)
    finally:
        state["running"] = False
        state["phase"] = "done"


@router.post("/setup")
async def local_setup_endpoint(req: LocalSetupRequest, request: Request) -> dict:
    if req.model not in MODEL_SIZES:
        raise HTTPException(
            status_code=400,
            detail=f"unknown model '{req.model}'. Choices: {', '.join(MODEL_SIZES)}",
        )

    state = _setup_state(request.app)
    if state["running"]:
        raise HTTPException(status_code=409, detail="setup already in progress")

    state["running"] = True
    state["phase"] = "starting"
    state["error"] = None
    state["last_model"] = req.model

    loop = asyncio.get_event_loop()
    loop.run_in_executor(None, _background_setup, request.app, req.model)

    return {"status": "started", "model": req.model}


@router.post("/teardown")
async def local_teardown_endpoint(request: Request) -> dict:
    state = _setup_state(request.app)
    if state["running"]:
        raise HTTPException(status_code=409, detail="setup in progress")

    # Teardown is fast enough to run synchronously; keeps the UI simple.
    result = await asyncio.get_event_loop().run_in_executor(None, run_teardown)
    return result
