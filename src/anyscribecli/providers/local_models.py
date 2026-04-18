"""Local Whisper model vocabulary and on-disk cache management.

Single source of truth for the sizes the user can pick and the HuggingFace
repos they map to. Wraps ``huggingface_hub`` for list/download/delete so the
rest of the codebase never has to touch the HF cache layout directly.

These helpers are safe to import before ``faster-whisper`` is installed:
``list_cached_models()`` returns ``[]`` and ``is_cached()`` returns ``False``
when the hub library isn't available, so status UIs can render a "not set up"
state without crashing.
"""

from __future__ import annotations

from typing import Any

MODEL_SIZES: list[str] = ["tiny", "base", "small", "medium", "large-v3"]

RECOMMENDED_MODEL: str = "base"

# faster-whisper loads these HF repos directly. Keep the keys in lockstep with
# MODEL_SIZES; the size string is also what we accept on the CLI and store
# in settings.local_model.
MODEL_REPOS: dict[str, str] = {
    "tiny": "Systran/faster-whisper-tiny",
    "base": "Systran/faster-whisper-base",
    "small": "Systran/faster-whisper-small",
    "medium": "Systran/faster-whisper-medium",
    "large-v3": "Systran/faster-whisper-large-v3",
}

# Approximate figures used by the UI (CLI + Web) to help the user pick a size.
# Download sizes are what HF reports for the int8 CTranslate2 weights; RAM
# numbers are typical peak usage during transcription on CPU.
MODEL_SPECS: dict[str, dict[str, Any]] = {
    "tiny": {
        "download_mb": 75,
        "ram_mb": 400,
        "relative_speed": "~10x realtime (CPU)",
        "quality": "lowest",
    },
    "base": {
        "download_mb": 145,
        "ram_mb": 600,
        "relative_speed": "~7x realtime (CPU)",
        "quality": "good for most use cases",
    },
    "small": {
        "download_mb": 480,
        "ram_mb": 1200,
        "relative_speed": "~4x realtime (CPU)",
        "quality": "noticeably better than base",
    },
    "medium": {
        "download_mb": 1500,
        "ram_mb": 2500,
        "relative_speed": "~2x realtime (CPU)",
        "quality": "near-large for many languages",
    },
    "large-v3": {
        "download_mb": 3000,
        "ram_mb": 5000,
        "relative_speed": "~1x realtime (CPU); fast on GPU",
        "quality": "highest",
    },
}


def validate_size(size: str) -> None:
    """Raise ValueError if ``size`` isn't one of MODEL_SIZES."""
    if size not in MODEL_SIZES:
        raise ValueError(f"unknown model size '{size}'. Choices: {', '.join(MODEL_SIZES)}")


def _safe_import_hub():
    """Return the huggingface_hub module or None if unavailable."""
    try:
        import huggingface_hub  # type: ignore[import-not-found]

        return huggingface_hub
    except ImportError:
        return None


def faster_whisper_importable() -> bool:
    """Return True if ``faster_whisper`` can be imported right now."""
    try:
        import faster_whisper  # type: ignore[import-not-found]  # noqa: F401

        return True
    except ImportError:
        return False


def faster_whisper_version() -> str | None:
    """Return faster-whisper's installed version, or None if not importable."""
    try:
        import faster_whisper  # type: ignore[import-not-found]

        return getattr(faster_whisper, "__version__", None)
    except ImportError:
        return None


def list_cached_models() -> list[dict[str, Any]]:
    """Return one entry per MODEL_SIZES with cache status + disk bytes.

    Safe before setup: if huggingface_hub isn't importable, every entry is
    ``cached=False, bytes=0``.
    """
    cached_bytes: dict[str, int] = {}
    hub = _safe_import_hub()
    if hub is not None:
        try:
            info = hub.scan_cache_dir()
            repo_to_size = {repo: size for size, repo in MODEL_REPOS.items()}
            for repo in info.repos:
                size = repo_to_size.get(repo.repo_id)
                if size:
                    cached_bytes[size] = cached_bytes.get(size, 0) + int(repo.size_on_disk)
        except Exception:
            # scan_cache_dir can fail on a half-written cache; treat as empty.
            pass

    result = []
    for size in MODEL_SIZES:
        bytes_on_disk = cached_bytes.get(size, 0)
        result.append(
            {
                "size": size,
                "repo": MODEL_REPOS[size],
                "cached": bytes_on_disk > 0,
                "bytes": bytes_on_disk,
                "spec": MODEL_SPECS[size],
            }
        )
    return result


def is_cached(size: str) -> bool:
    """Return True if any revision of the repo for ``size`` is in the HF cache."""
    validate_size(size)
    for entry in list_cached_models():
        if entry["size"] == size:
            return bool(entry["cached"])
    return False


def any_model_cached() -> bool:
    """Return True if at least one size is cached."""
    return any(e["cached"] for e in list_cached_models())


def pull_model(size: str) -> dict[str, Any]:
    """Download the weights for ``size`` via huggingface_hub. Idempotent.

    Returns a dict with keys ``{status, size, repo, bytes}``. ``status`` is
    ``"already_present"`` if already fully cached, otherwise ``"downloaded"``.
    Raises if huggingface_hub or faster-whisper aren't installed.
    """
    validate_size(size)

    if not faster_whisper_importable():
        raise RuntimeError(
            "faster-whisper is not installed. Run `scribe local setup --model <size>` "
            "to install it and pull a model."
        )

    hub = _safe_import_hub()
    if hub is None:
        raise RuntimeError(
            "huggingface_hub is not available. Reinstall anyscribecli to restore it."
        )

    repo = MODEL_REPOS[size]

    if is_cached(size):
        bytes_on_disk = 0
        for entry in list_cached_models():
            if entry["size"] == size:
                bytes_on_disk = int(entry["bytes"])
                break
        return {
            "status": "already_present",
            "size": size,
            "repo": repo,
            "bytes": bytes_on_disk,
        }

    hub.snapshot_download(repo_id=repo)

    bytes_on_disk = 0
    for entry in list_cached_models():
        if entry["size"] == size:
            bytes_on_disk = int(entry["bytes"])
            break

    return {
        "status": "downloaded",
        "size": size,
        "repo": repo,
        "bytes": bytes_on_disk,
    }


def delete_model(size: str) -> dict[str, Any]:
    """Remove all cached revisions of ``size`` from the HF cache.

    Returns ``{status, size, bytes_freed}``. ``status`` is ``"not_present"``
    if nothing was cached, otherwise ``"removed"``.
    """
    validate_size(size)

    hub = _safe_import_hub()
    if hub is None:
        return {"status": "not_present", "size": size, "bytes_freed": 0}

    try:
        info = hub.scan_cache_dir()
    except Exception:
        return {"status": "not_present", "size": size, "bytes_freed": 0}

    repo_id = MODEL_REPOS[size]
    commit_hashes: list[str] = []
    total_bytes = 0
    for repo in info.repos:
        if repo.repo_id != repo_id:
            continue
        for rev in repo.revisions:
            commit_hashes.append(rev.commit_hash)
            total_bytes += int(rev.size_on_disk)

    if not commit_hashes:
        return {"status": "not_present", "size": size, "bytes_freed": 0}

    strategy = info.delete_revisions(*commit_hashes)
    strategy.execute()
    return {"status": "removed", "size": size, "bytes_freed": total_bytes}


def delete_all_models() -> dict[str, Any]:
    """Remove every cached size. Used by teardown.

    Returns ``{models_deleted: [...], bytes_freed: int}``.
    """
    deleted: list[str] = []
    total = 0
    for size in MODEL_SIZES:
        res = delete_model(size)
        if res["status"] == "removed":
            deleted.append(size)
            total += int(res["bytes_freed"])
    return {"models_deleted": deleted, "bytes_freed": total}
