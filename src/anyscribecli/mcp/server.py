"""MCP server for scribe — transcription tools for AI harnesses.

Exposes scribe's core functionality (transcribe, download, config, providers)
as MCP tools for Claude Desktop, Cursor, Windsurf, and other AI clients.

Entry point: `scribe-mcp` (registered in pyproject.toml).
"""

from __future__ import annotations

import json
import os
import shutil
import tempfile
from pathlib import Path
from typing import Optional

from mcp.server.fastmcp import FastMCP

from anyscribecli import __version__

mcp = FastMCP(
    "scribe",
    instructions=(
        "Transcription CLI — download and transcribe video/audio from YouTube, "
        "Instagram, or local files into structured markdown. Use transcribe to "
        "process a URL, list_transcripts to browse results, get_config to check "
        "settings, and list_providers to see available transcription services."
    ),
)


def _load_settings():
    """Load config and env, return Settings object."""
    from anyscribecli.config.settings import load_config, load_env

    load_env()
    return load_config()


# ── Transcription ────────────────────────────────────────────


@mcp.tool()
def transcribe(
    url: str,
    provider: Optional[str] = None,
    language: Optional[str] = None,
) -> str:
    """Transcribe a video/audio URL or local file to markdown.

    Downloads audio, transcribes via API, and saves a formatted markdown
    file to the Obsidian workspace. Returns metadata about the result.

    Args:
        url: YouTube/Instagram URL or local file path. Always quote URLs.
        provider: Override provider (openai, elevenlabs, sargam, openrouter, local).
        language: Language code (en, es, fr, hi, etc.) or "auto" for detection.

    Returns:
        JSON with success status, file path, title, duration, word count, provider.
    """
    from anyscribecli.core.orchestrator import process

    settings = _load_settings()
    if provider:
        settings.provider = provider
    if language:
        settings.language = language

    try:
        result = process(url, settings, quiet=True)
        return json.dumps({
            "success": True,
            "file": str(result.file_path),
            "title": result.title,
            "platform": result.platform,
            "duration": result.duration,
            "language": result.language,
            "word_count": result.word_count,
            "provider": result.provider,
        })
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})


@mcp.tool()
def batch_transcribe(
    urls: list[str],
    provider: Optional[str] = None,
    language: Optional[str] = None,
    stop_on_error: bool = False,
) -> str:
    """Transcribe multiple URLs or file paths.

    Processes each URL sequentially. Returns a summary with per-URL results.

    Args:
        urls: List of YouTube/Instagram URLs or local file paths.
        provider: Override provider for all transcriptions.
        language: Override language for all transcriptions.
        stop_on_error: Stop processing at first failure.

    Returns:
        JSON with total, succeeded, failed counts, and per-URL results.
    """
    from anyscribecli.core.orchestrator import process

    settings = _load_settings()
    if provider:
        settings.provider = provider
    if language:
        settings.language = language

    results = []
    succeeded = 0
    failed = 0

    for url in urls:
        try:
            result = process(url, settings, quiet=True)
            succeeded += 1
            results.append({
                "success": True,
                "url": url,
                "file": str(result.file_path),
                "title": result.title,
                "platform": result.platform,
                "duration": result.duration,
                "language": result.language,
                "word_count": result.word_count,
            })
        except Exception as e:
            failed += 1
            results.append({
                "success": False,
                "url": url,
                "error": str(e),
            })
            if stop_on_error:
                break

    return json.dumps({
        "total": len(urls),
        "succeeded": succeeded,
        "failed": failed,
        "results": results,
    })


# ── Download ─────────────────────────────────────────────────


@mcp.tool()
def download(
    url: str,
    audio_only: bool = False,
) -> str:
    """Download video or audio from a URL without transcribing.

    Saves to ~/.anyscribecli/downloads/video/ or audio/.

    Args:
        url: YouTube or Instagram URL.
        audio_only: Download audio only (smaller file).

    Returns:
        JSON with file path, title, platform, and type.
    """
    from anyscribecli.config.paths import TMP_DIR, AUDIO_DIR
    from anyscribecli.downloaders.registry import get_downloader, detect_platform
    from anyscribecli.vault.writer import slugify

    _load_settings()  # loads env for credentials

    TMP_DIR.mkdir(parents=True, exist_ok=True)
    tmp_dir = Path(tempfile.mkdtemp(dir=TMP_DIR))

    try:
        platform = detect_platform(url)

        if audio_only:
            downloader = get_downloader(url)
            dl_result = downloader.download(url, tmp_dir)
            slug = slugify(dl_result.title) or "untitled"
            dest_dir = AUDIO_DIR / platform
            dest_dir.mkdir(parents=True, exist_ok=True)
            dest = dest_dir / f"{slug}{dl_result.audio_path.suffix}"
            shutil.copy2(dl_result.audio_path, dest)
            return json.dumps({
                "success": True,
                "file": str(dest),
                "title": dl_result.title,
                "platform": platform,
                "type": "audio",
                "duration": dl_result.duration,
            })
        else:
            from anyscribecli.cli.download import _download_video

            result = _download_video(url, platform, tmp_dir, quiet=True)
            return json.dumps({"success": True, **result})

    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})
    finally:
        if tmp_dir.exists():
            shutil.rmtree(tmp_dir, ignore_errors=True)


# ── Workspace ────────────────────────────────────────────────


@mcp.tool()
def list_transcripts(
    platform: Optional[str] = None,
    limit: int = 20,
) -> str:
    """List transcripts in the workspace.

    Reads frontmatter from markdown files in the workspace to return
    a list of transcripts with metadata.

    Args:
        platform: Filter by platform (youtube, instagram, local).
        limit: Maximum number of results (default 20, newest first).

    Returns:
        JSON array of transcript metadata (title, date, platform, duration, path).
    """
    import yaml

    from anyscribecli.config.paths import get_workspace_dir

    ws = get_workspace_dir()
    sources = ws / "sources"

    if not sources.is_dir():
        return json.dumps([])

    entries = []
    search_dir = sources / platform if platform else sources

    if not search_dir.is_dir():
        return json.dumps([])

    for md_file in search_dir.rglob("*.md"):
        if md_file.name.startswith("_"):
            continue
        try:
            text = md_file.read_text()
            if not text.startswith("---"):
                continue
            end = text.index("---", 3)
            fm = yaml.safe_load(text[3:end])
            if not isinstance(fm, dict):
                continue
            entries.append({
                "title": fm.get("title", md_file.stem),
                "date": fm.get("date_processed", ""),
                "platform": fm.get("platform", ""),
                "duration": fm.get("duration", ""),
                "language": fm.get("language", ""),
                "word_count": fm.get("word_count", 0),
                "provider": fm.get("provider", ""),
                "source_url": fm.get("source", ""),
                "file": str(md_file),
            })
        except Exception:
            continue

    # Sort newest first
    entries.sort(key=lambda e: e["date"], reverse=True)
    return json.dumps(entries[:limit])


# ── Configuration ────────────────────────────────────────────


@mcp.tool()
def get_config() -> str:
    """Show current scribe configuration.

    Returns all settings including resolved workspace path.
    Sensitive values (API keys) are NOT included — they live in .env.

    Returns:
        JSON with all config settings and resolved workspace path.
    """
    from anyscribecli.config.paths import get_workspace_dir

    settings = _load_settings()
    data = settings.to_dict()
    data["_resolved_workspace"] = str(get_workspace_dir())
    data["_version"] = __version__
    return json.dumps(data)


@mcp.tool()
def set_config(key: str, value: str) -> str:
    """Change a scribe configuration setting.

    Use dot-notation for nested keys (e.g., "instagram.username").

    Args:
        key: Setting key (provider, language, keep_media, workspace_path, etc.).
        value: New value. Booleans accept true/false/yes/no.

    Returns:
        JSON with success status and the updated key/value.
    """
    from anyscribecli.config.settings import Settings, load_config, save_config

    settings = load_config()
    data = settings.to_dict()

    keys = key.split(".")
    target = data
    for k in keys[:-1]:
        if k not in target or not isinstance(target[k], dict):
            return json.dumps({"success": False, "error": f"Invalid key: {key}"})
        target = target[k]

    final_key = keys[-1]
    if final_key not in target:
        available = list(data.keys())
        return json.dumps({
            "success": False,
            "error": f"Unknown key: {key}",
            "available_keys": available,
        })

    # Type coercion
    old_value = target[final_key]
    if isinstance(old_value, bool):
        typed_value = value.lower() in ("true", "1", "yes")
    elif isinstance(old_value, int):
        try:
            typed_value = int(value)
        except ValueError:
            return json.dumps({"success": False, "error": f"Expected integer for {key}"})
    else:
        typed_value = value

    target[final_key] = typed_value
    new_settings = Settings.from_dict(data)
    save_config(new_settings)

    return json.dumps({"success": True, "key": key, "value": typed_value})


# ── Providers ────────────────────────────────────────────────


@mcp.tool()
def list_providers() -> str:
    """List available transcription providers.

    Returns:
        JSON array of providers with name and active status.
    """
    from anyscribecli.providers import list_providers as _list_providers

    settings = _load_settings()
    active = settings.provider
    providers = _list_providers()

    return json.dumps([
        {"name": p, "active": p == active}
        for p in providers
    ])


@mcp.tool()
def test_provider(name: Optional[str] = None) -> str:
    """Test a provider's API key and connectivity.

    Args:
        name: Provider to test. Defaults to the active provider.

    Returns:
        JSON with provider name, status, and any issues.
    """
    from anyscribecli.providers import get_provider

    settings = _load_settings()
    provider_name = name or settings.provider

    key_map = {
        "openai": "OPENAI_API_KEY",
        "openrouter": "OPENROUTER_API_KEY",
        "elevenlabs": "ELEVENLABS_API_KEY",
        "sargam": "SARGAM_API_KEY",
    }

    try:
        provider = get_provider(provider_name)
    except ValueError as e:
        return json.dumps({"success": False, "provider": provider_name, "error": str(e)})

    env_var = key_map.get(provider_name)
    api_key_set = True
    if env_var:
        api_key_set = bool(os.environ.get(env_var))

    return json.dumps({
        "success": True,
        "provider": provider_name,
        "class": provider.__class__.__name__,
        "api_key_env": env_var,
        "api_key_set": api_key_set,
        "requires_api_key": env_var is not None,
    })


# ── Diagnostics ──────────────────────────────────────────────


@mcp.tool()
def doctor() -> str:
    """Run diagnostic checks on scribe installation.

    Checks dependencies, config, workspace, and skill status.

    Returns:
        JSON with system health status.
    """
    from anyscribecli.config.paths import (
        APP_HOME,
        ASCLI_SKILL_TARGET,
        CONFIG_FILE,
        ENV_FILE,
        get_workspace_dir,
    )
    from anyscribecli.core.deps import check_dependencies
    from anyscribecli.core.updater import get_install_path

    # Dependencies
    dep_results = check_dependencies()
    deps = []
    for r in dep_results:
        deps.append({
            "name": r.dep.name,
            "found": r.found,
            "version": r.version,
            "required": r.dep.required,
        })

    # Config
    config = {
        "app_directory": APP_HOME.exists(),
        "config_file": CONFIG_FILE.exists(),
        "env_file": ENV_FILE.exists(),
        "workspace": get_workspace_dir().exists(),
        "workspace_path": str(get_workspace_dir()),
    }

    # Installation
    install = {
        "version": __version__,
        "type": "git (editable)" if get_install_path() else "pip package",
    }
    repo = get_install_path()
    if repo:
        install["repo_path"] = str(repo)

    # Skill
    skill = {"installed": ASCLI_SKILL_TARGET.exists()}
    if ASCLI_SKILL_TARGET.exists():
        version_marker = ASCLI_SKILL_TARGET / ".version"
        try:
            skill["version"] = version_marker.read_text().strip()
        except (FileNotFoundError, OSError):
            skill["version"] = "unknown"
        skill["current"] = skill.get("version") == __version__

    return json.dumps({
        "dependencies": deps,
        "config": config,
        "installation": install,
        "skill": skill,
    })


# ── Resources ────────────────────────────────────────────────


@mcp.resource("scribe://config")
def resource_config() -> str:
    """Current scribe configuration."""
    return get_config()


@mcp.resource("scribe://providers")
def resource_providers() -> str:
    """Available transcription providers."""
    return list_providers()


@mcp.resource("scribe://workspace")
def resource_workspace() -> str:
    """Workspace info and transcript count."""
    from anyscribecli.config.paths import get_workspace_dir

    ws = get_workspace_dir()
    sources = ws / "sources"

    count = 0
    platforms = {}
    if sources.is_dir():
        for md_file in sources.rglob("*.md"):
            if not md_file.name.startswith("_"):
                count += 1
                # Extract platform from path
                try:
                    platform = md_file.relative_to(sources).parts[0]
                    platforms[platform] = platforms.get(platform, 0) + 1
                except (IndexError, ValueError):
                    pass

    return json.dumps({
        "workspace_path": str(ws),
        "exists": ws.exists(),
        "total_transcripts": count,
        "by_platform": platforms,
    })


# ── Entry point ──────────────────────────────────────────────


def main() -> None:
    """Run the MCP server (stdio transport)."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
