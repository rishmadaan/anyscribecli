"""Transcript history endpoints — reads from the Obsidian vault."""

from __future__ import annotations

from pathlib import Path

import yaml
from fastapi import APIRouter, HTTPException

from anyscribecli.config.paths import get_workspace_dir

router = APIRouter(prefix="/api", tags=["history"])


def _scan_transcripts(
    platform: str | None = None,
    limit: int = 50,
    workspace: Path | None = None,
) -> list[dict]:
    """Scan vault markdown files and return metadata from frontmatter.

    Shared utility — used by both web routes and MCP server.
    """
    ws = workspace or get_workspace_dir()
    sources = ws / "sources"

    if not sources.is_dir():
        return []

    search_dir = sources / platform if platform else sources
    if not search_dir.is_dir():
        return []

    entries = []
    for md_file in search_dir.rglob("*.md"):
        if md_file.name.startswith("_"):
            continue
        try:
            text = md_file.read_text()
            if not text.startswith("---"):
                continue
            end = text.index("---", 3)
            fm = yaml.safe_load(text[3:end])
            if not isinstance(fm, dict):
                continue
            entries.append(
                {
                    "id": md_file.stem,
                    "title": fm.get("title", md_file.stem),
                    "date": str(fm.get("date_processed", "")),
                    "platform": fm.get("platform", ""),
                    "duration": fm.get("duration", ""),
                    "language": fm.get("language", ""),
                    "word_count": fm.get("word_count", 0),
                    "provider": fm.get("provider", ""),
                    "source_url": fm.get("source", ""),
                    "file_path": str(md_file),
                    "diarized": fm.get("diarized", False),
                }
            )
        except Exception:
            continue

    entries.sort(key=lambda e: e["date"], reverse=True)
    return entries[:limit] if limit else entries


@router.get("/transcripts")
async def list_transcripts(platform: str | None = None, limit: int = 50, offset: int = 0) -> dict:
    all_entries = _scan_transcripts(platform=platform, limit=0)
    total = len(all_entries)
    items = all_entries[offset : offset + limit]
    return {"items": items, "total": total, "offset": offset, "limit": limit}


@router.get("/transcripts/{transcript_id}")
async def get_transcript(transcript_id: str) -> dict:
    """Get a single transcript by its slug (file stem)."""
    ws = get_workspace_dir()
    sources = ws / "sources"

    if not sources.is_dir():
        raise HTTPException(status_code=404, detail="No sources directory")

    # Find the file by stem across all platform subdirectories
    for md_file in sources.rglob("*.md"):
        if md_file.stem == transcript_id:
            text = md_file.read_text()
            frontmatter = {}
            body = text

            if text.startswith("---"):
                try:
                    end = text.index("---", 3)
                    frontmatter = yaml.safe_load(text[3:end]) or {}
                    body = text[end + 3 :].strip()
                except Exception:
                    pass

            return {
                "id": transcript_id,
                "frontmatter": frontmatter,
                "body": body,
                "file_path": str(md_file),
            }

    raise HTTPException(status_code=404, detail=f"Transcript not found: {transcript_id}")


@router.get("/workspace/info")
async def workspace_info() -> dict:
    ws = get_workspace_dir()
    sources = ws / "sources"

    file_count = 0
    total_words = 0

    if sources.is_dir():
        for md_file in sources.rglob("*.md"):
            if md_file.name.startswith("_"):
                continue
            file_count += 1
            try:
                text = md_file.read_text()
                if text.startswith("---"):
                    end = text.index("---", 3)
                    fm = yaml.safe_load(text[3:end])
                    if isinstance(fm, dict):
                        total_words += fm.get("word_count", 0)
            except Exception:
                continue

    return {
        "path": str(ws),
        "file_count": file_count,
        "total_words": total_words,
    }
