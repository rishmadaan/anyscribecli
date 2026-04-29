"""Settings management — load, save, and validate config."""

from __future__ import annotations

from dataclasses import dataclass, field, asdict

import yaml
from dotenv import load_dotenv

from anyscribecli.config.paths import CONFIG_FILE, ENV_FILE


@dataclass
class InstagramSettings:
    """Instagram downloader configuration.

    ``browser`` is the name of a yt-dlp-supported browser (firefox, chrome,
    safari, brave, edge, chromium, vivaldi, opera) whose cookies will be
    used when downloading. Empty string = no cookies (anonymous fetch only,
    works for many public reels).

    Legacy fields ``username`` and ``password`` from pre-0.8.3 versions are
    silently discarded by ``Settings.from_dict``.
    """

    browser: str = ""


@dataclass
class Settings:
    provider: str = "openai"
    language: str = "auto"
    keep_media: bool = False
    output_format: str = "clean"  # clean | timestamped | diarized
    diarize: bool = False
    prompt_download: str = "never"  # never | always | ask (prompt after transcription)
    local_file_media: str = "skip"  # skip | copy | move | ask
    workspace_path: str = ""  # empty = ~/anyscribe (default)
    local_model: str = "base"  # tiny | base | small | medium | large-v3
    instagram: InstagramSettings = field(default_factory=InstagramSettings)

    def to_dict(self) -> dict:
        """Serialize to a plain dict for YAML output."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> Settings:
        """Deserialize from a dict (loaded from YAML)."""
        ig_data = data.pop("instagram", {}) or {}
        # Discard pre-0.8.3 fields. The yt-dlp migration removed username/password
        # — we read cookies from the user's browser instead.
        ig_data.pop("username", None)
        ig_data.pop("password", None)
        ig = InstagramSettings(**ig_data) if ig_data else InstagramSettings()
        return cls(instagram=ig, **data)


def load_config() -> Settings:
    """Load settings from config.yaml. Returns defaults if file doesn't exist."""
    if not CONFIG_FILE.exists():
        return Settings()
    with open(CONFIG_FILE) as f:
        data = yaml.safe_load(f) or {}
    return Settings.from_dict(data)


def save_config(settings: Settings) -> None:
    """Write settings to config.yaml (atomic write)."""
    from anyscribecli.core.fileutil import atomic_write

    content = yaml.dump(settings.to_dict(), default_flow_style=False, sort_keys=False)
    atomic_write(CONFIG_FILE, content)


def load_env() -> None:
    """Load API keys and secrets from .env file."""
    if ENV_FILE.exists():
        load_dotenv(ENV_FILE)


def save_env(keys: dict[str, str]) -> None:
    """Write or update secrets in .env file (atomic write)."""
    from anyscribecli.core.fileutil import atomic_write

    ENV_FILE.parent.mkdir(parents=True, exist_ok=True)

    existing: dict[str, str] = {}
    if ENV_FILE.exists():
        with open(ENV_FILE) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    existing[k.strip()] = v.strip()

    existing.update(keys)

    content = "".join(f"{k}={v}\n" for k, v in existing.items())
    atomic_write(ENV_FILE, content)
