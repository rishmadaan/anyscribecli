"""Health check endpoint."""

from __future__ import annotations

from fastapi import APIRouter

from anyscribecli import __version__

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health")
async def health() -> dict:
    from anyscribecli.core.deps import check_dependencies

    results = check_dependencies()
    deps = {name: found for name, found, _ in results}
    return {
        "ok": all(deps.values()),
        "version": __version__,
        "dependencies": deps,
    }
