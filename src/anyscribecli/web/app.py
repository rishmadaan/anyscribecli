"""FastAPI application factory for the scribe web UI."""

from __future__ import annotations

import webbrowser
from pathlib import Path

from fastapi import FastAPI
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
    from anyscribecli.web.routes.transcribe import router as transcribe_router

    app.include_router(health_router)
    app.include_router(config_router)
    app.include_router(history_router)
    app.include_router(transcribe_router)

    # Serve built React SPA from static/ (production mode)
    if STATIC_DIR.exists() and (STATIC_DIR / "index.html").exists():
        app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")

    return app


def run(host: str = "127.0.0.1", port: int = 8457, open_browser: bool = True) -> None:
    """Start the uvicorn server."""
    import uvicorn

    app = create_app()
    config = uvicorn.Config(app, host=host, port=port, log_level="warning")
    server = uvicorn.Server(config)

    if open_browser:

        @app.on_event("startup")
        async def _open_browser() -> None:
            webbrowser.open(f"http://{host}:{port}")

    server.run()
