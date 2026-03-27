"""ascli — main CLI entry point."""

from __future__ import annotations

from typing import Optional

import typer
from rich.console import Console

from anyscribecli import __version__

app = typer.Typer(
    name="ascli",
    help="Download, transcribe, and convert video/audio to structured markdown.",
    rich_markup_mode="rich",
    no_args_is_help=True,
)

console = Console()
err_console = Console(stderr=True)


def version_callback(value: bool) -> None:
    if value:
        console.print(f"ascli v{__version__}")
        raise typer.Exit()


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
    """[bold]ascli[/bold] — download, transcribe, and convert video/audio to structured markdown."""


# Register commands
from anyscribecli.cli.onboard import onboard  # noqa: E402
from anyscribecli.cli.transcribe import transcribe  # noqa: E402
from anyscribecli.cli.config_cmd import config_app, providers_app  # noqa: E402
from anyscribecli.cli.batch import batch  # noqa: E402
from anyscribecli.cli.download import download  # noqa: E402

app.command()(onboard)
app.command()(transcribe)
app.command()(batch)
app.command()(download)
app.add_typer(config_app, name="config")
app.add_typer(providers_app, name="providers")


@app.command()
def update(
    force: bool = typer.Option(False, "--force", "-f", help="Force update even with local changes."),
    check: bool = typer.Option(False, "--check", "-c", help="Only check for updates, don't install."),
) -> None:
    """[bold yellow]Update[/bold yellow] ascli to the latest version.

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
    from anyscribecli.config.paths import APP_HOME, CONFIG_FILE, ENV_FILE, WORKSPACE_DIR
    from anyscribecli.core.updater import get_install_path, check_for_updates

    console.print("[bold]ascli doctor[/bold]\n")

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
        ("Workspace vault", WORKSPACE_DIR.exists()),
        ("Workspace index", (WORKSPACE_DIR / "_index.md").exists()),
    ]
    for name, ok in checks:
        status = "[green]OK[/green]" if ok else "[red]Missing[/red]"
        console.print(f"  {name}: {status}")

    if not CONFIG_FILE.exists():
        console.print("\n  [yellow]Run [bold]ascli onboard[/bold] to set up.[/yellow]")

    # Install info
    console.print("\n[bold]3. Installation[/bold]\n")
    console.print(f"  Version: v{__version__}")
    repo = get_install_path()
    if repo:
        console.print("  Install type: git (editable)")
        console.print(f"  Repo path: {repo}")
    else:
        console.print("  Install type: pip package")

    # Updates
    console.print()
    check_for_updates(quiet=True)
