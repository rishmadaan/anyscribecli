"""Settings management — load, save, and validate config."""

from __future__ import annotations

from dataclasses import dataclass, field, asdict, fields

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
        loads instead of crashing. This also drops pre-0.8.3 Instagram fields
        (username/password) — the yt-dlp migration reads browser cookies instead.
        """
        data = dict(data)  # don't mutate the caller's dict
        ig_data = data.pop("instagram", {}) or {}
        known_ig = {f.name for f in fields(InstagramSettings)}
        ig = InstagramSettings(**{k: v for k, v in ig_data.items() if k in known_ig})
        known = {f.name for f in fields(cls)} - {"instagram"}
        return cls(instagram=ig, **{k: v for k, v in data.items() if k in known})


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


def _read_env_pairs() -> dict[str, str]:
    """Parse .env into {key: value}, returning {} if the file is absent.

    Tolerates an optional ``export `` prefix on keys (valid dotenv syntax that
    python-dotenv also honours) by normalizing it away — so ``export FOO=x`` is
    read as key ``FOO``. Comments and blank lines are skipped. Rewriting via
    save_env/delete_env therefore normalizes any export-prefixed lines to plain
    ``KEY=value`` form. Shared by save_env and delete_env so both agree on what
    a key name is.
    """
    pairs: dict[str, str] = {}
    if not ENV_FILE.exists():
        return pairs
    with open(ENV_FILE) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            k = k.strip()
            if k.startswith("export "):
                k = k[len("export ") :].strip()
            pairs[k] = v.strip()
    return pairs


def env_file_keys() -> set[str]:
    """The set of secret names persisted in .env (empty if the file is absent).

    Lets callers distinguish a key we actually saved from one merely inherited
    from the parent process environment — only the former is removable.
    """
    return set(_read_env_pairs())


def save_env(keys: dict[str, str]) -> None:
    """Write or update secrets in .env file (atomic write)."""
    from anyscribecli.core.fileutil import atomic_write

    ENV_FILE.parent.mkdir(parents=True, exist_ok=True)
    existing = _read_env_pairs()
    existing.update(keys)
    content = "".join(f"{k}={v}\n" for k, v in existing.items())
    atomic_write(ENV_FILE, content)


def delete_env(names: list[str]) -> None:
    """Remove secrets from .env, rewriting it without them (atomic write).

    No-op if the file is absent. The counterpart to ``save_env`` — same
    export-aware parsing, minus the dropped keys.
    """
    from anyscribecli.core.fileutil import atomic_write

    if not ENV_FILE.exists():
        return

    drop = set(names)
    remaining = {k: v for k, v in _read_env_pairs().items() if k not in drop}
    content = "".join(f"{k}={v}\n" for k, v in remaining.items())
    atomic_write(ENV_FILE, content)
