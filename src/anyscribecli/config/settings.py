"""Settings management — load, save, and validate config."""

from __future__ import annotations

import os
from dataclasses import dataclass, field, asdict, fields

import yaml
from dotenv import dotenv_values, load_dotenv, set_key, unset_key

from anyscribecli.config.paths import CONFIG_FILE, ENV_FILE

# Snapshot of the environment as the process was launched — captured before any
# .env is loaded (load_env lives in this module, so nothing has loaded it yet).
# Lets us tell a key inherited from the parent shell, which we don't own and
# must not discard, from one we merely loaded out of .env.
_PRISTINE_ENV: dict[str, str] = dict(os.environ)


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
    local_model: str = "base"  # any size in providers/local_models.py MODEL_SIZES
    # provider name -> pinned model id (see providers.PROVIDER_MODELS).
    # Missing key = that provider's default model.
    provider_models: dict[str, str] = field(default_factory=dict)
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


def env_file_keys() -> set[str]:
    """The set of secret names persisted in .env (empty if the file is absent).

    Uses python-dotenv's own parser, so it sees exactly what ``load_env`` will
    load — including ``export``-prefixed and quoted forms. Lets callers tell a
    key we actually saved from one merely inherited from the parent process
    environment; only the former is removable.
    """
    if not ENV_FILE.exists():
        return set()
    return set(dotenv_values(ENV_FILE))


def save_env(keys: dict[str, str]) -> None:
    """Write or update secrets in .env, one key at a time.

    Delegates to python-dotenv's ``set_key`` (atomic temp-file + os.replace),
    which updates or appends the target key while preserving every other line —
    comments, multiline values, and unrelated bindings — verbatim. ``quote_mode
    ="never"`` keeps our plain ``KEY=value`` format for single-line tokens.

    The file is created and kept mode ``0600`` (owner-only) — it holds API keys
    and must never be world-readable, matching the prior ``atomic_write`` path.
    """
    ENV_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not ENV_FILE.exists():
        # Create owner-only up front; os.open applies the mode atomically, so
        # there's no world-readable window before the first key lands.
        os.close(os.open(ENV_FILE, os.O_CREAT | os.O_WRONLY, 0o600))
    for k, v in keys.items():
        set_key(ENV_FILE, k, v, quote_mode="never")
    ENV_FILE.chmod(0o600)  # enforce owner-only even if the file predated this


def delete_env(names: list[str]) -> None:
    """Remove secrets from .env. No-op if the file is absent.

    The counterpart to ``save_env`` — python-dotenv's ``unset_key`` removes only
    the named binding (matching the same grammar ``load_env`` accepts) and
    leaves every other line's original text intact.
    """
    if not ENV_FILE.exists():
        return
    for name in names:
        unset_key(ENV_FILE, name)


def forget_env_var(name: str) -> None:
    """Reflect a .env deletion in the live process environment.

    Restores the value the process inherited from its parent shell (if any), so
    removing a saved key never discards a credential that also comes from the
    environment; otherwise drops it entirely. Mirrors what a fresh start would
    resolve now that the key is gone from .env.
    """
    inherited = _PRISTINE_ENV.get(name)
    if inherited is None:
        os.environ.pop(name, None)
    else:
        os.environ[name] = inherited
