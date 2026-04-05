"""Install the scribe Claude Code skill to ~/.claude/skills/scribe/."""

from importlib.resources import as_file
from pathlib import Path

import typer
from rich.console import Console

from anyscribecli.config.paths import (
    ASCLI_SKILL_TARGET,
    CLAUDE_HOME,
    get_skill_source_dir,
)

console = Console()


def copy_skill_files() -> Path:
    """Copy bundled skill files to ~/.claude/skills/scribe/. Returns target path."""
    source = get_skill_source_dir()

    # Create target directories
    refs_dir = ASCLI_SKILL_TARGET / "references"
    refs_dir.mkdir(parents=True, exist_ok=True)

    # Copy SKILL.md
    with as_file(source.joinpath("SKILL.md")) as src:
        (ASCLI_SKILL_TARGET / "SKILL.md").write_text(src.read_text())

    # Copy reference files
    refs_source = source.joinpath("references")
    for name in ("commands.md", "providers.md", "troubleshooting.md", "config.md"):
        with as_file(refs_source.joinpath(name)) as src:
            (refs_dir / name).write_text(src.read_text())

    return ASCLI_SKILL_TARGET


def install_skill(
    force: bool = typer.Option(False, "--force", "-f", help="Overwrite existing skill files"),
) -> None:
    """Install the scribe skill for Claude Code."""
    if not CLAUDE_HOME.exists():
        console.print("\n  [yellow]Claude Code not detected.[/yellow] ~/.claude/ does not exist.")
        console.print("  Install Claude Code first: https://docs.anthropic.com/en/docs/claude-code")
        raise typer.Exit(1)

    if ASCLI_SKILL_TARGET.exists() and not force:
        console.print(f"\n  Skill already installed at [cyan]{ASCLI_SKILL_TARGET}[/cyan]")
        console.print("  Run with [bold]--force[/bold] to overwrite.")
        raise typer.Exit(0)

    target = copy_skill_files()
    console.print(f"\n  [green]✓[/green] Skill installed to [cyan]{target}[/cyan]")
    console.print(
        "  Claude Code can now use [bold]/scribe[/bold] or auto-activate "
        "when you ask it to transcribe."
    )
