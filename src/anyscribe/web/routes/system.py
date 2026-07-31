"""System endpoints — shutdown, autostart."""

from __future__ import annotations

import sys
from importlib.util import find_spec

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from anyscribe.core import service

router = APIRouter(prefix="/api", tags=["system"])


class AutostartRequest(BaseModel):
    enabled: bool


def _autostart_state() -> dict:
    supported = sys.platform == "darwin"
    return {
        "supported": supported,
        "enabled": supported and service.plist_path().exists(),
    }


@router.get("/autostart")
async def autostart_status() -> dict:
    """Report whether open-at-login is available and currently on."""
    return _autostart_state()


@router.put("/autostart")
async def set_autostart(req: AutostartRequest) -> dict:
    """Install or remove the tray LaunchAgent. macOS only."""
    if sys.platform != "darwin":
        raise HTTPException(status_code=400, detail="Autostart is only supported on macOS")
    if req.enabled:
        # A LaunchAgent without pystray installs fine and then fails at login,
        # silently. Refuse up front instead.
        if find_spec("pystray") is None:
            raise HTTPException(
                status_code=400,
                detail='The menu-bar tray isn\'t installed. Run: pip install "anyscribe[tray]" first.',
            )
        service.install_service()
    else:
        service.uninstall_service()
    return _autostart_state()


@router.post("/shutdown")
async def shutdown(request: Request) -> dict:
    """Gracefully shut down the server."""
    server = getattr(request.app.state, "server", None)
    if server:
        server.should_exit = True
    return {"ok": True, "message": "shutting down"}
