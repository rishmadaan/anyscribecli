"""scribe — main CLI entry point."""

from __future__ import annotations

from typing import Optional

import click
import typer
from typer.core import TyperGroup
from rich.console import Console

from anyscribecli import __version__


class DefaultToTranscribe(TyperGroup):
    """Route bare URLs/paths to the transcribe command automatically.

    If the first argument isn't a known subcommand or a flag,
    assume it's a URL or file path and prepend 'transcribe'.
    This lets users write `scribe "https://..."` instead of
    `scribe transcribe "https://..."`.
    """

    def parse_args(self, ctx: click.Context, args: list[str]) -> list[str]:
        if args and args[0] not in self.commands and not args[0].startswith("-"):
            args = ["transcribe"] + args
        return super().parse_args(ctx, args)


app = typer.Typer(
    name="scribe",
    cls=DefaultToTranscribe,
    help="Download, transcribe, and convert video/audio to structured markdown.",
    rich_markup_mode="rich",
    no_args_is_help=True,
)

console = Console()
err_console = Console(stderr=True)


def version_callback(value: bool) -> None:
    if value:
        console.print(f"scribe v{__version__}")
        raise typer.Exit()


def _auto_update_skill() -> None:
    """Silently install or update the Claude Code skill.

    AI-first app: if Claude Code is present (~/.claude/ exists), the skill
    is always installed and kept current. No opt-in required.

    Checks a .version marker file in the installed skill directory.
    If it doesn't match the current package version, re-copies all skill files.
    This runs on every invocation but is fast (one file read + string compare).

    Also handles one-time migration from the old ``ascli`` skill dir to ``scribe``.
    """
    import shutil

    from anyscribecli.config.paths import ASCLI_SKILL_TARGET, CLAUDE_HOME, CLAUDE_SKILLS_DIR

    # No Claude Code → nothing to do
    if not CLAUDE_HOME.exists():
        return

    # Migrate old 'ascli' skill → 'scribe' (one-time, v0.5.4 → v0.5.5+)
    old_skill_dir = CLAUDE_SKILLS_DIR / "ascli"
    if old_skill_dir.exists():
        try:
            shutil.rmtree(old_skill_dir)
        except Exception:
            pass

    if not ASCLI_SKILL_TARGET.exists():
        # Claude Code present but skill not installed — auto-install
        try:
            from anyscribecli.cli.skill_cmd import copy_skill_files

            copy_skill_files(quiet=True)
        except Exception:
            pass
        return

    # Skill exists — check version marker
    version_marker = ASCLI_SKILL_TARGET / ".version"
    try:
        installed_version = version_marker.read_text().strip()
    except (FileNotFoundError, OSError):
        installed_version = ""

    if installed_version == __version__:
        return  # Already up to date

    # Version mismatch — silently update
    try:
        from anyscribecli.cli.skill_cmd import copy_skill_files

        copy_skill_files(quiet=True)
    except Exception:
        pass  # Never block CLI on skill update failure


def _check_path_windows() -> None:
    """On Windows, warn once if `scribe` is not on PATH and print the fix command."""
    import platform
    import shutil

    if platform.system() != "Windows":
        return
    if shutil.which("scribe") is not None:
        return

    import sysconfig

    from anyscribecli.config.paths import APP_HOME

    # Only warn once — write a marker file after first warning
    marker = APP_HOME / ".path_warned"
    if marker.exists():
        return

    scripts_dir = sysconfig.get_path("scripts")
    console.print()
    console.print("[bold yellow]scribe is not on your PATH.[/bold yellow]")
    console.print("Run this command in PowerShell to fix it permanently:\n")
    console.print(
        f'  [bold cyan]$env:Path += ";{scripts_dir}"; '
        f"[Environment]::SetEnvironmentVariable('Path', "
        f"[Environment]::GetEnvironmentVariable('Path', 'User') + ';{scripts_dir}', "
        f"'User')[/bold cyan]\n"
    )
    console.print("Then restart your terminal and use [bold]scribe[/bold] directly.\n")
    APP_HOME.mkdir(parents=True, exist_ok=True)
    marker.touch()


@app.callback()
def main(
    version: Optional[bool] = typer.Option(
        None,
        "--version",
        "-v",
        help="Show version and exit.",
        callback=version_callback,
        is_eager=True,
    ),
) -> None:
    """[bold]scribe[/bold] — download, transcribe, and convert video/audio to structured markdown."""
    _auto_update_skill()
    _check_path_windows()


# Register commands
from anyscribecli.cli.onboard import onboard  # noqa: E402
from anyscribecli.cli.transcribe import transcribe  # noqa: E402
from anyscribecli.cli.config_cmd import config_app, providers_app  # noqa: E402
from anyscribecli.cli.batch import batch  # noqa: E402
from anyscribecli.cli.download import download  # noqa: E402
from anyscribecli.cli.skill_cmd import install_skill  # noqa: E402

app.command()(onboard)
app.command()(transcribe)
app.command()(batch)
app.command()(download)
app.command("install-skill")(install_skill)
app.add_typer(config_app, name="config")
app.add_typer(providers_app, name="providers")


@app.command()
def update(
    force: bool = typer.Option(
        False, "--force", "-f", help="Force update even with local changes."
    ),
    check: bool = typer.Option(
        False, "--check", "-c", help="Only check for updates, don't install."
    ),
) -> None:
    """[bold yellow]Update[/bold yellow] scribe to the latest version.

    Pulls the latest changes from git and reinstalls the package.
    """
    from anyscribecli.core.updater import check_for_updates, update as do_update

    if check:
        check_for_updates(quiet=False)
    else:
        success = do_update(force=force)
        if not success:
            raise typer.Exit(code=1)


@app.command()
def doctor() -> None:
    """[bold]Check[/bold] system health — dependencies, config, and workspace.

    Runs all diagnostic checks and reports status.
    """
    from anyscribecli.core.deps import check_dependencies, print_dependency_status
    from anyscribecli.config.paths import APP_HOME, CONFIG_FILE, ENV_FILE, get_workspace_dir
    from anyscribecli.core.updater import get_install_path, check_for_updates

    console.print("[bold]scribe doctor[/bold]\n")

    # Dependencies
    console.print("[bold]1. System Dependencies[/bold]\n")
    results = check_dependencies()
    print_dependency_status(results)

    # Config
    console.print("\n[bold]2. Configuration[/bold]\n")
    checks = [
        ("App directory", APP_HOME.exists()),
        ("Config file", CONFIG_FILE.exists()),
        ("API keys file", ENV_FILE.exists()),
        ("Workspace vault", get_workspace_dir().exists()),
        ("Workspace index", (get_workspace_dir() / "_index.md").exists()),
    ]
    for name, ok in checks:
        status = "[green]OK[/green]" if ok else "[red]Missing[/red]"
        console.print(f"  {name}: {status}")

    if not CONFIG_FILE.exists():
        console.print("\n  [yellow]Run [bold]scribe onboard[/bold] to set up.[/yellow]")

    # Install info
    console.print("\n[bold]3. Installation[/bold]\n")
    console.print(f"  Version: v{__version__}")
    repo = get_install_path()
    if repo:
        console.print("  Install type: git (editable)")
        console.print(f"  Repo path: {repo}")
    else:
        console.print("  Install type: pip package")

    # Claude Code skill
    from anyscribecli.config.paths import ASCLI_SKILL_TARGET

    console.print("\n[bold]4. Claude Code Skill[/bold]\n")
    if not ASCLI_SKILL_TARGET.exists():
        console.print("  Skill: [yellow]Not installed[/yellow]")
        console.print("  [dim]Run [bold]scribe install-skill[/bold] to install.[/dim]")
    else:
        version_marker = ASCLI_SKILL_TARGET / ".version"
        try:
            installed_version = version_marker.read_text().strip()
        except (FileNotFoundError, OSError):
            installed_version = "unknown"

        if installed_version == __version__:
            console.print(f"  Skill: [green]Installed (v{installed_version})[/green]")
        elif installed_version == "unknown":
            console.print("  Skill: [yellow]Installed (version unknown — pre-0.5.5)[/yellow]")
            console.print("  [dim]Run [bold]scribe install-skill --force[/bold] to update.[/dim]")
        else:
            console.print(
                f"  Skill: [yellow]Outdated (v{installed_version} → v{__version__})[/yellow]"
            )
            console.print("  [dim]Run [bold]scribe install-skill --force[/bold] to update.[/dim]")
        console.print(f"  Path: {ASCLI_SKILL_TARGET}")

    # Updates
    console.print()
    check_for_updates(quiet=True)
