---
type: feature
tags: [web-ui, fastapi, react, websocket]
tldr: "Added scribe ui — a local web dashboard (FastAPI + React SPA) wrapping the existing CLI pipeline with real-time transcription progress via WebSocket."
---

# Web UI — Initial Implementation

**Date:** 2026-04-18

## What was built

`scribe ui` launches a local web dashboard at `http://127.0.0.1:8457` that wraps the existing CLI pipeline. Three views:

- **Transcribe** — paste a URL, choose provider/language/diarize options, watch real-time progress, see results with stat cards
- **History** — browse past transcripts from the Obsidian vault, grouped by date, with search
- **Settings** — edit config, view provider status with test buttons, system health

## Architecture decisions

**React SPA over Jinja2+HTMX:** The transcription pipeline has 4 distinct steps (download → transcribe → write → index) that need instant feedback. HTMX polling every 30s would feel broken. WebSocket with event replay was the right call.

**Progress callback over async rewrite:** Added `on_progress` to `process()` instead of rewriting all providers as async. The callback runs in a ThreadPoolExecutor thread and bridges to asyncio.Queue via `call_soon_threadsafe`. Backward-compatible — CLI/MCP callers pass nothing.

**Core dependency, not optional:** Following gitstow's pattern — `fastapi`, `uvicorn`, `websockets` are core deps. One install, one app. Users shouldn't need to know about extras.

**Frontend source at `ui/` root, build output in package:** Node tooling (node_modules, vite config) doesn't belong inside a Python package tree. Build output committed to `src/anyscribecli/web/static/` so `pip install` works without Node.js.

## Files added

- `src/anyscribecli/web/` — FastAPI backend (app.py, jobs.py, progress.py, models.py, routes/)
- `src/anyscribecli/web/routes/` — transcribe, history, config, health, system
- `src/anyscribecli/web/static/` — built React app
- `ui/` — frontend source (React 19 + TypeScript + Vite + Tailwind CSS v4)
- `tests/test_web.py` — 17 smoke tests

## Files modified

- `src/anyscribecli/core/orchestrator.py` — added `on_progress` callback parameter
- `src/anyscribecli/cli/main.py` — added `scribe ui` command with port conflict detection
- `pyproject.toml` — fastapi/uvicorn/websockets as core dependencies

## What's next

- Design polish with frontend-design skill
- Batch transcription view
- Transcript detail view with markdown rendering
