"""All path constants for anyscribecli."""

from importlib.resources import files as pkg_files
from pathlib import Path

APP_HOME = Path.home() / ".anyscribecli"
CONFIG_FILE = APP_HOME / "config.yaml"
ENV_FILE = APP_HOME / ".env"
LOGS_DIR = APP_HOME / "logs"
SESSIONS_DIR = APP_HOME / "sessions"
TMP_DIR = APP_HOME / "tmp"

# Media lives OUTSIDE the workspace — keeps the Obsidian vault pure markdown
MEDIA_DIR = APP_HOME / "media"
AUDIO_DIR = MEDIA_DIR / "audio"
VIDEO_DIR = MEDIA_DIR / "video"

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
ASCLI_SKILL_TARGET = CLAUDE_SKILLS_DIR / "ascli"


def get_skill_source_dir():
    """Return path to bundled skill files in the package."""
    return pkg_files("anyscribecli").joinpath("skill")


def ensure_app_dirs() -> None:
    """Create all required app directories if they don't exist."""
    for d in [APP_HOME, LOGS_DIR, SESSIONS_DIR, TMP_DIR]:
        d.mkdir(parents=True, exist_ok=True)
