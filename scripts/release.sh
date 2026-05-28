#!/usr/bin/env bash
# Release script - bumps version, commits, tags, and pushes to trigger PyPI publish.
#
# Usage:
#   ./scripts/release.sh 0.5.0
#   ./scripts/release.sh 0.5.0 "Short description of what changed"
#
# What it does:
#   1. Updates version in __init__.py and pyproject.toml
#   2. Commits the version bump
#   3. Creates a git tag (v0.5.0)
#   4. Pushes commit + tag, which triggers GitHub Actions to publish to PyPI

set -euo pipefail

VERSION="${1:-}"
MESSAGE="${2:-}"

if [ -z "$VERSION" ]; then
    echo "Usage: ./scripts/release.sh <version> [description]"
    echo "Example: ./scripts/release.sh 0.5.0 \"configurable workspace path\""
    exit 1
fi

# Validate version format (semver-ish)
if ! echo "$VERSION" | grep -qE '^[0-9]+\.[0-9]+\.[0-9]+$'; then
    echo "Error: Version must be in X.Y.Z format (got: $VERSION)"
    exit 1
fi

# Check for clean working tree.
if [ -n "$(git status --porcelain)" ]; then
    echo "Error: Working tree is not clean. Commit or stash changes first."
    git status --short
    exit 1
fi

# Check we're on main
BRANCH=$(git branch --show-current)
if [ "$BRANCH" != "main" ]; then
    echo "Warning: You're on '$BRANCH', not 'main'. Continue? (y/N)"
    read -r CONFIRM
    [ "$CONFIRM" = "y" ] || exit 1
fi

# Check tag doesn't already exist locally or on origin.
if git rev-parse "v$VERSION" >/dev/null 2>&1; then
    echo "Error: Tag v$VERSION already exists locally."
    exit 1
fi

if git ls-remote --exit-code --tags origin "refs/tags/v$VERSION" >/dev/null 2>&1; then
    echo "Error: Tag v$VERSION already exists on origin."
    exit 1
fi

PYTHON=${PYTHON:-python3}
if ! command -v "$PYTHON" >/dev/null 2>&1; then
    PYTHON=python
fi

INIT_FILE="src/anyscribecli/__init__.py"
TOML_FILE="pyproject.toml"

OLD_VERSION=$("$PYTHON" -c "import tomllib; print(tomllib.load(open('$TOML_FILE','rb'))['project']['version'])")
echo "Bumping $OLD_VERSION -> $VERSION"

# Update version in both files. Use Python instead of sed -i so this works
# on both GNU/Linux and macOS release machines.
"$PYTHON" - "$INIT_FILE" "$TOML_FILE" "$OLD_VERSION" "$VERSION" <<'PY'
from pathlib import Path
import sys

init_file = Path(sys.argv[1])
toml_file = Path(sys.argv[2])
old = sys.argv[3]
new = sys.argv[4]

replacements = [
    (init_file, f'__version__ = "{old}"', f'__version__ = "{new}"'),
    (toml_file, f'version = "{old}"', f'version = "{new}"'),
]

for path, before, after in replacements:
    text = path.read_text()
    if before not in text:
        raise SystemExit(f"Could not find expected version string in {path}: {before}")
    path.write_text(text.replace(before, after, 1))
PY

# Verify the changes
NEW_INIT=$(grep '__version__' "$INIT_FILE")
NEW_TOML=$(grep '^version' "$TOML_FILE")
echo "  $INIT_FILE: $NEW_INIT"
echo "  $TOML_FILE: $NEW_TOML"

# Build commit message
COMMIT_MSG="Bump to v$VERSION"
if [ -n "$MESSAGE" ]; then
    COMMIT_MSG="Bump to v$VERSION - $MESSAGE"
fi

# Commit, tag, push
git add "$INIT_FILE" "$TOML_FILE"
git commit -m "$COMMIT_MSG"
git tag "v$VERSION"
git push && git push --tags

echo ""
echo "Released v$VERSION"
echo "  GitHub Actions will publish to PyPI automatically."
echo "  Track it: https://github.com/rishmadaan/anyscribecli/actions"
