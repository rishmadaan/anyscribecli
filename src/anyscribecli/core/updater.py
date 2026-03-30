"""Version checking and self-update system.

Supports two install types:
  - git: editable install from cloned repo (developer workflow)
  - pip: standard pip install from PyPI or git+https:// (user workflow)

Detection is automatic — if the package lives inside a git repo, it's a git install.
Otherwise, it's a pip install.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from rich.console import Console

from anyscribecli import __version__

console = Console()

# GitHub repo for pip-based installs
GITHUB_REPO = "https://github.com/rishmadaan/anyscribecli.git"
PYPI_PACKAGE = "anyscribecli"


def get_install_type() -> str:
    """Detect how anyscribecli was installed.

    Returns 'git' (editable, from cloned repo) or 'pip' (standard package install).
    """
    repo = _find_git_repo()
    return "git" if repo else "pip"


def _find_git_repo() -> Path | None:
    """Find the git repo root if this is a git-based install."""
    try:
        import anyscribecli

        pkg_path = Path(anyscribecli.__file__).resolve()
        for parent in pkg_path.parents:
            if (parent / ".git").exists():
                return parent
            if parent == Path.home():
                break
    except Exception:
        pass
    return None


def get_install_path() -> Path | None:
    """Get the git repo path, or None for pip installs."""
    return _find_git_repo()


def get_current_version() -> str:
    """Get the currently installed version."""
    return __version__


# ── Git-based update ──────────────────────────────────────────


def _git_check_latest(repo_path: Path) -> str | None:
    """Check git remote for a newer version. Returns version string or None."""
    try:
        subprocess.run(
            ["git", "fetch", "--quiet"],
            cwd=repo_path,
            capture_output=True,
            timeout=30,
        )
        result = subprocess.run(
            ["git", "log", "HEAD..origin/main", "--oneline"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0 and result.stdout.strip():
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
        return None
    except Exception:
        return None


def _git_update(repo_path: Path, force: bool = False) -> bool:
    """Update a git-based install by pulling and reinstalling."""
    current = get_current_version()
    console.print("  Install type: [cyan]git (editable)[/cyan]")
    console.print(f"  Repo path: {repo_path}")

    # Check for uncommitted changes
    status_result = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=repo_path,
        capture_output=True,
        text=True,
        timeout=10,
    )
    if status_result.stdout.strip() and not force:
        console.print("\n[yellow]You have uncommitted changes in the repo.[/yellow]")
        console.print(
            "Run [bold]ascli update --force[/bold] to update anyway (will stash changes)."
        )
        return False

    if status_result.stdout.strip() and force:
        console.print("[dim]Stashing local changes...[/dim]")
        subprocess.run(["git", "stash"], cwd=repo_path, capture_output=True, timeout=10)

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

    console.print("[dim]Reinstalling...[/dim]")
    pip_result = subprocess.run(
        [sys.executable, "-m", "pip", "install", "-e", "."],
        cwd=repo_path,
        capture_output=True,
        text=True,
        timeout=120,
    )
    if pip_result.returncode != 0:
        console.print(f"[red]Reinstall failed:[/red] {pip_result.stderr.strip()[:300]}")
        return False

    # Read new version from file (module is cached)
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
        console.print(f"\n[green]Up to date:[/green] v{current}")
    return True


# ── Pip-based update ──────────────────────────────────────────


def _pip_check_latest() -> str | None:
    """Check PyPI (or pip) for a newer version."""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "index", "versions", PYPI_PACKAGE],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0 and result.stdout.strip():
            # Output format: "anyscribecli (0.2.0)\nAvailable versions: 0.2.0, 0.1.0"
            first_line = result.stdout.strip().split("\n")[0]
            if "(" in first_line and ")" in first_line:
                return first_line.split("(")[1].split(")")[0]
    except Exception:
        pass
    return None


def _pip_update() -> bool:
    """Update a pip-based install."""
    current = get_current_version()
    console.print("  Install type: [cyan]pip package[/cyan]")

    console.print("[dim]Upgrading via pip...[/dim]")
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", "--upgrade", PYPI_PACKAGE],
        capture_output=True,
        text=True,
        timeout=120,
    )

    if result.returncode != 0:
        # PyPI might not have the package yet — try GitHub
        console.print("[dim]PyPI package not found, trying GitHub...[/dim]")
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "--upgrade", f"git+{GITHUB_REPO}"],
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode != 0:
            console.print(f"[red]Update failed:[/red] {result.stderr.strip()[:300]}")
            return False

    # Check new version
    ver_result = subprocess.run(
        [sys.executable, "-c", "from anyscribecli import __version__; print(__version__)"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    new_version = ver_result.stdout.strip() if ver_result.returncode == 0 else current

    if new_version != current:
        console.print(f"\n[green]Updated:[/green] v{current} → v{new_version}")
    else:
        console.print(f"\n[green]Up to date:[/green] v{current}")
    return True


# ── Public API ────────────────────────────────────────────────


def check_for_updates(quiet: bool = False) -> bool:
    """Check if updates are available. Returns True if update exists."""
    current = get_current_version()
    install_type = get_install_type()

    if install_type == "git":
        repo_path = _find_git_repo()
        if not repo_path:
            return False
        if not quiet:
            console.print("[dim]Checking for updates (git)...[/dim]")
        latest = _git_check_latest(repo_path)
    else:
        if not quiet:
            console.print("[dim]Checking for updates (pip)...[/dim]")
        latest = _pip_check_latest()

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
    """Update ascli to the latest version.

    Automatically detects install type (git vs pip) and uses the appropriate method.
    """
    current = get_current_version()
    install_type = get_install_type()

    console.print(f"  Current version: v{current}")

    if install_type == "git":
        repo_path = _find_git_repo()
        if not repo_path:
            console.print("[red]Git repo not found.[/red]")
            return False
        return _git_update(repo_path, force=force)
    else:
        return _pip_update()
