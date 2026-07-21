"""All path constants for anyscribe."""

from importlib.resources import files as pkg_files
from pathlib import Path

APP_HOME = Path.home() / ".anyscribe"
LEGACY_APP_HOME = Path.home() / ".anyscribecli"
CONFIG_FILE = APP_HOME / "config.yaml"
ENV_FILE = APP_HOME / ".env"
LOGS_DIR = APP_HOME / "logs"
SESSIONS_DIR = APP_HOME / "sessions"
TMP_DIR = APP_HOME / "tmp"

# Recovery / checkpoint dirs for resilience
RECOVERY_DIR = APP_HOME / "recovery"
CHECKPOINT_DIR = APP_HOME / "checkpoints"

# Downloads live OUTSIDE the workspace — keeps the Obsidian vault pure markdown
DOWNLOADS_DIR = APP_HOME / "downloads"
AUDIO_DIR = DOWNLOADS_DIR / "audio"
VIDEO_DIR = DOWNLOADS_DIR / "video"

# Legacy path (pre-v0.5.1)
LEGACY_MEDIA_DIR = APP_HOME / "media"

# Workspace — visible, user-facing (configurable via config.yaml workspace_path)
DEFAULT_WORKSPACE = Path.home() / "anyscribe"
LEGACY_WORKSPACE = APP_HOME / "workspace"


def get_workspace_dir() -> Path:
    """Resolve workspace path: config value > default ~/anyscribe."""
    if CONFIG_FILE.exists():
        import yaml

        with open(CONFIG_FILE) as f:
            data = yaml.safe_load(f) or {}
        custom = data.get("workspace_path", "")
        if custom:
            return Path(custom).expanduser()
    return DEFAULT_WORKSPACE


# Claude Code skill installation
CLAUDE_HOME = Path.home() / ".claude"
CLAUDE_SKILLS_DIR = CLAUDE_HOME / "skills"
ASCLI_SKILL_TARGET = CLAUDE_SKILLS_DIR / "anyscribe"


def get_skill_source_dir():
    """Return path to bundled skill files in the package."""
    return pkg_files("anyscribe").joinpath("skill")


def ensure_app_dirs() -> None:
    """Create all required app directories if they don't exist."""
    from anyscribe.core.migrate import migrate_app_home_once

    migrate_app_home_once()  # before mkdir, or we create an empty new home
    for d in [APP_HOME, LOGS_DIR, SESSIONS_DIR, TMP_DIR]:
        d.mkdir(parents=True, exist_ok=True)
