"""MCP server for anyscribe — transcription tools for AI harnesses.

Exposes anyscribe's core functionality (transcribe, download, config, providers)
as MCP tools for Claude Desktop, Cursor, Windsurf, and other AI clients.

Entry point: `anyscribe-mcp` (registered in pyproject.toml; `scribe-mcp` is a
permanent alias).
"""

from __future__ import annotations

import json
import os
import shutil
import tempfile
from pathlib import Path
from typing import Optional

from mcp.server.fastmcp import FastMCP

from anyscribe import __version__
from anyscribe.providers import PROVIDER_KEY_ENV

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
    from anyscribe.config.settings import load_config, load_env

    load_env()
    return load_config()


# ── Transcription ────────────────────────────────────────────


@mcp.tool()
def transcribe(
    url: str,
    provider: Optional[str] = None,
    model: Optional[str] = None,
    language: Optional[str] = None,
    diarize: bool = False,
    quality: Optional[str] = None,
    force: bool = False,
) -> str:
    """Transcribe a video/audio URL or local file to markdown.

    Downloads audio, transcribes via API, and saves a formatted markdown
    file to the Obsidian workspace. Returns metadata about the result.
    If the source was already transcribed, returns the existing file with
    "cached": true instead of re-transcribing (unless force is set).

    Args:
        url: YouTube/Instagram URL or local file path. Always quote URLs.
        provider: Override provider (openai, elevenlabs, sargam, deepgram, groq, openrouter, local).
        model: Override the provider's model (e.g. gpt-transcribe for openai,
            whisper-large-v3 for groq). See list_providers for options.
        language: Language code (en, es, fr, hi, hi-Latn, etc.) or "auto" for detection.
        diarize: Enable speaker diarization for multi-speaker transcripts.
        quality: Quality preset (accuracy | balanced | cost | free) — auto-routes
            to a provider; ignored when an explicit provider is given.
        force: Re-transcribe even if this source already exists in the workspace.

    Returns:
        JSON with success status, file path, title, duration, word count, provider, cached.
    """
    from anyscribe.core.orchestrator import process
    from anyscribe.core.resolve import resolve_run

    settings = _load_settings()
    if language:
        settings.language = language
    if diarize:
        settings.diarize = True
        if settings.output_format == "clean":
            settings.output_format = "diarized"
    if quality:
        settings.quality = quality

    try:
        plan = resolve_run(settings, cli_provider=provider, cli_model=model, diarize=diarize)
        settings.provider = plan.provider
        result = process(url, settings, quiet=True, force=force, model=plan.model)
        return json.dumps(
            {
                "success": True,
                "file": str(result.file_path),
                "title": result.title,
                "platform": result.platform,
                "duration": result.duration,
                "language": result.language,
                "word_count": result.word_count,
                "provider": result.provider,
                "model": plan.model,
                "notes": plan.notes,
                "cached": result.cached,
            }
        )
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})


@mcp.tool()
def batch_transcribe(
    urls: list[str],
    provider: Optional[str] = None,
    model: Optional[str] = None,
    language: Optional[str] = None,
    diarize: bool = False,
    stop_on_error: bool = False,
    quality: Optional[str] = None,
    force: bool = False,
) -> str:
    """Transcribe multiple URLs or file paths.

    Processes each URL sequentially. Returns a summary with per-URL results.
    Already-transcribed sources are skipped and returned with "cached": true
    (unless force is set).

    Args:
        urls: List of YouTube/Instagram URLs or local file paths.
        provider: Override provider for all transcriptions.
        model: Override the provider's model for all transcriptions.
        language: Override language for all transcriptions.
        diarize: Enable speaker diarization for multi-speaker transcripts.
        stop_on_error: Stop processing at first failure.
        quality: Quality preset (accuracy | balanced | cost | free) — auto-routes
            to a provider; ignored when an explicit provider is given.
        force: Re-transcribe even if a source already exists in the workspace.

    Returns:
        JSON with total, succeeded, failed counts, and per-URL results.
    """
    from anyscribe.core.orchestrator import process
    from anyscribe.core.resolve import resolve_run

    settings = _load_settings()
    if language:
        settings.language = language
    if diarize:
        settings.diarize = True
        if settings.output_format == "clean":
            settings.output_format = "diarized"
    if quality:
        settings.quality = quality

    try:
        plan = resolve_run(settings, cli_provider=provider, cli_model=model, diarize=diarize)
    except ValueError as e:
        return json.dumps({"success": False, "total": len(urls), "error": str(e)})
    settings.provider = plan.provider

    results = []
    succeeded = 0
    failed = 0

    for url in urls:
        try:
            result = process(url, settings, quiet=True, force=force, model=plan.model)
            succeeded += 1
            results.append(
                {
                    "success": True,
                    "url": url,
                    "file": str(result.file_path),
                    "title": result.title,
                    "platform": result.platform,
                    "duration": result.duration,
                    "language": result.language,
                    "word_count": result.word_count,
                    "cached": result.cached,
                }
            )
        except Exception as e:
            failed += 1
            results.append(
                {
                    "success": False,
                    "url": url,
                    "error": str(e),
                }
            )
            if stop_on_error:
                break

    return json.dumps(
        {
            "total": len(urls),
            "succeeded": succeeded,
            "failed": failed,
            "provider": plan.provider,
            "model": plan.model,
            "notes": plan.notes,
            "results": results,
        }
    )


# ── Download ─────────────────────────────────────────────────


@mcp.tool()
def download(
    url: str,
    audio_only: bool = False,
) -> str:
    """Download video or audio from a URL without transcribing.

    Saves to ~/.anyscribe/downloads/video/ or audio/.

    Args:
        url: YouTube or Instagram URL.
        audio_only: Download audio only (smaller file).

    Returns:
        JSON with file path, title, platform, and type.
    """
    from anyscribe.config.paths import TMP_DIR, AUDIO_DIR
    from anyscribe.downloaders.registry import get_downloader, detect_platform
    from anyscribe.vault.writer import slugify

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
            return json.dumps(
                {
                    "success": True,
                    "file": str(dest),
                    "title": dl_result.title,
                    "platform": platform,
                    "type": "audio",
                    "duration": dl_result.duration,
                }
            )
        else:
            from anyscribe.cli.download import _download_video

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

    from anyscribe.config.paths import get_workspace_dir

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
            entries.append(
                {
                    "title": fm.get("title", md_file.stem),
                    "date": fm.get("date_processed", ""),
                    "platform": fm.get("platform", ""),
                    "duration": fm.get("duration", ""),
                    "language": fm.get("language", ""),
                    "word_count": fm.get("word_count", 0),
                    "provider": fm.get("provider", ""),
                    "source_url": fm.get("source", ""),
                    "file": str(md_file),
                }
            )
        except Exception:
            continue

    # Sort newest first
    entries.sort(key=lambda e: e["date"], reverse=True)
    return json.dumps(entries[:limit])


@mcp.tool()
def delete_transcript(target: str) -> str:
    """Delete a transcript from the workspace and resync the master index.

    Removes the markdown file and its row in _index.md. Daily logs are
    kept as append-only history. Only files inside the workspace
    sources/ tree can be deleted.

    Args:
        target: Full file path or slug (filename without .md).

    Returns:
        JSON {success, deleted: path} or {success: false, error}.
    """
    from anyscribe.vault.index import delete_transcript as _delete
    from anyscribe.vault.index import find_transcript

    matches = find_transcript(target)
    if not matches:
        return json.dumps({"success": False, "error": f"Transcript not found: {target}"})
    if len(matches) > 1:
        return json.dumps(
            {
                "success": False,
                "error": "Ambiguous slug — matches: " + ", ".join(str(m) for m in matches),
            }
        )
    try:
        _delete(matches[0])
        return json.dumps({"success": True, "deleted": str(matches[0])})
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})


# ── Configuration ────────────────────────────────────────────


@mcp.tool()
def get_config() -> str:
    """Show current anyscribe configuration.

    Returns all settings including resolved workspace path.
    Sensitive values (API keys) are NOT included — they live in .env.

    Returns:
        JSON with all config settings and resolved workspace path.
    """
    from anyscribe.config.paths import get_workspace_dir

    settings = _load_settings()
    data = settings.to_dict()
    data["_resolved_workspace"] = str(get_workspace_dir())
    data["_version"] = __version__
    return json.dumps(data)


@mcp.tool()
def set_config(key: str, value: str) -> str:
    """Change an anyscribe configuration setting.

    Handles every settable key, including API keys (e.g. "openai_api_key",
    written to .env), model pins ("provider_models.<provider>"), user-added
    OpenRouter slugs ("extra_models.openrouter", comma-separated; empty clears)
    and dot-notation nested keys ("instagram.browser").

    Setting "provider" also sets quality="custom" so the choice sticks.

    Args:
        key: Setting key (provider, quality, language, keep_media, ...).
        value: New value. Booleans accept true/false/yes/no.

    Returns:
        JSON: {success, key, value, message} or {success: false, error, choices}.
    """
    from anyscribe.core.config_set import set_value

    outcome = set_value(key, value)
    if not outcome.ok:
        return json.dumps({"success": False, "error": outcome.error, "choices": outcome.choices})
    return json.dumps({"success": True, "key": key, "value": value, "message": outcome.message})


# ── Providers ────────────────────────────────────────────────


@mcp.tool()
def list_providers() -> str:
    """List available transcription providers.

    Returns:
        JSON array of providers with name, active status, the model each will
        use (pinned or default), and the full pickable model list.
    """
    from anyscribe.providers import get_models, list_providers as _list_providers

    settings = _load_settings()
    active = settings.provider

    def _entry(p: str) -> dict:
        models = get_models(p, settings.extra_models)
        return {
            "name": p,
            "active": p == active,
            "model": settings.provider_models.get(p, models[0] if models else ""),
            "models": models,
        }

    return json.dumps([_entry(p) for p in _list_providers()])


@mcp.tool()
def test_provider(name: Optional[str] = None) -> str:
    """Test a provider's API key and connectivity.

    Args:
        name: Provider to test. Defaults to the active provider.

    Returns:
        JSON with provider name, status, and any issues.
    """
    from anyscribe.providers import get_provider, normalize_provider_name

    settings = _load_settings()
    # Canonicalize first — get_provider() normalizes internally, so a raw alias
    # would miss the PROVIDER_KEY_ENV lookup and report api_key_set: true for a
    # provider with no key at all.
    provider_name = normalize_provider_name(name or settings.provider)

    try:
        provider = get_provider(provider_name)
    except ValueError as e:
        return json.dumps({"success": False, "provider": provider_name, "error": str(e)})

    env_var = PROVIDER_KEY_ENV.get(provider_name)
    api_key_set = True
    if env_var:
        api_key_set = bool(os.environ.get(env_var))

    return json.dumps(
        {
            "success": True,
            "provider": provider_name,
            "class": provider.__class__.__name__,
            "api_key_env": env_var,
            "api_key_set": api_key_set,
            "requires_api_key": env_var is not None,
        }
    )


# ── Diagnostics ──────────────────────────────────────────────


@mcp.tool()
def doctor() -> str:
    """Run diagnostic checks on anyscribe installation.

    Checks dependencies, config, workspace, and skill status.

    Returns:
        JSON with system health status.
    """
    from anyscribe.config.paths import (
        APP_HOME,
        ASCLI_SKILL_TARGET,
        CONFIG_FILE,
        ENV_FILE,
        get_workspace_dir,
    )
    from anyscribe.core.deps import check_dependencies
    from anyscribe.core.updater import get_install_path

    # Dependencies
    dep_results = check_dependencies()
    deps = []
    for r in dep_results:
        deps.append(
            {
                "name": r.dep.name,
                "found": r.found,
                "version": r.version,
                "required": r.dep.required,
            }
        )

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

    return json.dumps(
        {
            "dependencies": deps,
            "config": config,
            "installation": install,
            "skill": skill,
        }
    )


# ── Resources ────────────────────────────────────────────────


@mcp.resource("scribe://config")
def resource_config() -> str:
    """Current anyscribe configuration."""
    return get_config()


@mcp.resource("scribe://providers")
def resource_providers() -> str:
    """Available transcription providers."""
    return list_providers()


@mcp.resource("scribe://workspace")
def resource_workspace() -> str:
    """Workspace info and transcript count."""
    from anyscribe.config.paths import get_workspace_dir

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

    return json.dumps(
        {
            "workspace_path": str(ws),
            "exists": ws.exists(),
            "total_transcripts": count,
            "by_platform": platforms,
        }
    )


# ── Entry point ──────────────────────────────────────────────


def main() -> None:
    """Run the MCP server (stdio transport)."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
