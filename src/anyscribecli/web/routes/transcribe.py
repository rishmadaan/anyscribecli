"""Transcription job endpoints — submit jobs and stream progress via WebSocket."""

from __future__ import annotations

import asyncio
import shutil
import uuid

from fastapi import APIRouter, UploadFile, WebSocket, WebSocketDisconnect

from anyscribecli.config.paths import TMP_DIR
from anyscribecli.config.settings import load_config, load_env
from anyscribecli.web.jobs import job_manager
from anyscribecli.web.models import JobStatusResponse, TranscribeRequest

router = APIRouter(prefix="/api", tags=["transcribe"])


@router.post("/upload")
async def upload_file(file: UploadFile) -> dict:
    """Upload a local audio/video file for transcription. Returns the server-side path."""
    TMP_DIR.mkdir(parents=True, exist_ok=True)
    upload_dir = TMP_DIR / "uploads"
    upload_dir.mkdir(exist_ok=True)

    # Preserve original extension, use unique name to avoid collisions
    suffix = ""
    if file.filename:
        from pathlib import Path as P

        suffix = P(file.filename).suffix
    dest = upload_dir / f"{uuid.uuid4().hex[:8]}{suffix}"

    with open(dest, "wb") as f:
        shutil.copyfileobj(file.file, f)

    return {"path": str(dest), "filename": file.filename}


@router.post("/transcribe")
async def start_transcribe(req: TranscribeRequest) -> dict:
    """Start a transcription job. Returns job_id for WebSocket progress tracking."""
    load_env()
    settings = load_config()

    # Apply overrides from request
    if req.provider:
        settings.provider = req.provider
    if req.language:
        settings.language = req.language
    if req.output_format:
        settings.output_format = req.output_format
    settings.diarize = req.diarize
    if req.diarize and settings.output_format == "clean":
        settings.output_format = "diarized"
    settings.keep_media = req.keep_media

    loop = asyncio.get_event_loop()
    job_id = await job_manager.submit(req.url, settings, loop)
    return {"job_id": job_id}


@router.get("/jobs/{job_id}")
async def get_job_status(job_id: str) -> JobStatusResponse:
    """Poll job status (fallback for when WebSocket isn't available)."""
    job = job_manager.get(job_id)
    if not job:
        return JobStatusResponse(
            job_id=job_id, status="not_found", events=[], result=None, error="Job not found"
        )
    return JobStatusResponse(
        job_id=job.id,
        status=job.status.value,
        events=[e.to_dict() for e in job.events],
        result=job.result,
        error=job.error,
    )


@router.websocket("/ws/jobs/{job_id}")
async def job_websocket(websocket: WebSocket, job_id: str) -> None:
    """Stream real-time progress events for a transcription job."""
    await websocket.accept()

    job = job_manager.get(job_id)
    if not job:
        await websocket.send_json({"step": "error", "status": "error", "message": "Job not found"})
        await websocket.close(code=4004)
        return

    queue = job_manager.subscribe(job)
    try:
        # Replay events that already happened before we connected
        for event in list(job.events):
            await websocket.send_json(event.to_dict())

        # Stream new events as they arrive
        while True:
            event = await queue.get()
            await websocket.send_json(event.to_dict())
            if event.step in ("done", "error"):
                break

    except WebSocketDisconnect:
        pass
    finally:
        job_manager.unsubscribe(job, queue)
