"""Maintain vault indexes — master MOC and daily logs."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from anyscribecli.config.paths import get_workspace_dir
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
            index_file.write_text("\n".join(lines))
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

    if not daily_file.exists():
        header = (
            f"# Processing Log — {today}\n\n"
            f"| Time | Platform | Entry | Duration |\n"
            f"|------|----------|-------|----------|\n"
        )
        daily_file.write_text(header)

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
        daily_file.write_text("\n".join(lines))
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
