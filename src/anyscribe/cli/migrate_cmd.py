"""``anyscribe migrate`` — one-shot move from an old anyscribecli install.

Every existing user runs this once. It does the whole job in five steps and
reports honestly, including what it chose *not* to touch. ``--dry-run`` runs
the same five steps in inspect-only mode and writes nothing at all.
"""

from __future__ import annotations

import json
import os
import shutil
import sys
from pathlib import Path
from typing import Any, Iterator

import typer
from rich.console import Console

console = Console()
err_console = Console(stderr=True)

# `scribe` and `ascli` are permanent aliases, not deprecations — a missing one
# is a broken install, so all three are verified.
VERIFIED_COMMANDS = ("anyscribe", "scribe", "ascli")


# --- formatting -----------------------------------------------------------


def _tilde(p: Path) -> str:
    """Render a path with ``~`` for the home dir, for pasteable output."""
    home = str(Path.home())
    s = str(p)
    return "~" + s[len(home) :] if s.startswith(home) else s


def _size(n: int) -> str:
    mb = n / (1024 * 1024)
    return f"{mb:.1f} MB" if mb >= 0.1 else f"{n / 1024:.0f} KB"


def _env_key_count(env_file: Path) -> int:
    """Count keys in a .env file. Never returns or logs the values."""
    try:
        text = env_file.read_text()
    except OSError:
        return 0
    return sum(
        1 for line in text.splitlines() if "=" in line and not line.lstrip().startswith("#")
    )


def _tree_stats(paths: list[Path]) -> tuple[int, int]:
    """(file count, total bytes) across the given files/dirs."""
    files = 0
    total = 0
    for p in paths:
        for f in [p] if p.is_file() else p.rglob("*"):
            if f.is_file():
                files += 1
                try:
                    total += f.stat().st_size
                except OSError:
                    pass
    return files, total


def _label(p: Path) -> str:
    """`sessions/`, `config.yaml`, or `.env (3 keys)` — never a key value."""
    if p.is_dir():
        return f"{p.name}/"
    if p.name == ".env":
        return f".env ({_env_key_count(p)} keys)"
    return p.name


# --- ~/.claude.json MCP registration --------------------------------------


def _iter_mcp_servers(node: Any) -> Iterator[dict]:
    """Yield every ``mcpServers`` dict in the tree.

    ~/.claude.json carries a top-level block *and* one per project under
    ``projects``, so a top-level-only lookup silently leaves entries behind.
    """
    if isinstance(node, dict):
        servers = node.get("mcpServers")
        if isinstance(servers, dict):
            yield servers
        for v in node.values():
            yield from _iter_mcp_servers(v)
    elif isinstance(node, list):
        for v in node:
            yield from _iter_mcp_servers(v)


def _retarget(s: str, legacy_pkg: str) -> str:
    s = s.replace(legacy_pkg, "anyscribe")
    if "anyscribe-mcp" not in s:
        s = s.replace("scribe-mcp", "anyscribe-mcp")
    return s


def _rekey_scribe_mcp(data: Any, legacy_pkg: str) -> int:
    """Re-key `scribe` MCP entries to `anyscribe` in place. Returns count changed.

    Skips any block that already has an `anyscribe` key — never clobber.
    """
    changed = 0
    # Materialise before mutating: the generator walks the same dicts we edit.
    for servers in list(_iter_mcp_servers(data)):
        entry = servers.get("scribe")
        if not isinstance(entry, dict) or "anyscribe" in servers:
            continue
        args = entry.get("args") or []
        blob = " ".join([str(entry.get("command", ""))] + [str(a) for a in args])
        if "scribe-mcp" not in blob and legacy_pkg not in blob:
            continue
        new = dict(entry)
        if isinstance(entry.get("command"), str):
            new["command"] = _retarget(entry["command"], legacy_pkg)
        if isinstance(args, list):
            new["args"] = [_retarget(a, legacy_pkg) if isinstance(a, str) else a for a in args]
        servers["anyscribe"] = new
        del servers["scribe"]
        changed += 1
    return changed


def _migrate_mcp(claude_json: Path, legacy_pkg: str, dry_run: bool) -> tuple[int, str | None]:
    """Step 4. Returns (entries changed, warning). Never raises, never truncates."""
    if not claude_json.is_file():
        return 0, None  # No Claude Code MCP config — nothing to migrate.
    try:
        data = json.loads(claude_json.read_text())
    except (OSError, ValueError) as e:
        return 0, f"{_tilde(claude_json)} could not be read as JSON ({e}) — skipped, not touched."

    changed = _rekey_scribe_mcp(data, legacy_pkg)
    if not changed or dry_run:
        return changed, None

    backup = claude_json.with_name(claude_json.name + ".bak")
    shutil.copy2(claude_json, backup)
    # Temp file in the same dir + os.replace: a crash can never leave the
    # user's (large, irreplaceable) ~/.claude.json half-written.
    tmp = claude_json.with_name(claude_json.name + ".tmp")
    tmp.write_text(json.dumps(data, indent=2) + "\n")
    os.replace(tmp, claude_json)
    return changed, None


# --- the command ----------------------------------------------------------


def migrate(
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Show exactly what would change and write nothing."
    ),
    output_json: bool = typer.Option(False, "--json", "-j", help="Output result as JSON."),
) -> None:
    """[bold]Migrate[/bold] an old anyscribecli install to anyscribe.

    Moves the config directory, refreshes the Claude Code skill, re-points the
    MCP registration, and verifies the commands. Safe to run twice.
    """
    from anyscribe import __version__
    from anyscribe.cli.skill_cmd import copy_skill_files
    from anyscribe.config.paths import (
        APP_HOME,
        ASCLI_SKILL_TARGET,
        CLAUDE_HOME,
        CLAUDE_SKILLS_DIR,
        LEGACY_APP_HOME,
    )
    from anyscribe.core.migrate import app_home_moves, maybe_migrate_app_home

    # Constraint: the old package name lives in exactly one constant.
    legacy_pkg = LEGACY_APP_HOME.name.lstrip(".")

    lines: list[str] = []
    warnings: list[str] = []
    data: dict[str, Any] = {"dry_run": dry_run}

    # 1. Config directory — one decision table, shared with the real run.
    moves = app_home_moves()
    n_files, n_bytes, labels = 0, 0, []
    if moves:
        srcs = (
            sorted(LEGACY_APP_HOME.iterdir())
            if moves[0][0] == LEGACY_APP_HOME
            else [s for s, _ in moves]
        )
        n_files, n_bytes = _tree_stats(srcs)
        labels = [_label(s) for s in srcs]
        lines.append(
            f"  {_tilde(LEGACY_APP_HOME)}  →  {_tilde(APP_HOME)}"
            f"        {n_files} files, {_size(n_bytes)}"
        )
        lines.append(f"    {', '.join(labels)}")
        if not dry_run:
            maybe_migrate_app_home()
    elif LEGACY_APP_HOME.is_dir():
        warnings.append(
            f"{_tilde(LEGACY_APP_HOME)} still exists but nothing was moved — "
            f"{_tilde(APP_HOME)} is already set up, or a transcription is running."
        )
    data["app_home"] = {
        "from": str(LEGACY_APP_HOME),
        "to": str(APP_HOME),
        "files": n_files,
        "bytes": n_bytes,
        "entries": labels,
    }

    # 2. Stale skill dir — the one directory removal this tool is allowed.
    stale_skill = CLAUDE_SKILLS_DIR / "scribe"
    stale_removed = stale_skill.is_dir()
    if stale_removed:
        lines.append(f"  {_tilde(stale_skill)}/  →  remove (stale)")
        if not dry_run:
            shutil.rmtree(stale_skill)
    data["stale_skill_removed"] = stale_removed

    # 3. Skill install. Only where Claude Code exists — don't conjure ~/.claude.
    skill_installed = False
    if CLAUDE_HOME.is_dir():
        try:
            installed = (ASCLI_SKILL_TARGET / ".version").read_text().strip()
        except OSError:
            installed = ""
        if installed != __version__:
            skill_installed = True
            lines.append(f"  {_tilde(ASCLI_SKILL_TARGET)}/  →  install")
            if not dry_run:
                copy_skill_files()
    data["skill_installed"] = skill_installed

    # 4. MCP registration in ~/.claude.json.
    claude_json = CLAUDE_HOME.with_name(CLAUDE_HOME.name + ".json")
    mcp_changed, mcp_warning = _migrate_mcp(claude_json, legacy_pkg, dry_run)
    if mcp_warning:
        warnings.append(mcp_warning)
    if mcp_changed:
        lines.append(f'  {_tilde(claude_json)}  mcp "scribe" → "anyscribe"  ×{mcp_changed}')
    data["mcp_entries_updated"] = mcp_changed

    # 5. Verification — report only; repairing PATH is not this tool's job.
    found = {name: shutil.which(name) for name in VERIFIED_COMMANDS}
    lines.append(
        "  commands: "
        + "  ".join(f"{n} {'✓' if found[n] else '✗'}" for n in VERIFIED_COMMANDS)
    )
    data["commands"] = {n: found[n] for n in VERIFIED_COMMANDS}

    missing = [n for n, p in found.items() if not p]
    if missing:
        warnings.append(
            f"not on PATH: {', '.join(missing)} — run "
            f"'pip install --force-reinstall anyscribe'."
        )

    data["changed"] = bool(moves or stale_removed or skill_installed or mcp_changed)
    data["warnings"] = warnings

    if output_json:
        json.dump({"success": True, "data": data, "error": None}, sys.stdout, indent=2)
        sys.stdout.write("\n")
        return

    console.print()
    if not data["changed"]:
        console.print("  [green]nothing to do[/green] — already migrated to anyscribe.")
    for line in lines:
        console.print(line, highlight=False)
    for w in warnings:
        console.print(f"  [yellow]![/yellow] {w}")
    if dry_run:
        console.print("  [dim]nothing written (--dry-run)[/dim]")
    console.print()
