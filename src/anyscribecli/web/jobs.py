"""In-memory job manager — runs process() in threads, bridges to async."""

from __future__ import annotations

import asyncio
import time
import uuid
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from anyscribecli.web.progress import ProgressEvent

# Cleanup constants
JOB_TTL_SECONDS = 3600  # Remove completed/failed jobs after 1 hour
MAX_EVENTS_PER_JOB = 100  # Cap event history per job
MAX_JOBS = 500  # Hard cap on total jobs in memory


class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class Job:
    id: str
    url: str
    status: JobStatus = JobStatus.PENDING
    events: list[ProgressEvent] = field(default_factory=list)
    result: dict[str, Any] | None = None
    error: str | None = None
    completed_at: float | None = None
    _subscribers: list[asyncio.Queue] = field(default_factory=list)


class JobManager:
    """Manages transcription jobs with thread-pool execution and async event streaming."""

    def __init__(self, max_workers: int = 2) -> None:
        self._jobs: OrderedDict[str, Job] = OrderedDict()
        self._executor = ThreadPoolExecutor(max_workers=max_workers)

    def _cleanup_stale(self) -> None:
        """Remove completed/failed jobs older than TTL."""
        now = time.time()
        stale = [
            jid
            for jid, job in self._jobs.items()
            if job.status in (JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED)
            and job.completed_at
            and (now - job.completed_at) > JOB_TTL_SECONDS
        ]
        for jid in stale:
            del self._jobs[jid]
        # Hard cap
        while len(self._jobs) > MAX_JOBS:
            self._jobs.popitem(last=False)

    def get(self, job_id: str) -> Job | None:
        self._cleanup_stale()
        return self._jobs.get(job_id)

    def subscribe(self, job: Job) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue()
        job._subscribers.append(q)
        return q

    def unsubscribe(self, job: Job, queue: asyncio.Queue) -> None:
        try:
            job._subscribers.remove(queue)
        except ValueError:
            pass

    async def submit(self, url: str, settings: Any, loop: asyncio.AbstractEventLoop) -> str:
        """Submit a new transcription job. Returns job_id immediately."""
        self._cleanup_stale()
        job_id = uuid.uuid4().hex[:8]
        job = Job(id=job_id, url=url)
        self._jobs[job_id] = job
        loop.run_in_executor(self._executor, self._run_job, job, settings, loop)
        return job_id

    def _run_job(self, job: Job, settings: Any, loop: asyncio.AbstractEventLoop) -> None:
        """Run process() synchronously in a thread, pushing events to subscribers."""
        from anyscribecli.config.settings import load_env
        from anyscribecli.core.orchestrator import process

        load_env()
        job.status = JobStatus.RUNNING

        def on_progress(step: str, status: str, message: str, **kwargs: Any) -> None:
            event = ProgressEvent(
                step=step,
                status=status,
                message=message,
                percent=kwargs.get("percent"),
                data=kwargs.get("data", {}),
            )
            job.events.append(event)
            # Cap event history to prevent unbounded growth
            if len(job.events) > MAX_EVENTS_PER_JOB:
                job.events = job.events[-MAX_EVENTS_PER_JOB:]
            dead_queues = []
            for q in list(job._subscribers):
                try:
                    loop.call_soon_threadsafe(q.put_nowait, event)
                except Exception:
                    dead_queues.append(q)
            for q in dead_queues:
                try:
                    job._subscribers.remove(q)
                except ValueError:
                    pass

        try:
            result = process(
                url=job.url,
                settings=settings,
                quiet=True,
                on_progress=on_progress,
            )
            job.status = JobStatus.COMPLETED
            job.completed_at = time.time()
            job.result = {
                "file_path": str(result.file_path),
                "title": result.title,
                "platform": result.platform,
                "duration": result.duration,
                "language": result.language,
                "word_count": result.word_count,
                "provider": result.provider,
            }
            # Send completion event
            done_event = ProgressEvent(
                step="done",
                status="completed",
                message="Transcription complete",
                data=job.result,
            )
            job.events.append(done_event)
            for q in list(job._subscribers):
                try:
                    loop.call_soon_threadsafe(q.put_nowait, done_event)
                except Exception:
                    pass

        except Exception as e:
            job.status = JobStatus.FAILED
            job.completed_at = time.time()
            job.error = str(e)
            err_event = ProgressEvent(
                step="error",
                status="error",
                message=str(e),
            )
            job.events.append(err_event)
            for q in list(job._subscribers):
                try:
                    loop.call_soon_threadsafe(q.put_nowait, err_event)
                except Exception:
                    pass


# Singleton for the app lifetime
job_manager = JobManager()
