"""Onboarding status + save endpoints for the Web UI wizard.

The wizard itself is a React component that composes writes across several
existing endpoints (`PUT /api/config`, `PUT /api/keys`, `POST /api/local/setup`).
This router only exposes the *status* check — "is the user onboarded yet?" —
that the Web UI uses to decide whether to pop the wizard on launch.

There's also a single ``/save`` endpoint that lets the wizard fan out to the
backend in one round-trip. It internally calls the same ``run_headless_onboard``
module the CLI ``--yes`` path uses, so both surfaces produce identical state.
"""

from __future__ import annotations

import os
from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from anyscribecli.config.paths import get_workspace_dir
from anyscribecli.config.settings import load_config, load_env
from anyscribecli.core.local_setup import local_ready
from anyscribecli.core.onboard_headless import (
    OnboardValidationError,
    PROVIDER_KEY_ENV,
    run_headless_onboard,
)

router = APIRouter(prefix="/api/onboarding", tags=["onboarding"])


class OnboardingSaveRequest(BaseModel):
    provider: str
    api_key: Optional[str] = None
    workspace: Optional[str] = None
    language: Optional[str] = None
    keep_media: Optional[bool] = None
    output_format: Optional[str] = None
    local_model: Optional[str] = None
    extra_api_keys: Optional[dict[str, str]] = None
    instagram_browser: Optional[str] = None


def _recommended_next_step(
    has_workspace: bool,
    has_any_key: bool,
    local: bool,
    provider_keys: dict[str, bool],
) -> str:
    """Short string telling the UI what's still needed. Cheap heuristic."""
    if not has_workspace:
        return "pick_workspace"
    if not (has_any_key or local):
        return "pick_provider"
    return "done"


@router.get("/status")
async def onboarding_status() -> dict[str, Any]:
    load_env()
    settings = load_config()
    workspace = get_workspace_dir()
    has_workspace = workspace.exists()

    provider_keys = {
        name: bool(os.environ.get(env_var)) for name, env_var in PROVIDER_KEY_ENV.items()
    }
    has_any_api_key = any(provider_keys.values())
    local = local_ready()
    completed = has_workspace and (has_any_api_key or local)

    return {
        "completed": completed,
        "has_workspace": has_workspace,
        "has_any_api_key": has_any_api_key,
        "local_ready": local,
        "provider_keys": provider_keys,
        "current_provider": settings.provider,
        "recommended_next_step": _recommended_next_step(
            has_workspace, has_any_api_key, local, provider_keys
        ),
    }


@router.post("/save")
async def save_onboarding(req: OnboardingSaveRequest) -> dict[str, Any]:
    """Single round-trip save — validates + writes config + secrets + vault.

    Local provider setup (if picked) runs *synchronously* inside this call —
    it can take minutes for large models, so Web UI callers should hit
    ``/api/local/setup`` for a streaming flow instead of going through this
    endpoint when the user picks local. This endpoint still supports it for
    CLI-like parity.
    """
    try:
        result = run_headless_onboard(
            provider=req.provider,
            api_key=req.api_key,
            workspace=req.workspace,
            language=req.language,
            keep_media=req.keep_media,
            output_format=req.output_format,
            local_model=req.local_model,
            extra_api_keys=req.extra_api_keys,
            instagram_browser=req.instagram_browser,
        )
    except OnboardValidationError as e:
        raise HTTPException(status_code=400, detail=e.payload)

    return result
