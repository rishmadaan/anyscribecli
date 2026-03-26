"""Version checking and self-update system."""

from __future__ import annotations

import subprocess
from pathlib import Path

from rich.console import Console

from anyscribecli import __version__

console = Console()


def get_install_path() -> Path | None:
    """Find where anyscribecli is installed from (git repo root)."""
    try:
        import anyscribecli

        pkg_path = Path(anyscribecli.__file__).resolve()
        # Walk up to find a .git directory (means it's a git-based install)
        for parent in pkg_path.parents:
            if (parent / ".git").exists():
                return parent
            # Stop at home directory
            if parent == Path.home():
                break
    except Exception:
        pass
    return None


def get_current_version() -> str:
    """Get the currently installed version."""
    return __version__


def get_latest_version(repo_path: Path) -> str | None:
    """Check the remote for the latest version (via git fetch)."""
    try:
        # Fetch latest without merging
        subprocess.run(
            ["git", "fetch", "--quiet"],
            cwd=repo_path,
            capture_output=True,
            timeout=30,
        )
        # Check if we're behind
        result = subprocess.run(
            ["git", "log", "HEAD..origin/main", "--oneline"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0 and result.stdout.strip():
            # There are new commits — read the version from remote
            ver_result = subprocess.run(
                ["git", "show", "origin/main:src/anyscribecli/__init__.py"],
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=10,
            )
            if ver_result.returncode == 0:
                for line in ver_result.stdout.split("\n"):
                    if "__version__" in line:
                        return line.split('"')[1]
        return None  # No updates available
    except Exception:
        return None


def check_for_updates(quiet: bool = False) -> bool:
    """Check if updates are available. Returns True if update exists."""
    repo_path = get_install_path()
    if not repo_path:
        if not quiet:
            console.print("[yellow]Cannot check for updates — not installed from git.[/yellow]")
        return False

    if not quiet:
        console.print("[dim]Checking for updates...[/dim]")

    latest = get_latest_version(repo_path)
    current = get_current_version()

    if latest and latest != current:
        console.print(
            f"[yellow]Update available:[/yellow] v{current} → v{latest}\n"
            f"  Run [bold]ascli update[/bold] to update."
        )
        return True
    elif not quiet:
        console.print(f"[green]Up to date:[/green] v{current}")
    return False


def update(force: bool = False) -> bool:
    """Pull latest changes and reinstall.

    Returns True on success.
    """
    repo_path = get_install_path()
    if not repo_path:
        console.print("[red]Cannot update — not installed from a git repository.[/red]")
        console.print("If you installed via pip, run: [bold]pip install --upgrade anyscribecli[/bold]")
        return False

    current = get_current_version()
    console.print(f"Current version: v{current}")
    console.print(f"Install path: {repo_path}")

    # Check for uncommitted changes
    status_result = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=repo_path,
        capture_output=True,
        text=True,
        timeout=10,
    )
    if status_result.stdout.strip() and not force:
        console.print("[yellow]You have uncommitted changes in the repo.[/yellow]")
        console.print("Run [bold]ascli update --force[/bold] to update anyway (will stash changes).")
        return False

    # Stash if force
    if status_result.stdout.strip() and force:
        console.print("[dim]Stashing local changes...[/dim]")
        subprocess.run(
            ["git", "stash"],
            cwd=repo_path,
            capture_output=True,
            timeout=10,
        )

    # Pull
    console.print("[dim]Pulling latest changes...[/dim]")
    pull_result = subprocess.run(
        ["git", "pull", "--rebase"],
        cwd=repo_path,
        capture_output=True,
        text=True,
        timeout=60,
    )
    if pull_result.returncode != 0:
        console.print(f"[red]Git pull failed:[/red] {pull_result.stderr.strip()}")
        return False

    # Reinstall
    console.print("[dim]Reinstalling...[/dim]")
    pip_result = subprocess.run(
        ["pip", "install", "-e", "."],
        cwd=repo_path,
        capture_output=True,
        text=True,
        timeout=120,
    )
    if pip_result.returncode != 0:
        console.print(f"[red]Reinstall failed:[/red] {pip_result.stderr.strip()[:300]}")
        return False

    # Report new version
    # Re-read version from file since the module is cached
    version_file = repo_path / "src" / "anyscribecli" / "__init__.py"
    new_version = current
    if version_file.exists():
        for line in version_file.read_text().split("\n"):
            if "__version__" in line:
                new_version = line.split('"')[1]
                break

    if new_version != current:
        console.print(f"\n[green]Updated:[/green] v{current} → v{new_version}")
    else:
        console.print(f"\n[green]Already up to date:[/green] v{current}")

    return True
