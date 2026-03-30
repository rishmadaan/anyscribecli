"""Create and initialize the Obsidian vault structure."""

from __future__ import annotations

import json
from pathlib import Path

from anyscribecli.config.paths import get_workspace_dir

CORE_PLUGINS = [
    "file-explorer",
    "global-search",
    "backlink",
    "tag-pane",
    "graph",
    "outline",
    "properties",
]

INITIAL_INDEX = """\
# Transcripts — Recent Entries

| Date | Platform | Entry | Duration | TL;DR |
|------|----------|-------|----------|-------|
"""


def create_vault(workspace: Path | None = None) -> Path:
    """Create the Obsidian vault directory structure and config files.

    Returns the workspace path.
    """
    ws = workspace or get_workspace_dir()

    # Create directory tree
    dirs = [
        ws / ".obsidian",
        ws / "sources" / "youtube",
        ws / "sources" / "instagram",
        ws / "daily",
    ]
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)

    # Write .obsidian config
    obsidian = ws / ".obsidian"

    core_plugins_file = obsidian / "core-plugins.json"
    if not core_plugins_file.exists():
        core_plugins_file.write_text(json.dumps(CORE_PLUGINS, indent=2) + "\n")

    app_file = obsidian / "app.json"
    if not app_file.exists():
        app_file.write_text(json.dumps({"showFrontmatter": True}, indent=2) + "\n")

    appearance_file = obsidian / "appearance.json"
    if not appearance_file.exists():
        appearance_file.write_text(json.dumps({"baseFontSize": 16}, indent=2) + "\n")

    # Write initial _index.md
    index_file = ws / "_index.md"
    if not index_file.exists():
        index_file.write_text(INITIAL_INDEX)

    return ws
