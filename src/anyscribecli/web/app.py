"""FastAPI application factory for the scribe web UI."""

from __future__ import annotations

import webbrowser
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from anyscribecli import __version__

STATIC_DIR = Path(__file__).parent / "static"


def create_app() -> FastAPI:
    """Build and return the FastAPI application."""
    app = FastAPI(
        title="scribe",
        version=__version__,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )

    # Import and include route modules
    from anyscribecli.web.routes.config import router as config_router
    from anyscribecli.web.routes.health import router as health_router
    from anyscribecli.web.routes.history import router as history_router
    from anyscribecli.web.routes.local import router as local_router
    from anyscribecli.web.routes.models import router as models_router
    from anyscribecli.web.routes.onboarding import router as onboarding_router
    from anyscribecli.web.routes.system import router as system_router
    from anyscribecli.web.routes.transcribe import router as transcribe_router

    app.include_router(health_router)
    app.include_router(config_router)
    app.include_router(history_router)
    app.include_router(transcribe_router)
    app.include_router(system_router)
    app.include_router(local_router)
    app.include_router(models_router)
    app.include_router(onboarding_router)

    # Serve built React SPA from static/
    if STATIC_DIR.exists() and (STATIC_DIR / "index.html").exists():
        # Mount static assets (JS, CSS, images)
        app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="assets")

        # SPA catch-all: any non-API path serves index.html for client-side routing
        @app.get("/{full_path:path}")
        async def spa_fallback(request: Request, full_path: str) -> FileResponse:
            # Serve actual files if they exist (favicon.svg, etc.)
            file_path = STATIC_DIR / full_path
            if full_path and file_path.is_file():
                return FileResponse(file_path)
            return FileResponse(STATIC_DIR / "index.html")

    return app


def run(host: str = "127.0.0.1", port: int = 8457, open_browser: bool = True) -> None:
    """Start the uvicorn server."""
    import uvicorn

    app = create_app()
    config = uvicorn.Config(app, host=host, port=port, log_level="warning")
    server = uvicorn.Server(config)

    # Stash server on app.state so /shutdown route can access it
    app.state.server = server

    if open_browser:

        @app.on_event("startup")
        async def _open_browser() -> None:
            webbrowser.open(f"http://{host}:{port}")

    server.run()
