"""Maintain vault indexes — master MOC and daily logs."""

from __future__ import annotations

import yaml
from datetime import date
from pathlib import Path

from anyscribecli.config.paths import get_workspace_dir
from anyscribecli.core.fileutil import atomic_write, file_lock
from anyscribecli.downloaders.base import DownloadResult
from anyscribecli.vault.writer import format_duration


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
