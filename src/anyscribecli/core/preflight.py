"""Pre-flight checks — validate prerequisites before starting the pipeline."""

from __future__ import annotations

import os
import shutil
from pathlib import Path

from anyscribecli.config.paths import TMP_DIR
from anyscribecli.config.settings import Settings

# Minimum free space required (500 MB)
MIN_FREE_BYTES = 500 * 1024 * 1024

# Provider -> env var mapping
_PROVIDER_ENV_VARS: dict[str, str] = {
    "openai": "OPENAI_API_KEY",
    "deepgram": "DEEPGRAM_API_KEY",
    "elevenlabs": "ELEVENLABS_API_KEY",
    "sargam": "SARGAM_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
}

SUPPORTED_AUDIO_EXTS = {
    ".mp3",
    ".mp4",
    ".m4a",
    ".wav",
    ".opus",
    ".ogg",
    ".flac",
    ".webm",
    ".aac",
    ".wma",
}


def preflight_check(settings: Settings, url: str) -> None:
    """Validate prerequisites before starting the pipeline.

    Raises RuntimeError with actionable messages on failure.
    """
    # 1. Check ffmpeg / ffprobe
    if not shutil.which("ffmpeg"):
        raise RuntimeError(
            "ffmpeg not found. Install it:\n"
            "  macOS:  brew install ffmpeg\n"
            "  Linux:  sudo apt install ffmpeg\n"
            "  Or run: scribe doctor"
        )
    if not shutil.which("ffprobe"):
        raise RuntimeError(
            "ffprobe not found (usually bundled with ffmpeg). Install ffmpeg:\n"
            "  macOS:  brew install ffmpeg\n"
            "  Linux:  sudo apt install ffmpeg"
        )

    # 2. Check API key for configured provider
    env_var = _PROVIDER_ENV_VARS.get(settings.provider)
    if env_var and not os.environ.get(env_var):
        raise RuntimeError(
            f"{env_var} not set for provider '{settings.provider}'.\n"
            f"  Fix: scribe config set {settings.provider}_api_key YOUR_KEY\n"
            f"  Or:  scribe onboard --force"
        )

    # 3. Check disk space
    check_dir = TMP_DIR.parent if TMP_DIR.parent.exists() else Path.home()
    free = shutil.disk_usage(check_dir).free
    if free < MIN_FREE_BYTES:
        raise RuntimeError(
            f"Low disk space: {free // (1024 * 1024)}MB free. "
            f"Need at least {MIN_FREE_BYTES // (1024 * 1024)}MB for audio processing."
        )

    # 4. Validate local file format
    is_local = not url.startswith("http://") and not url.startswith("https://")
    if is_local:
        p = Path(url)
        if not p.exists():
            raise RuntimeError(f"File not found: {p}")
        if p.suffix.lower() not in SUPPORTED_AUDIO_EXTS:
            raise RuntimeError(
                f"Unsupported format: {p.suffix}\n"
                f"Supported: {', '.join(sorted(SUPPORTED_AUDIO_EXTS))}"
            )
