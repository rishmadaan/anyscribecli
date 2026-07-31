"""Duplicate detection — find an existing transcript for a source URL/path."""

from __future__ import annotations

from pathlib import Path

import yaml

from anyscribe.config.paths import get_workspace_dir


def find_existing_transcript(source: str) -> Path | None:
    """Return the transcript whose frontmatter ``source:`` matches exactly, else None.

    Scans sources/*/*.md in the workspace, reading only the frontmatter block.
    The vault is the source of truth — no cache, no index parsing.
    """
    sources_dir = get_workspace_dir() / "sources"
    if not sources_dir.is_dir():
        return None

    for md_file in sorted(sources_dir.glob("*/*.md")):
        if md_file.name.startswith("_"):
            continue
        try:
            with open(md_file) as f:
                if f.readline().strip() != "---":
                    continue
                for line in f:
                    if line.strip() == "---":
                        break
                    if line.startswith("source:") and line[len("source:") :].strip() == source:
                        return md_file
        except OSError:
            continue
    return None


def read_frontmatter(path: Path) -> dict:
    """Parse the YAML frontmatter of a transcript file. Returns {} on failure."""
    try:
        text = path.read_text()
        if not text.startswith("---"):
            return {}
        end = text.index("---", 3)
        fm = yaml.safe_load(text[3:end])
        return fm if isinstance(fm, dict) else {}
    except Exception:
        return {}
