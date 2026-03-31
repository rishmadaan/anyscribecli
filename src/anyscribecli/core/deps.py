"""System dependency checking and installation."""

from __future__ import annotations

import platform
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone

from rich.console import Console
from rich.table import Table

console = Console()

# yt-dlp versions older than this many days trigger an auto-update
YTDLP_MAX_AGE_DAYS = 60


@dataclass
class Dependency:
    """A system dependency that ascli needs."""

    name: str
    command: str  # binary name to check via shutil.which (for system binaries)
    required: bool
    description: str
    install_brew: str  # homebrew install command
    install_pip: str  # pip install command (fallback)
    install_apt: str  # apt install command (Linux)
    install_url: str  # manual install URL
    min_version: str | None = None
    module_name: str | None = None  # Python module name for pip-installed tools


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
        module_name="yt_dlp",
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


def get_command(name: str) -> list[str]:
    """Return the subprocess invocation prefix for a dependency.

    For pip-installed tools with a module_name (e.g. yt-dlp), returns
    [sys.executable, "-m", module_name] — works cross-platform regardless
    of PATH configuration. For system binaries (ffmpeg, etc.), returns [command].
    """
    for dep in DEPENDENCIES:
        if dep.name == name:
            if dep.module_name:
                return [sys.executable, "-m", dep.module_name]
            return [dep.command]
    return [name]


def _detect_os() -> str:
    """Detect the operating system."""
    system = platform.system().lower()
    if system == "darwin":
        return "macos"
    elif system == "linux":
        return "linux"
    elif system == "windows":
        return "windows"
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


def _check_module(module_name: str) -> tuple[bool, str | None]:
    """Check if a Python module is available and get its version."""
    try:
        result = subprocess.run(
            [sys.executable, "-m", module_name, "--version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            output = result.stdout.strip() or result.stderr.strip()
            version = output.split("\n")[0] if output else None
            return True, version
    except (subprocess.TimeoutExpired, OSError):
        pass
    return False, None


def check_dependencies() -> list[DepCheckResult]:
    """Check all system dependencies. Returns list of results."""
    results = []
    for dep in DEPENDENCIES:
        if dep.name == "Python":
            # We're already running inside Python — check version directly
            major, minor = _get_python_version()
            version = f"{major}.{minor}"
            found = (major, minor) >= (3, 10)
            path = sys.executable
        elif dep.module_name:
            # pip-installed tool: check via `python -m module` (works cross-platform)
            found, version = _check_module(dep.module_name)
            path = f"{sys.executable} -m {dep.module_name}" if found else None
        else:
            # System binary: check PATH
            path = shutil.which(dep.command)
            found = path is not None
            version = _get_version(dep.command) if found else None

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


def _build_install_cmd(cmd_str: str) -> list[str]:
    """Convert an install command string to a subprocess arg list.

    Rewrites bare `pip install ...` to `sys.executable -m pip install ...`
    so it targets the correct Python environment on all platforms.
    """
    parts = cmd_str.split()
    if parts and parts[0] == "pip":
        return [sys.executable, "-m"] + parts
    return parts


def install_dependency(dep: Dependency) -> bool:
    """Attempt to install a missing dependency. Returns True on success."""
    cmd_str = get_install_command(dep)
    if not cmd_str:
        console.print(f"  [yellow]Cannot auto-install {dep.name}.[/yellow]")
        console.print(f"  Install manually: {dep.install_url}")
        return False

    cmd_parts = _build_install_cmd(cmd_str)
    console.print(f"  Running: [cyan]{' '.join(cmd_parts)}[/cyan]")
    try:
        result = subprocess.run(cmd_parts, capture_output=True, text=True, timeout=300)
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


def _parse_ytdlp_version_date(version_str: str) -> datetime | None:
    """Parse yt-dlp version string (e.g. 'yt-dlp 2025.10.22') into a datetime."""
    match = re.search(r"(\d{4})\.(\d{1,2})\.(\d{1,2})", version_str)
    if not match:
        return None
    year, month, day = int(match.group(1)), int(match.group(2)), int(match.group(3))
    try:
        return datetime(year, month, day, tzinfo=timezone.utc)
    except ValueError:
        return None


def ensure_ytdlp_current() -> None:
    """Check if yt-dlp is stale (>60 days old) and auto-update if so.

    Called before any yt-dlp subprocess invocation to prevent
    403 errors from outdated extractors (e.g. YouTube SABR streaming).
    Silently skips if version can't be parsed or update fails.
    """
    ytdlp_cmd = get_command("yt-dlp")
    try:
        result = subprocess.run(
            [*ytdlp_cmd, "--version"], capture_output=True, text=True, timeout=10
        )
        version_str = result.stdout.strip() or result.stderr.strip()
    except (subprocess.TimeoutExpired, OSError):
        version_str = None
    if not version_str:
        return

    release_date = _parse_ytdlp_version_date(version_str)
    if not release_date:
        return

    age_days = (datetime.now(timezone.utc) - release_date).days
    if age_days <= YTDLP_MAX_AGE_DAYS:
        return

    console.print(
        f"[yellow]yt-dlp is {age_days} days old ({version_str.strip()}) — updating...[/yellow]"
    )
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "--upgrade", "yt-dlp"],
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode == 0:
            try:
                v = subprocess.run(
                    [*ytdlp_cmd, "--version"],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                new_version = v.stdout.strip() or "unknown"
            except (subprocess.TimeoutExpired, OSError):
                new_version = "unknown"
            console.print(f"[green]yt-dlp updated to {new_version.strip()}[/green]")
        else:
            console.print(
                "[yellow]yt-dlp auto-update failed. Run manually: pip install -U yt-dlp[/yellow]"
            )
    except (subprocess.TimeoutExpired, OSError):
        console.print(
            "[yellow]yt-dlp auto-update timed out. Run manually: pip install -U yt-dlp[/yellow]"
        )


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
