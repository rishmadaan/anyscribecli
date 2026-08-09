"""anyscribe — main CLI entry point."""

from __future__ import annotations

from typing import Optional

import click
import typer
from typer.core import TyperGroup
from rich.console import Console

from anyscribe import __version__


class DefaultToTranscribe(TyperGroup):
    """Route bare URLs/paths to the transcribe command automatically.

    If the first argument isn't a known subcommand or a flag,
    assume it's a URL or file path and prepend 'transcribe'.
    This lets users write `anyscribe "https://..."` instead of
    `anyscribe transcribe "https://..."`.
    """

    def parse_args(self, ctx: click.Context, args: list[str]) -> list[str]:
        if args and args[0] not in self.commands and not args[0].startswith("-"):
            args = ["transcribe"] + args
        return super().parse_args(ctx, args)


app = typer.Typer(
    name="anyscribe",
    cls=DefaultToTranscribe,
    help="Download, transcribe, and convert video/audio to structured markdown.",
    rich_markup_mode="rich",
    no_args_is_help=True,
)

console = Console()
err_console = Console(stderr=True)

# How far past --port `anyscribe ui` will look for a free port.
PORT_SCAN_SPAN = 10


def version_callback(value: bool) -> None:
    if value:
        console.print(f"anyscribe v{__version__}")
        raise typer.Exit()


def _auto_update_skill() -> None:
    """Silently install or update the Claude Code skill.

    AI-first app: if Claude Code is present (~/.claude/ exists), the skill
    is always installed and kept current. No opt-in required.

    Checks a .version marker file in the installed skill directory.
    If it doesn't match the current package version, re-copies all skill files.
    This runs on every invocation but is fast (one file read + string compare).

    Also drops superseded skill dirs (``ascli``, then ``scribe``) so Claude Code
    never sees two competing anyscribe skills, one of them serving stale commands.
    """
    import shutil

    from anyscribe.config.paths import ASCLI_SKILL_TARGET, CLAUDE_HOME, CLAUDE_SKILLS_DIR

    # No Claude Code → nothing to do
    if not CLAUDE_HOME.exists():
        return

    # Superseded skill dirs: 'ascli' (v0.5.4 → v0.5.5+), 'scribe' (→ 'anyscribe').
    # This is the silent path every existing user hits, so the cleanup belongs
    # here rather than in `skill install`.
    for stale_name in ("ascli", "scribe"):
        stale_dir = CLAUDE_SKILLS_DIR / stale_name
        if stale_dir.exists():
            try:
                shutil.rmtree(stale_dir)
            except Exception:
                pass

    if not ASCLI_SKILL_TARGET.exists():
        # Claude Code present but skill not installed — auto-install
        try:
            from anyscribe.cli.skill_cmd import copy_skill_files

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
        from anyscribe.cli.skill_cmd import copy_skill_files

        copy_skill_files(quiet=True)
    except Exception:
        pass  # Never block CLI on skill update failure


def _check_path_windows() -> None:
    """On Windows, warn once if `anyscribe` is not on PATH and print the fix command."""
    import platform
    import shutil

    if platform.system() != "Windows":
        return
    if shutil.which("anyscribe") is not None:
        return

    import sysconfig

    from anyscribe.config.paths import APP_HOME

    # Only warn once — write a marker file after first warning
    marker = APP_HOME / ".path_warned"
    if marker.exists():
        return

    scripts_dir = sysconfig.get_path("scripts")
    console.print()
    console.print("[bold yellow]anyscribe is not on your PATH.[/bold yellow]")
    console.print("Run this command in PowerShell to fix it permanently:\n")
    console.print(
        f'  [bold cyan]$env:Path += ";{scripts_dir}"; '
        f"[Environment]::SetEnvironmentVariable('Path', "
        f"[Environment]::GetEnvironmentVariable('Path', 'User') + ';{scripts_dir}', "
        f"'User')[/bold cyan]\n"
    )
    console.print("Then restart your terminal and use [bold]anyscribe[/bold] directly.\n")
    APP_HOME.mkdir(parents=True, exist_ok=True)
    marker.touch()


# Module-level debug flag — checked by CLI error handlers
_debug_mode = False


@app.callback()
def main(
    ctx: typer.Context,
    version: Optional[bool] = typer.Option(
        None,
        "--version",
        "-v",
        help="Show version and exit.",
        callback=version_callback,
        is_eager=True,
    ),
    debug: bool = typer.Option(
        False,
        "--debug",
        help="Enable debug output with full tracebacks and log to ~/.anyscribe/logs/scribe.log.",
    ),
) -> None:
    """[bold]anyscribe[/bold] — download, transcribe, and convert video/audio to structured markdown."""
    global _debug_mode
    _debug_mode = debug
    if debug:
        import logging

        from anyscribe.config.paths import LOGS_DIR

        LOGS_DIR.mkdir(parents=True, exist_ok=True)
        logging.basicConfig(
            level=logging.DEBUG,
            format="%(asctime)s %(name)s %(levelname)s %(message)s",
            handlers=[
                logging.FileHandler(LOGS_DIR / "scribe.log"),
                logging.StreamHandler(),
            ],
        )
    # `migrate` does the skill install itself, visibly, and honours --dry-run.
    # Letting the silent auto-updater run first would remove the stale skill
    # dir and write skill files before a `--dry-run` had reported anything —
    # the one flag whose whole value is that it writes nothing.
    if ctx.invoked_subcommand != "migrate":
        _auto_update_skill()
        _check_path_windows()


# Register commands
from anyscribe.cli.onboard import onboard  # noqa: E402
from anyscribe.cli.transcribe import transcribe  # noqa: E402
from anyscribe.cli.config_cmd import config_app, providers_app  # noqa: E402
from anyscribe.cli.batch import batch  # noqa: E402
from anyscribe.cli.download import download  # noqa: E402
from anyscribe.cli.rm import rm  # noqa: E402
from anyscribe.cli.logs_cmd import logs  # noqa: E402
from anyscribe.cli.migrate_cmd import migrate  # noqa: E402
from anyscribe.cli.skill_cmd import install_skill  # noqa: E402
from anyscribe.cli.local_cmd import local_app  # noqa: E402
from anyscribe.cli.models_cmd import models_app  # noqa: E402
from anyscribe.cli.tray_cmd import tray  # noqa: E402
from anyscribe.cli.service_cmd import install_service, uninstall_service  # noqa: E402

app.command()(onboard)
app.command()(transcribe)
app.command()(batch)
app.command()(download)
app.command()(rm)
app.command()(logs)
app.command()(migrate)
app.command("install-skill")(install_skill)
app.command()(tray)
app.command("install-service")(install_service)
app.command("uninstall-service")(uninstall_service)
app.add_typer(config_app, name="config")
app.add_typer(providers_app, name="providers")
app.add_typer(local_app, name="local")
app.add_typer(models_app, name="model")


@app.command()
def ui(
    port: int = typer.Option(8457, "--port", "-p", help="Port to listen on."),
    no_open: bool = typer.Option(False, "--no-open", help="Don't auto-open browser."),
) -> None:
    """Launch the [bold]web UI[/bold] in your browser.

    Starts a local web server and opens the anyscribe dashboard.
    """
    import socket

    from anyscribe.web.app import run

    # A busy port is nearly always our own second window or a stale server, so
    # roll forward instead of dead-ending the user. Only the exhausted scan is
    # a real error.
    # min() keeps the scan inside the valid port range — connect_ex raises
    # OverflowError on 65536, which would traceback instead of erroring cleanly.
    for candidate in range(port, min(port + PORT_SCAN_SPAN, 65535) + 1):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(("127.0.0.1", candidate)) != 0:
                break
    else:
        err_console.print(f"[red]Port {port} is already in use.[/red]")
        err_console.print(
            f"Ports {port}–{min(port + PORT_SCAN_SPAN, 65535)} are all busy. "
            "Try: [bold]anyscribe ui --port <free port>[/bold]"
        )
        raise typer.Exit(code=1)

    if candidate != port:
        console.print(f"[yellow]Port {port} busy — using {candidate}.[/yellow]")
    port = candidate

    console.print(f"[bold]anyscribe ui[/bold] → http://127.0.0.1:{port}")
    try:
        run(port=port, open_browser=not no_open)
    except KeyboardInterrupt:
        console.print("\n[dim]stopped.[/dim]")


@app.command()
def update(
    force: bool = typer.Option(
        False, "--force", "-f", help="Force update even with local changes."
    ),
    check: bool = typer.Option(
        False, "--check", "-c", help="Only check for updates, don't install."
    ),
) -> None:
    """[bold yellow]Update[/bold yellow] anyscribe to the latest version.

    Pulls the latest changes from git and reinstalls the package.
    """
    from anyscribe.core.updater import check_for_updates, update as do_update

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
    from anyscribe.core.deps import check_dependencies, print_dependency_status
    from anyscribe.config.paths import APP_HOME, CONFIG_FILE, ENV_FILE, get_workspace_dir
    from anyscribe.core.updater import get_install_path, check_for_updates

    console.print("[bold]anyscribe doctor[/bold]\n")

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
        console.print("\n  [yellow]Run [bold]anyscribe onboard[/bold] to set up.[/yellow]")

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
    from anyscribe.config.paths import ASCLI_SKILL_TARGET

    console.print("\n[bold]4. Claude Code Skill[/bold]\n")
    if not ASCLI_SKILL_TARGET.exists():
        console.print("  Skill: [yellow]Not installed[/yellow]")
        console.print("  [dim]Run [bold]anyscribe install-skill[/bold] to install.[/dim]")
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
            console.print("  [dim]Run [bold]anyscribe install-skill --force[/bold] to update.[/dim]")
        else:
            console.print(
                f"  Skill: [yellow]Outdated (v{installed_version} → v{__version__})[/yellow]"
            )
            console.print("  [dim]Run [bold]anyscribe install-skill --force[/bold] to update.[/dim]")
        console.print(f"  Path: {ASCLI_SKILL_TARGET}")

    # Updates
    console.print()
    check_for_updates(quiet=True)
