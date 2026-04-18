"""System endpoints — shutdown, version."""

from __future__ import annotations

from fastapi import APIRouter, Request

from anyscribecli import __version__

router = APIRouter(prefix="/api", tags=["system"])


@router.post("/shutdown")
async def shutdown(request: Request) -> dict:
    """Gracefully shut down the server."""
    server = getattr(request.app.state, "server", None)
    if server:
        server.should_exit = True
    return {"ok": True, "message": "shutting down"}


@router.get("/version")
async def version() -> dict:
    return {"version": __version__}
