#!/usr/bin/env bash
# Release script — bumps version, commits, tags, and pushes to trigger PyPI publish.
#
# Usage:
#   ./scripts/release.sh 0.5.0
#   ./scripts/release.sh 0.5.0 "Short description of what changed"
#
# What it does:
#   1. Updates version in __init__.py and pyproject.toml
#   2. Commits the version bump
#   3. Creates a git tag (v0.5.0)
#   4. Pushes commit + tag → triggers GitHub Actions → publishes to PyPI

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

# Check for clean working tree (except version files we're about to change)
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

# Check tag doesn't already exist
if git rev-parse "v$VERSION" >/dev/null 2>&1; then
    echo "Error: Tag v$VERSION already exists."
    exit 1
fi

INIT_FILE="src/anyscribecli/__init__.py"
TOML_FILE="pyproject.toml"

OLD_VERSION=$(python3 -c "import tomllib; print(tomllib.load(open('$TOML_FILE','rb'))['project']['version'])")
echo "Bumping $OLD_VERSION → $VERSION"

# Update version in both files
sed -i '' "s/__version__ = \"$OLD_VERSION\"/__version__ = \"$VERSION\"/" "$INIT_FILE"
sed -i '' "s/^version = \"$OLD_VERSION\"/version = \"$VERSION\"/" "$TOML_FILE"

# Verify the changes
NEW_INIT=$(grep '__version__' "$INIT_FILE")
NEW_TOML=$(grep '^version' "$TOML_FILE")
echo "  $INIT_FILE: $NEW_INIT"
echo "  $TOML_FILE: $NEW_TOML"

# Build commit message
COMMIT_MSG="Bump to v$VERSION"
if [ -n "$MESSAGE" ]; then
    COMMIT_MSG="Bump to v$VERSION — $MESSAGE"
fi

# Commit, tag, push
git add "$INIT_FILE" "$TOML_FILE"
git commit -m "$COMMIT_MSG"
git tag "v$VERSION"
git push && git push --tags

echo ""
echo "✓ Released v$VERSION"
echo "  GitHub Actions will publish to PyPI automatically."
echo "  Track it: https://github.com/rishmadaan/anyscribecli/actions"
