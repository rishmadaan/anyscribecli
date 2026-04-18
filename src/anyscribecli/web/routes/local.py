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


# Max lines the setup log keeps per run. Enough to diagnose pip/HF issues
# without blowing up memory if something goes pathological.
LOG_RING_LIMIT = 500


def _setup_state(app) -> dict[str, Any]:
    state = getattr(app.state, "local_setup", None)
    if state is None:
        state = {
            "running": False,
            "phase": None,
            "error": None,
            "last_model": None,
            "log": [],
        }
        app.state.local_setup = state
    return state


def _append_log(state: dict, line: str) -> None:
    """Append a single line to the ring buffer, trimming from the head."""
    log = state["log"]
    log.append(line)
    if len(log) > LOG_RING_LIMIT:
        del log[: len(log) - LOG_RING_LIMIT]


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


@router.get("/setup/log")
async def local_setup_log(request: Request, since: int = 0) -> dict:
    """Return lines appended to the setup log since index ``since``.

    Used by the UI to stream pip/install output into a collapsible panel
    inside LocalSetupModal. Lightweight polling, not WebSocket.
    """
    state = _setup_state(request.app)
    log = state["log"]
    total = len(log)
    since = max(0, min(since, total))
    return {
        "lines": log[since:],
        "total": total,
        "running": bool(state["running"]),
    }


def _background_setup(app, model: str) -> None:
    """Run run_setup synchronously in a thread — faster-whisper/HF calls block."""
    state = _setup_state(app)
    # Fresh run = fresh log.
    state["log"].clear()

    def on_progress(ev: dict) -> None:
        name = ev.get("event")
        state["phase"] = name
        # Mirror phase transitions into the log so the UI panel tells a story
        # even before the install subprocess starts emitting output.
        if name == "installing_package":
            method = ev.get("method", "?")
            cmd = ev.get("command") or []
            _append_log(state, f"[phase] installing faster-whisper via {method}")
            if cmd:
                _append_log(state, f"[cmd] {' '.join(cmd)}")
        elif name == "package_installed":
            _append_log(state, "[phase] faster-whisper installed")
        elif name == "downloading_model":
            _append_log(state, f"[phase] downloading model: {ev.get('size', '?')}")
        elif name == "model_downloaded":
            mb = int(ev.get("bytes", 0)) // (1024 * 1024)
            _append_log(state, f"[phase] model downloaded ({mb} MB)")
        elif name == "done":
            _append_log(state, "[phase] done")

    try:
        result = run_setup(model, on_progress=on_progress)
        if result.get("status") == "failed":
            phase = result.get("phase")
            install = result.get("install") or {}
            install_stderr = (install.get("stderr") or "").strip()
            error_msg = result.get("error") or install_stderr or f"setup failed in {phase}"
            state["error"] = error_msg
            if install_stderr:
                for line in install_stderr.splitlines():
                    _append_log(state, f"[stderr] {line}")
            _append_log(state, f"[error] {error_msg}")
        else:
            state["error"] = None
    except Exception as e:
        state["error"] = str(e)
        _append_log(state, f"[error] {e}")
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
