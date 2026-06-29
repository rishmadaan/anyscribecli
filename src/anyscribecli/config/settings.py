"""Settings management — load, save, and validate config."""

from __future__ import annotations

import os
from dataclasses import dataclass, field, asdict, fields

import yaml
from dotenv import load_dotenv

from anyscribecli.config.paths import CONFIG_FILE, ENV_FILE


@dataclass
class InstagramSettings:
    username: str = ""
    # password is NOT stored here — it lives in .env as INSTAGRAM_PASSWORD


@dataclass
class Settings:
    provider: str = "openai"
    quality: str = "balanced"  # accuracy | balanced | cost | free (resolves to a provider)
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
        """Deserialize from a dict (loaded from YAML).

        Tolerant of unknown keys so a config written by a different version
        (e.g. one with an extra instagram field) loads instead of crashing.
        """
        data = dict(data)  # don't mutate the caller's dict
        ig_data = data.pop("instagram", {}) or {}
        ig_data.pop("password", None)  # password lives in .env, never config
        known_ig = {f.name for f in fields(InstagramSettings)}
        ig = InstagramSettings(**{k: v for k, v in ig_data.items() if k in known_ig})
        known = {f.name for f in fields(cls)} - {"instagram"}
        return cls(instagram=ig, **{k: v for k, v in data.items() if k in known})

    def get_instagram_password(self) -> str:
        """Get Instagram password from environment (stored in .env)."""
        return os.environ.get("INSTAGRAM_PASSWORD", "")


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
