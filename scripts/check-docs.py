#!/usr/bin/env python3
"""Docs honesty gates: version drift + MCP table drift + changelog gap.

Exit non-zero on any of them.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SVG_PATH_DATA = re.compile(r'\sd="[^"]*"')


def real_version() -> str:
    m = re.search(r'^version = "([^"]+)"', (ROOT / "pyproject.toml").read_text(), re.M)
    assert m, "version not found in pyproject.toml"
    return m.group(1)


def check_versions() -> list[str]:
    """Any vX.Y.Z in user-facing prose must equal the real version or be
    marked <!-- version-pin-ok --> on the same line.

    landing/docs/*.html is scanned too, so a marker in a .md source must land on
    the SAME line as the version once rendered (keep both inside one paragraph).
    """
    version = real_version()
    offenders = []
    targets = ["docs/user", "landing", "README.md", "src/anyscribe/skill"]
    # Lookarounds keep IPs (127.0.0.1) and SVG path data out of the match.
    pat = re.compile(r"(?<![\d.])v?\d+\.\d+\.\d+(?!\.?\d)")
    for target in targets:
        base = ROOT / target
        files = (
            [base]
            if base.is_file()
            else [p for p in base.rglob("*") if p.suffix in {".md", ".html"}]
        )
        for f in files:
            for i, line in enumerate(f.read_text().splitlines(), 1):
                if "version-pin-ok" in line:
                    continue
                line = SVG_PATH_DATA.sub("", line)  # icon coordinates aren't versions
                for hit in pat.findall(line):
                    if hit.lstrip("v") != version:
                        offenders.append(f"{f.relative_to(ROOT)}:{i}: {hit}")
    if offenders:
        # Without this, the failure is a bare list of line numbers and the
        # reader has to find the escape hatch by reading this file. The common
        # cause is a deliberate historical mention (a "fixed in X" note) that
        # was current when written and went stale at the next version bump.
        offenders.append(
            f"  ^ these are versions other than the current {version}. Update them, "
            "or append <!-- version-pin-ok --> on the SAME line if the mention is "
            "deliberately historical (keep marker and version in one paragraph, "
            "since the rendered HTML is scanned too)."
        )
    return offenders


def check_mcp_table() -> list[str]:
    """Every @mcp.tool in server.py must appear backticked in agents.md."""
    server = (ROOT / "src/anyscribe/mcp/server.py").read_text()
    actual = set(re.findall(r"@mcp\.tool\(\)\s*\ndef (\w+)", server))
    agents = (ROOT / "docs/user/agents.md").read_text()
    documented = set(re.findall(r"`([a-z_]+)`", agents))
    missing = actual - documented
    return [f"agents.md missing MCP tool: `{t}`" for t in sorted(missing)]


def check_changelog() -> list[str]:
    """The version being shipped must have its own CHANGELOG.md entry.

    A changelog nobody notices has gone stale is worse than no changelog — it
    reads as "nothing changed". This turns the omission into a red build at the
    moment the version bump lands, which is the only moment anyone is looking.
    """
    version = real_version()
    text = (ROOT / "CHANGELOG.md").read_text()
    if re.search(rf"^## {re.escape(version)}(\s|$)", text, re.M):
        return []
    return [f"CHANGELOG.md: no '## {version}' entry for the version being released"]


def main() -> int:
    problems = check_versions() + check_mcp_table() + check_changelog()
    for p in problems:
        print(p, file=sys.stderr)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
