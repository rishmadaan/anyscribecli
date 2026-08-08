#!/usr/bin/env python3
"""Docs honesty gates: version drift + MCP table drift. Exit non-zero on either."""

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
    marked <!-- version-pin-ok --> on the same line."""
    version = real_version()
    offenders = []
    targets = ["docs/user", "landing", "README.md", "src/anyscribe/skill"]
    # Lookarounds keep IPs (127.0.0.1) and SVG path data out of the match.
    pat = re.compile(r"(?<![\d.])v?\d+\.\d+\.\d+(?![\d.])")
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
    return offenders


def check_mcp_table() -> list[str]:
    """Every @mcp.tool in server.py must appear backticked in agents.md."""
    server = (ROOT / "src/anyscribe/mcp/server.py").read_text()
    actual = set(re.findall(r"@mcp\.tool\(\)\s*\ndef (\w+)", server))
    agents = (ROOT / "docs/user/agents.md").read_text()
    documented = set(re.findall(r"`([a-z_]+)`", agents))
    missing = actual - documented
    return [f"agents.md missing MCP tool: `{t}`" for t in sorted(missing)]


def main() -> int:
    problems = check_versions() + check_mcp_table()
    for p in problems:
        print(p, file=sys.stderr)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
