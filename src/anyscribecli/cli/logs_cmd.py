"""Logs command — view recent daily processing logs and recovery artifacts."""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime

import typer
from rich.console import Console

from anyscribecli.config.paths import RECOVERY_DIR, get_workspace_dir

console = Console()
err_console = Console(stderr=True)


def logs(
    limit: int = typer.Option(20, "--limit", "-n", help="Number of log entries to show."),
    output_json: bool = typer.Option(False, "--json", "-j", help="Output result as JSON."),
) -> None:
    """[bold]View recent activity[/bold] — daily processing logs and recovery artifacts.

    Reads the workspace's daily/*.md logs (newest first) and lists any files
    saved in the recovery directory after a failed transcription.
    """
    daily_dir = get_workspace_dir() / "daily"
    entries: list[dict] = []

    if daily_dir.is_dir():
        for daily_file in sorted(daily_dir.glob("*.md"), reverse=True):
            date = daily_file.stem
            for row in _parse_rows(daily_file.read_text()):
                row["date"] = date
                entries.append(row)
                if len(entries) >= limit:
                    break
            if len(entries) >= limit:
                break

    recovery: list[dict] = []
    if RECOVERY_DIR.is_dir():
        for item in sorted(RECOVERY_DIR.rglob("*")):
            if item.is_file():
                stat = item.stat()
                recovery.append(
                    {
                        "name": str(item.relative_to(RECOVERY_DIR)),
                        "size": stat.st_size,
                        "mtime": datetime.fromtimestamp(stat.st_mtime).isoformat(
                            timespec="seconds"
                        ),
                    }
                )

    if output_json:
        json.dump(
            {"success": True, "data": {"entries": entries, "recovery": recovery}, "error": None},
            sys.stdout,
            indent=2,
        )
        sys.stdout.write("\n")
        return

    if not entries:
        console.print("No activity logged yet.")
    else:
        console.print(f"[bold]Recent activity[/bold] (last {len(entries)}):\n")
        for e in entries:
            title = e["entry"].rsplit("|", 1)[-1].removesuffix("]]")
            console.print(f"  [dim]{e['date']} {e['time']}[/dim]  {e['platform']:<10} {title}")

    if recovery:
        console.print(
            "\n[bold yellow]Recovery artifacts[/bold yellow] "
            "[dim](audio saved from failed transcriptions — re-run scribe to retry, or delete)[/dim]"
        )
        for r in recovery:
            console.print(f"  {r['name']}  [dim]{_human_size(r['size'])}  {r['mtime']}[/dim]")


_ROW_RE = re.compile(
    r"^\|\s*(?P<time>[^|]+?)\s*\|\s*(?P<platform>[^|]+?)\s*\|\s*(?P<entry>\[\[.*?\]\])\s*\|\s*(?P<duration>[^|]+?)\s*\|$"
)


def _parse_rows(content: str) -> list[dict]:
    """Parse daily-log markdown table rows, newest-first (rows are prepended).

    The entry cell is a `[[path|title]]` wikilink, which itself contains a
    pipe — a naive split("|") breaks on it, so match the row shape instead.
    """
    rows = []
    for line in content.splitlines():
        line = line.strip()
        if not line.startswith("|") or line.startswith("|---") or line.startswith("| Time"):
            continue
        m = _ROW_RE.match(line)
        if not m:
            continue
        rows.append(m.groupdict())
    return rows


def _human_size(n: int) -> str:
    size = float(n)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024:
            return f"{size:.0f}{unit}" if unit == "B" else f"{size:.1f}{unit}"
        size /= 1024
    return f"{size:.1f}TB"
