"""Settings management — load, save, and validate config."""

from __future__ import annotations

from dataclasses import dataclass, field, asdict

import yaml
from dotenv import load_dotenv

from anyscribecli.config.paths import CONFIG_FILE, ENV_FILE


@dataclass
class InstagramSettings:
    username: str = ""
    password: str = ""


@dataclass
class Settings:
    provider: str = "openai"
    language: str = "auto"
    keep_media: bool = False
    output_format: str = "clean"  # clean | timestamped (future: diarized)
    instagram: InstagramSettings = field(default_factory=InstagramSettings)

    def to_dict(self) -> dict:
        """Serialize to a plain dict for YAML output."""
        d = asdict(self)
        return d

    @classmethod
    def from_dict(cls, data: dict) -> Settings:
        """Deserialize from a dict (loaded from YAML)."""
        ig_data = data.pop("instagram", {})
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
    """Write settings to config.yaml."""
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        yaml.dump(settings.to_dict(), f, default_flow_style=False, sort_keys=False)


def load_env() -> None:
    """Load API keys from .env file."""
    if ENV_FILE.exists():
        load_dotenv(ENV_FILE)


def save_env(keys: dict[str, str]) -> None:
    """Write or update API keys in .env file."""
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

    with open(ENV_FILE, "w") as f:
        for k, v in existing.items():
            f.write(f"{k}={v}\n")
