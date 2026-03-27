"""All path constants for anyscribecli."""

from pathlib import Path

APP_HOME = Path.home() / ".anyscribecli"
CONFIG_FILE = APP_HOME / "config.yaml"
ENV_FILE = APP_HOME / ".env"
LOGS_DIR = APP_HOME / "logs"
WORKSPACE_DIR = APP_HOME / "workspace"
SESSIONS_DIR = APP_HOME / "sessions"
TMP_DIR = APP_HOME / "tmp"

# Media lives OUTSIDE the workspace — keeps the Obsidian vault pure markdown
MEDIA_DIR = APP_HOME / "media"
AUDIO_DIR = MEDIA_DIR / "audio"
VIDEO_DIR = MEDIA_DIR / "video"

# Workspace subdirs
SOURCES_DIR = WORKSPACE_DIR / "sources"
DAILY_DIR = WORKSPACE_DIR / "daily"
INDEX_FILE = WORKSPACE_DIR / "_index.md"


def ensure_app_dirs() -> None:
    """Create all required app directories if they don't exist."""
    for d in [APP_HOME, LOGS_DIR, SESSIONS_DIR, TMP_DIR]:
        d.mkdir(parents=True, exist_ok=True)
