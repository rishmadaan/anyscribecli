"""Maintain vault indexes — master MOC and daily logs."""

from __future__ import annotations

import yaml
from datetime import date
from pathlib import Path

from anyscribe.config.paths import get_workspace_dir
from anyscribe.core.fileutil import atomic_write, file_lock
from anyscribe.downloaders.base import DownloadResult
from anyscribe.vault.writer import format_duration


def update_master_index(
    entry_path: Path,
    download: DownloadResult,
    duration_str: str,
    workspace: Path | None = None,
) -> None:
    """Prepend a new row to _index.md."""
    ws = workspace or get_workspace_dir()
    index_file = ws / "_index.md"

    today = date.today().isoformat()
    # Relative path from workspace root for Obsidian link
    rel_path = entry_path.relative_to(ws)
    link = f"[[{rel_path}|{download.title}]]"

    new_row = f"| {today} | {download.platform} | {link} | {duration_str} | {download.title} |"

    with file_lock(index_file):
        if index_file.exists():
            content = index_file.read_text()
            lines = content.split("\n")

            # Find the table header separator (|---|...) and insert after it
            insert_idx = None
            for i, line in enumerate(lines):
                if line.strip().startswith("|---"):
                    insert_idx = i + 1
                    break

            if insert_idx is not None:
                lines.insert(insert_idx, new_row)
                atomic_write(index_file, "\n".join(lines))
                return

        # Fallback: append to file
        with open(index_file, "a") as f:
            f.write(new_row + "\n")


def update_daily_log(
    entry_path: Path,
    download: DownloadResult,
    duration_str: str,
    workspace: Path | None = None,
) -> None:
    """Create or update the daily processing log."""
    ws = workspace or get_workspace_dir()
    today = date.today().isoformat()
    daily_dir = ws / "daily"
    daily_dir.mkdir(parents=True, exist_ok=True)
    daily_file = daily_dir / f"{today}.md"

    rel_path = entry_path.relative_to(ws)
    link = f"[[{rel_path}|{download.title}]]"

    with file_lock(daily_file):
        if not daily_file.exists():
            header = (
                f"# Processing Log — {today}\n\n"
                f"| Time | Platform | Entry | Duration |\n"
                f"|------|----------|-------|----------|\n"
            )
            atomic_write(daily_file, header)

        from datetime import datetime

        now = datetime.now().strftime("%H:%M")
        row = f"| {now} | {download.platform} | {link} | {duration_str} |"

        content = daily_file.read_text()
        lines = content.split("\n")

        # Insert after table header separator
        insert_idx = None
        for i, line in enumerate(lines):
            if line.strip().startswith("|---"):
                insert_idx = i + 1
                break

        if insert_idx is not None:
            lines.insert(insert_idx, row)
            atomic_write(daily_file, "\n".join(lines))
        else:
            with open(daily_file, "a") as f:
                f.write(row + "\n")


def update_indexes(
    entry_path: Path,
    download: DownloadResult,
    workspace: Path | None = None,
) -> None:
    """Update all indexes after a new transcript is written."""
    duration_str = format_duration(download.duration)
    update_master_index(entry_path, download, duration_str, workspace)
    update_daily_log(entry_path, download, duration_str, workspace)


def remove_from_index(file_path: Path, workspace: Path | None = None) -> None:
    """Remove a transcript's row from _index.md.

    Daily logs are left untouched — they are append-only history.
    """
    ws = workspace or get_workspace_dir()
    index_file = ws / "_index.md"
    if not index_file.exists():
        return

    try:
        rel_path = file_path.resolve().relative_to(ws.resolve())
    except ValueError:
        return

    marker = f"[[{rel_path}|"
    with file_lock(index_file):
        lines = index_file.read_text().split("\n")
        kept = [line for line in lines if marker not in line]
        if len(kept) != len(lines):
            atomic_write(index_file, "\n".join(kept))


def find_transcript(target: str, workspace: Path | None = None) -> list[Path]:
    """Resolve a path or slug to matching transcript files.

    A path that exists is returned as-is; otherwise the slug is searched
    across sources/*/<slug>.md. Returns all matches (may be ambiguous).
    """
    ws = workspace or get_workspace_dir()
    p = Path(target).expanduser()
    if p.is_file():
        return [p]
    sources = ws / "sources"
    if not sources.is_dir():
        return []
    return sorted(sources.rglob(f"{target}.md"))


def delete_transcript(file_path: Path, workspace: Path | None = None) -> None:
    """Delete a transcript file and remove its row from the master index.

    Raises ValueError if the path is outside the workspace sources/ tree,
    FileNotFoundError if the file doesn't exist.
    """
    ws = (workspace or get_workspace_dir()).resolve()
    resolved = file_path.expanduser().resolve()
    try:
        resolved.relative_to(ws / "sources")
    except ValueError:
        raise ValueError(f"Refusing to delete outside workspace sources/: {file_path}") from None
    if not resolved.is_file():
        raise FileNotFoundError(f"Transcript not found: {file_path}")
    resolved.unlink()
    remove_from_index(resolved, ws)


def rebuild_master_index(workspace: Path | None = None) -> None:
    """Rebuild _index.md from scratch by scanning all transcript files.

    Reads frontmatter from each .md file in sources/, rebuilds the index
    with correct relative links. Sorted newest-first by date_processed.
    """
    ws = workspace or get_workspace_dir()
    sources = ws / "sources"
    index_file = ws / "_index.md"

    if not sources.is_dir():
        return

    entries: list[dict] = []
    for md_file in sources.rglob("*.md"):
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
            rel_path = md_file.relative_to(ws)
            entries.append(
                {
                    "date": fm.get("date_processed", ""),
                    "platform": fm.get("platform", ""),
                    "title": fm.get("title", md_file.stem),
                    "duration": fm.get("duration", ""),
                    "link": f"[[{rel_path}|{fm.get('title', md_file.stem)}]]",
                }
            )
        except Exception:
            continue

    # Sort newest first
    entries.sort(key=lambda e: e["date"], reverse=True)

    lines = [
        "# Transcripts\n",
        "",
        "| Date | Platform | Entry | Duration | Title |",
        "|------|----------|-------|----------|-------|",
    ]
    for e in entries:
        lines.append(
            f"| {e['date']} | {e['platform']} | {e['link']} | {e['duration']} | {e['title']} |"
        )
    lines.append("")

    atomic_write(index_file, "\n".join(lines))
