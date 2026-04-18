"""Unified setup + teardown for local transcription.

Local transcription needs two things on disk before it can run:

1. ``faster-whisper`` installed into the same Python environment as ``scribe``.
2. At least one Whisper model downloaded into the HuggingFace cache.

This module detects how ``scribe`` itself was installed (pipx / venv pip /
system pip) and runs the appropriate subprocess to add faster-whisper, then
pulls the requested model. The same routine powers the CLI (``scribe local
setup``), the onboarding wizard, and the Web UI "Set up local transcription"
button — one code path, consistent behaviour.

Never raises on subprocess failure — callers get a structured dict with the
exact command that ran and the captured stderr so they (or an agent) can
resolve it manually.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable, Literal

from anyscribecli.config.settings import load_config, save_config
from anyscribecli.core.deps import check_dependencies
from anyscribecli.providers.local_models import (
    MODEL_SIZES,
    any_model_cached,
    delete_all_models,
    faster_whisper_importable,
    faster_whisper_version,
    list_cached_models,
    pull_model,
    validate_size,
)

FASTER_WHISPER_SPEC = "faster-whisper>=1.0"

InstallMethod = Literal["pipx", "venv", "system", "unknown"]

ProgressFn = Callable[[dict[str, Any]], None]


def _emit(on_progress: ProgressFn | None, event: dict[str, Any]) -> None:
    if on_progress is not None:
        try:
            on_progress(event)
        except Exception:
            pass


def detect_install_method() -> InstallMethod:
    """Figure out how anyscribecli itself was installed.

    The detection drives which command we shell out to when adding or removing
    faster-whisper. Order matters: pipx lives inside its own venv, so we have
    to check the pipx markers before the generic venv heuristic.
    """
    exe = Path(sys.executable).resolve()

    pipx_home = os.environ.get("PIPX_HOME")
    pipx_default = Path.home() / ".local" / "pipx"
    pipx_roots = [Path(p) for p in [pipx_home, str(pipx_default)] if p]
    for root in pipx_roots:
        try:
            if root.exists() and str(exe).startswith(str(root.resolve())):
                return "pipx"
        except OSError:
            continue

    # Generic venv check: prefix differs from base_prefix in venvs/virtualenvs.
    if getattr(sys, "prefix", None) and getattr(sys, "base_prefix", None):
        if sys.prefix != sys.base_prefix:
            return "venv"

    # System Python (Homebrew, OS package, etc.). pip may be blocked by PEP 668.
    return "system"


def _pipx_venv_name() -> str | None:
    """Return the pipx venv name that owns the current Python, if detectable."""
    exe = Path(sys.executable).resolve()
    for parent in exe.parents:
        if parent.parent.name == "venvs" and parent.parent.parent.name == "pipx":
            return parent.name
    return None


def _install_command(method: InstallMethod) -> list[str]:
    """Build the argv list to install faster-whisper for the given method."""
    if method == "pipx":
        venv = _pipx_venv_name() or "anyscribecli"
        return ["pipx", "inject", venv, FASTER_WHISPER_SPEC]
    return [sys.executable, "-m", "pip", "install", FASTER_WHISPER_SPEC]


def _uninstall_command(method: InstallMethod) -> list[str]:
    if method == "pipx":
        venv = _pipx_venv_name() or "anyscribecli"
        return ["pipx", "uninject", venv, "faster-whisper"]
    return [sys.executable, "-m", "pip", "uninstall", "-y", "faster-whisper"]


def _run(cmd: list[str], timeout: int = 600) -> tuple[int, str, str]:
    """Run ``cmd`` with captured stdout/stderr. Never raises on nonzero."""
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return proc.returncode, proc.stdout, proc.stderr
    except (FileNotFoundError, PermissionError) as e:
        return 127, "", str(e)
    except subprocess.TimeoutExpired as e:
        return 124, "", f"timed out after {timeout}s: {e}"


def install_faster_whisper(
    on_progress: ProgressFn | None = None,
) -> dict[str, Any]:
    """Install faster-whisper into the running Python environment. Idempotent.

    Returns ``{status, method, command, version?, stderr?}``. ``status`` is
    one of ``"already_installed" | "installed" | "failed"``.
    """
    if faster_whisper_importable():
        return {
            "status": "already_installed",
            "method": detect_install_method(),
            "command": None,
            "version": faster_whisper_version(),
        }

    method = detect_install_method()
    cmd = _install_command(method)

    _emit(on_progress, {"event": "installing_package", "method": method, "command": cmd})

    # Guard against pipx missing on PATH in the pipx branch — fall back to pip.
    if method == "pipx" and shutil.which("pipx") is None:
        cmd = [sys.executable, "-m", "pip", "install", FASTER_WHISPER_SPEC]
        method = "venv"
        _emit(on_progress, {"event": "pipx_not_on_path_fallback", "command": cmd})

    rc, _, stderr = _run(cmd)
    if rc != 0:
        return {
            "status": "failed",
            "method": method,
            "command": cmd,
            "stderr": stderr.strip(),
        }

    _emit(on_progress, {"event": "package_installed", "method": method})

    return {
        "status": "installed",
        "method": method,
        "command": cmd,
        "version": faster_whisper_version(),
    }


def uninstall_faster_whisper(
    on_progress: ProgressFn | None = None,
) -> dict[str, Any]:
    """Remove faster-whisper. Returns ``{status, method, command, stderr?}``."""
    if not faster_whisper_importable():
        return {
            "status": "already_absent",
            "method": detect_install_method(),
            "command": None,
        }

    method = detect_install_method()
    cmd = _uninstall_command(method)

    if method == "pipx" and shutil.which("pipx") is None:
        cmd = [sys.executable, "-m", "pip", "uninstall", "-y", "faster-whisper"]
        method = "venv"

    _emit(on_progress, {"event": "uninstalling_package", "method": method, "command": cmd})

    rc, _, stderr = _run(cmd)
    if rc != 0:
        return {
            "status": "failed",
            "method": method,
            "command": cmd,
            "stderr": stderr.strip(),
        }
    return {"status": "removed", "method": method, "command": cmd}


def _ffmpeg_status() -> dict[str, Any]:
    """Return ``{ok, message}`` for ffmpeg using the existing deps check."""
    results = check_dependencies()
    for r in results:
        if r.dep.name == "ffmpeg":
            return {
                "ok": bool(r.found),
                "message": (r.version or "ffmpeg found") if r.found else "ffmpeg not found on PATH",
            }
    return {"ok": False, "message": "ffmpeg not found on PATH"}


def check_status() -> dict[str, Any]:
    """Snapshot of everything local-transcription-related on this machine.

    Safe to call before setup — faster_whisper_installed will just be False
    and models will all be uncached.
    """
    settings = load_config()
    fw_ok = faster_whisper_importable()
    models = list_cached_models()
    total_bytes = sum(int(m["bytes"]) for m in models)
    ffmpeg = _ffmpeg_status()

    return {
        "set_up": fw_ok and ffmpeg["ok"] and any(m["cached"] for m in models),
        "faster_whisper_installed": fw_ok,
        "faster_whisper_version": faster_whisper_version(),
        "ffmpeg_ok": ffmpeg["ok"],
        "ffmpeg_message": ffmpeg["message"],
        "default_model": settings.local_model,
        "models": [
            {
                "size": m["size"],
                "cached": m["cached"],
                "bytes": m["bytes"],
                "repo": m["repo"],
                "spec": m["spec"],
            }
            for m in models
        ],
        "total_disk_bytes": total_bytes,
        "install_method": detect_install_method(),
    }


def run_setup(
    model_size: str,
    on_progress: ProgressFn | None = None,
) -> dict[str, Any]:
    """The unified setup routine: install + pull + persist.

    Does NOT change ``settings.provider`` — setup prepares local; swapping the
    default provider stays with the user.
    """
    validate_size(model_size)

    _emit(on_progress, {"event": "detecting_install_method"})

    install_result = install_faster_whisper(on_progress=on_progress)
    if install_result["status"] == "failed":
        return {
            "status": "failed",
            "phase": "install",
            "install": install_result,
        }

    _emit(on_progress, {"event": "downloading_model", "size": model_size})

    try:
        pull_result = pull_model(model_size)
    except Exception as e:
        return {
            "status": "failed",
            "phase": "download",
            "install": install_result,
            "error": str(e),
        }

    _emit(
        on_progress,
        {"event": "model_downloaded", "size": model_size, "bytes": pull_result.get("bytes", 0)},
    )

    settings = load_config()
    settings.local_model = model_size
    save_config(settings)

    _emit(on_progress, {"event": "done"})

    return {
        "status": "set_up",
        "install": install_result,
        "model": pull_result,
        "default_model": model_size,
    }


def run_teardown(on_progress: ProgressFn | None = None) -> dict[str, Any]:
    """Uninstall faster-whisper, delete all cached models, reset provider.

    ``settings.local_model`` is preserved — it's harmless and re-used if the
    user sets up again later. ``settings.provider`` flips to ``"openai"`` only
    if it was currently ``"local"``, so the user isn't left with a broken
    default.
    """
    _emit(on_progress, {"event": "deleting_models"})
    deleted = delete_all_models()

    _emit(on_progress, {"event": "uninstalling_package"})
    uninstall = uninstall_faster_whisper(on_progress=on_progress)

    settings = load_config()
    provider_changed = False
    if settings.provider == "local":
        settings.provider = "openai"
        provider_changed = True
        save_config(settings)

    _emit(on_progress, {"event": "done"})

    return {
        "status": "removed",
        "models_deleted": deleted["models_deleted"],
        "bytes_freed": deleted["bytes_freed"],
        "uninstall": uninstall,
        "provider_reset": provider_changed,
    }


def valid_model_sizes() -> list[str]:
    """Shorthand for callers that want the list without touching local_models."""
    return list(MODEL_SIZES)


def local_ready() -> bool:
    """Quick predicate for the Web UI green-dot check.

    ``True`` when faster-whisper imports, ffmpeg is on PATH, and at least one
    model is cached. Used by the providers list endpoint.
    """
    if not faster_whisper_importable():
        return False
    if not _ffmpeg_status()["ok"]:
        return False
    return any_model_cached()
