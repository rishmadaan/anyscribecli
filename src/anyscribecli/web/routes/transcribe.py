"""Transcription job endpoints — submit jobs and stream progress via WebSocket."""

from __future__ import annotations

import asyncio
import shutil
import uuid
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile, WebSocket, WebSocketDisconnect

from anyscribecli.config.paths import TMP_DIR
from anyscribecli.config.settings import load_config, load_env
from anyscribecli.web.jobs import job_manager
from anyscribecli.web.models import JobStatusResponse, TranscribeRequest

router = APIRouter(prefix="/api", tags=["transcribe"])


@router.post("/upload")
async def upload_file(file: UploadFile) -> dict:
    """Upload a local audio/video file for transcription. Returns the server-side path.

    The file is saved inside a per-upload UUID subdir under its **original
    filename** (lightly sanitized for filesystem safety). Downstream the
    LocalFileDownloader reads ``Path.stem`` as the transcript title, and the
    vault writer slugifies it into kebab-case for the markdown filename. So
    an upload of ``My Recording.mp3`` becomes ``my-recording.md`` in the
    vault, not a UUID hex like ``3f2a8b9c.md``.
    """
    TMP_DIR.mkdir(parents=True, exist_ok=True)
    upload_dir = TMP_DIR / "uploads"
    upload_dir.mkdir(exist_ok=True)

    # Per-upload subdir avoids collisions without polluting the filename.
    upload_subdir = upload_dir / uuid.uuid4().hex[:8]
    upload_subdir.mkdir()

    # Preserve the original filename, but sanitize it for FS safety:
    # strip path separators, null bytes, and any leading dots that would
    # turn the file into a hidden dotfile.
    safe_name = "upload"
    if file.filename:
        raw = Path(file.filename).name  # drops any directory parts
        cleaned = raw.replace("\x00", "").lstrip(".").strip()
        if cleaned:
            safe_name = cleaned

    dest = upload_subdir / safe_name

    # Cap upload size so a runaway/malicious upload can't fill the disk.
    # 4 GiB comfortably fits multi-hour video; audio is far smaller.
    max_bytes = 4 * 1024**3
    written = 0
    with open(dest, "wb") as f:
        while chunk := file.file.read(1024 * 1024):
            written += len(chunk)
            if written > max_bytes:
                f.close()
                shutil.rmtree(upload_subdir, ignore_errors=True)
                raise HTTPException(status_code=413, detail="File exceeds the 4 GB upload limit.")
            f.write(chunk)

    return {"path": str(dest), "filename": file.filename}


@router.post("/transcribe")
async def start_transcribe(req: TranscribeRequest) -> dict:
    """Start a transcription job. Returns job_id for WebSocket progress tracking."""
    load_env()
    settings = load_config()

    # Apply overrides from request
    if req.quality:
        settings.quality = req.quality
    if req.language:
        settings.language = req.language
    if req.output_format:
        settings.output_format = req.output_format
    if req.diarize is not None:
        settings.diarize = req.diarize
    if settings.diarize and settings.output_format == "clean":
        settings.output_format = "diarized"
    settings.keep_media = req.keep_media

    from anyscribecli.core.resolve import resolve_run

    try:
        plan = resolve_run(
            settings, cli_provider=req.provider, cli_model=req.model, diarize=settings.diarize
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    settings.provider = plan.provider

    loop = asyncio.get_event_loop()
    job_id = await job_manager.submit(req.url, settings, loop, force=req.force, model=plan.model)
    return {
        "job_id": job_id,
        "provider": plan.provider,
        "model": plan.model,
        "notes": plan.notes,
    }


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


@router.post("/jobs/{job_id}/cancel")
async def cancel_job(job_id: str) -> dict:
    """Request cancellation of a running job. No-op if already finished."""
    job = job_manager.cancel(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return {"job_id": job.id, "status": job.status.value}


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
            if event.step in ("done", "error", "cancelled"):
                break

    except WebSocketDisconnect:
        pass
    finally:
        job_manager.unsubscribe(job, queue)
