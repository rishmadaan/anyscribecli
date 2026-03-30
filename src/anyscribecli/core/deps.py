"""System dependency checking and installation."""

from __future__ import annotations

import platform
import shutil
import subprocess
import sys
from dataclasses import dataclass

from rich.console import Console
from rich.table import Table

console = Console()


@dataclass
class Dependency:
    """A system dependency that ascli needs."""

    name: str
    command: str  # binary name to check via shutil.which
    required: bool
    description: str
    install_brew: str  # homebrew install command
    install_pip: str  # pip install command (fallback)
    install_apt: str  # apt install command (Linux)
    install_url: str  # manual install URL
    min_version: str | None = None


DEPENDENCIES = [
    Dependency(
        name="Python",
        command="python3",
        required=True,
        description="Python interpreter (3.10+)",
        install_brew="brew install python@3.12",
        install_pip="",
        install_apt="sudo apt install python3",
        install_url="https://www.python.org/downloads/",
        min_version="3.10",
    ),
    Dependency(
        name="yt-dlp",
        command="yt-dlp",
        required=True,
        description="YouTube/video downloader",
        install_brew="brew install yt-dlp",
        install_pip="pip install yt-dlp",
        install_apt="sudo apt install yt-dlp",
        install_url="https://github.com/yt-dlp/yt-dlp#installation",
    ),
    Dependency(
        name="ffmpeg",
        command="ffmpeg",
        required=True,
        description="Audio/video processing (needed for audio extraction and chunking)",
        install_brew="brew install ffmpeg",
        install_pip="",
        install_apt="sudo apt install ffmpeg",
        install_url="https://ffmpeg.org/download.html",
    ),
    Dependency(
        name="ffprobe",
        command="ffprobe",
        required=True,
        description="Audio metadata (bundled with ffmpeg)",
        install_brew="brew install ffmpeg",
        install_pip="",
        install_apt="sudo apt install ffmpeg",
        install_url="https://ffmpeg.org/download.html",
    ),
]


def _detect_os() -> str:
    """Detect the operating system."""
    system = platform.system().lower()
    if system == "darwin":
        return "macos"
    elif system == "linux":
        return "linux"
    return "other"


def _has_brew() -> bool:
    """Check if Homebrew is available."""
    return shutil.which("brew") is not None


def _has_apt() -> bool:
    """Check if apt is available."""
    return shutil.which("apt") is not None


def _get_python_version() -> tuple[int, int]:
    """Get current Python version as (major, minor)."""
    return sys.version_info.major, sys.version_info.minor


def _get_version(command: str) -> str | None:
    """Try to get version string from a command."""
    try:
        result = subprocess.run([command, "--version"], capture_output=True, text=True, timeout=10)
        output = result.stdout.strip() or result.stderr.strip()
        return output.split("\n")[0] if output else None
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return None


@dataclass
class DepCheckResult:
    """Result of checking a single dependency."""

    dep: Dependency
    found: bool
    version: str | None
    path: str | None


def check_dependencies() -> list[DepCheckResult]:
    """Check all system dependencies. Returns list of results."""
    results = []
    for dep in DEPENDENCIES:
        path = shutil.which(dep.command)
        found = path is not None

        version = None
        if found:
            if dep.name == "Python":
                major, minor = _get_python_version()
                version = f"{major}.{minor}"
                # Check minimum version
                if (major, minor) < (3, 10):
                    found = False
            else:
                version = _get_version(dep.command)

        results.append(DepCheckResult(dep=dep, found=found, version=version, path=path))
    return results


def print_dependency_status(results: list[DepCheckResult]) -> None:
    """Print a formatted table of dependency status."""
    table = Table(title="System Dependencies")
    table.add_column("Dependency", style="bold")
    table.add_column("Status")
    table.add_column("Version / Path")

    for r in results:
        if r.found:
            status = "[green]Found[/green]"
            info = r.version or r.path or ""
        else:
            req = (
                "[red]Missing (required)[/red]"
                if r.dep.required
                else "[yellow]Missing (optional)[/yellow]"
            )
            status = req
            info = r.dep.description

        table.add_row(r.dep.name, status, info)

    console.print(table)


def get_install_command(dep: Dependency) -> str | None:
    """Get the best install command for the current OS."""
    os_type = _detect_os()

    if os_type == "macos" and _has_brew() and dep.install_brew:
        return dep.install_brew
    elif os_type == "linux" and _has_apt() and dep.install_apt:
        return dep.install_apt
    elif dep.install_pip:
        return dep.install_pip
    return None


def install_dependency(dep: Dependency) -> bool:
    """Attempt to install a missing dependency. Returns True on success."""
    cmd_str = get_install_command(dep)
    if not cmd_str:
        console.print(f"  [yellow]Cannot auto-install {dep.name}.[/yellow]")
        console.print(f"  Install manually: {dep.install_url}")
        return False

    console.print(f"  Running: [cyan]{cmd_str}[/cyan]")
    try:
        result = subprocess.run(cmd_str.split(), capture_output=True, text=True, timeout=300)
        if result.returncode == 0:
            console.print(f"  [green]{dep.name} installed successfully.[/green]")
            return True
        else:
            console.print(f"  [red]Installation failed:[/red] {result.stderr.strip()[:200]}")
            console.print(f"  Install manually: {dep.install_url}")
            return False
    except (subprocess.TimeoutExpired, OSError) as e:
        console.print(f"  [red]Installation error:[/red] {e}")
        console.print(f"  Install manually: {dep.install_url}")
        return False


def check_and_install(interactive: bool = True) -> bool:
    """Check all dependencies and offer to install missing ones.

    Returns True if all required dependencies are satisfied.
    """
    import typer

    console.print("\n[bold]Checking system dependencies...[/bold]\n")
    results = check_dependencies()
    print_dependency_status(results)

    missing = [r for r in results if not r.found and r.dep.required]
    if not missing:
        console.print("\n[green]All dependencies satisfied.[/green]")
        return True

    console.print(f"\n[yellow]{len(missing)} required dependency(ies) missing.[/yellow]")

    if not interactive:
        console.print("[red]Cannot proceed without required dependencies.[/red]")
        return False

    # Offer to install each missing dependency
    all_installed = True
    for r in missing:
        # Skip Python — user needs to install it themselves
        if r.dep.name == "Python":
            console.print("\n[red]Python 3.10+ is required.[/red]")
            console.print(f"  Current: {r.version or 'not found'}")
            console.print(f"  Install from: {r.dep.install_url}")
            all_installed = False
            continue

        # Skip ffprobe if ffmpeg is also missing (installing ffmpeg covers both)
        if r.dep.name == "ffprobe":
            ffmpeg_missing = any(mr.dep.name == "ffmpeg" and not mr.found for mr in results)
            if ffmpeg_missing:
                continue  # will be installed with ffmpeg

        cmd = get_install_command(r.dep)
        if cmd:
            console.print(f"\n[bold]{r.dep.name}[/bold] — {r.dep.description}")
            console.print(f"  Install command: [cyan]{cmd}[/cyan]")
            if typer.confirm(f"  Install {r.dep.name}?", default=True):
                if not install_dependency(r.dep):
                    all_installed = False
            else:
                console.print(f"  Skipped. Install manually: {r.dep.install_url}")
                all_installed = False
        else:
            console.print(f"\n[bold]{r.dep.name}[/bold] — {r.dep.description}")
            console.print("  [yellow]No auto-installer available for your system.[/yellow]")
            console.print(f"  Install manually: {r.dep.install_url}")
            all_installed = False

    if all_installed:
        # Re-verify
        console.print("\n[bold]Re-checking dependencies...[/bold]\n")
        results = check_dependencies()
        print_dependency_status(results)
        missing = [r for r in results if not r.found and r.dep.required]
        if not missing:
            console.print("\n[green]All dependencies satisfied.[/green]")
            return True

    console.print(
        "\n[yellow]Some dependencies are still missing. ascli may not work fully.[/yellow]"
    )
    return typer.confirm("Continue anyway?", default=False)
