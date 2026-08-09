"""Pre-flight checks — validate prerequisites before starting the pipeline."""

from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path

from anyscribe.config.paths import TMP_DIR
from anyscribe.config.settings import Settings
from anyscribe.providers import PROVIDER_KEY_ENV

# Minimum free space required (500 MB)
MIN_FREE_BYTES = 500 * 1024 * 1024

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
            "  Or run: anyscribe doctor"
        )
    if not shutil.which("ffprobe"):
        raise RuntimeError(
            "ffprobe not found (usually bundled with ffmpeg). Install ffmpeg:\n"
            "  macOS:  brew install ffmpeg\n"
            "  Linux:  sudo apt install ffmpeg"
        )

    # 2. Check API key for configured provider
    env_var = PROVIDER_KEY_ENV.get(settings.provider)
    if env_var and not os.environ.get(env_var):
        raise RuntimeError(
            f"{env_var} not set for provider '{settings.provider}'.\n"
            f"  Fix: anyscribe config set {settings.provider}_api_key YOUR_KEY\n"
            f"  Or:  anyscribe onboard --force"
        )

    # 3. Validate local file format before environment-dependent disk checks.
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

    # 4. Check disk space
    if TMP_DIR.parent.exists():
        check_dir = TMP_DIR.parent
    else:
        try:
            check_dir = Path.home()
        except RuntimeError:
            check_dir = Path(tempfile.gettempdir())
    free = shutil.disk_usage(check_dir).free
    if free < MIN_FREE_BYTES:
        raise RuntimeError(
            f"Low disk space: {free // (1024 * 1024)}MB free. "
            f"Need at least {MIN_FREE_BYTES // (1024 * 1024)}MB for audio processing."
        )
